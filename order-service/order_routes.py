from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from fastapi_jwt_auth import AuthJWT
from typing import List, Optional
import requests
import os
from helper import to_ist
import models, schemas, database
from pytz import timezone
from uuid import UUID
from kafka_producer import delivery_event_producer


order_router = APIRouter(prefix="/api/v1/order", tags=["order"])

# ✅ Create a new order
@order_router.post("/create", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends(),
    Authorization: Optional[str] = Header(None)
):
    try:
        Authorize.jwt_required()
        raw_jwt = Authorize.get_raw_jwt()
        user_id = raw_jwt.get("user_id")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    headers = {"Authorization": f"{Authorization}"}

    # ✅ Validate outlet_code with outlet service
    outlet_service_url = os.getenv("OUTLET_SERVICE_BASE_URL", "http://127.0.0.1:8003") + f"/api/v1/outlet/{order.outlet_code}"


    try:
        outlet_response = requests.get(outlet_service_url, headers=headers, timeout=5)
        if outlet_response.status_code != 200:
            raise HTTPException(status_code=404, detail=f"Outlet with code '{order.outlet_code}' not found")
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Failed to communicate with outlet service")

    # ✅ Fetch pizza details and calculate total price
    pizza_service_url_base = os.getenv("PIZZA_SERVICE_BASE_URL", "http://127.0.0.1:8002")
    total_price = 0.0
    validated_items = []

    for item in order.items:
        pizza_url = f"{pizza_service_url_base}/api/v1/pizza/{item.pizza_id}"
        try:
            response = requests.get(pizza_url, headers=headers, timeout=5)
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail=f"Pizza with ID {item.pizza_id} not found")

            pizza_data = response.json()
            price = pizza_data["price"]
            quantity = item.quantity
            subtotal = price * quantity
            total_price += subtotal

            validated_items.append({
                "pizza_id": item.pizza_id,
                "quantity": quantity,
                "unit_price": price,
                "subtotal": subtotal
            })

        except requests.RequestException:
            raise HTTPException(status_code=503, detail="Failed to contact pizza service")

    # ✅ Create and store the order
    new_order = models.Order(
        customer_id=user_id,
        outlet_code=order.outlet_code,
        total_price=total_price,
        status=schemas.OrderStatus.PENDING,
        delivery_address = order.delivery_address
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # ✅ Send Kafka event to delivery-service
    try:
        delivery_event_producer({
            "order_uid": str(new_order.order_uid),
            "customer_id": new_order.customer_id,
            "outlet_code": new_order.outlet_code,
            "total_price": new_order.total_price,
            "status": str(new_order.status),
            "delivery_address": new_order.delivery_address,
            "items": validated_items,
            "created_at": new_order.created_at.isoformat()
        })
    except Exception as e:
        print(f"[Kafka Error] Failed to send event for order {new_order.order_uid} - {e}")

    # ✅ Store order items
    for item in validated_items:
        db.add(models.OrderItem(
            order_id=new_order.id,
            pizza_id=item["pizza_id"],
            quantity=item["quantity"],
            price=item["unit_price"]
        ))
    db.commit()
    db.refresh(new_order)

    # ✅ Prepare response with full calculation
    response_items = [
        schemas.OrderItemOut(
            pizza_id=item["pizza_id"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            subtotal=item["subtotal"]
        ) for item in validated_items
    ]

    return schemas.OrderOut(
        id=new_order.id,
        customer_id=new_order.customer_id,
        outlet_code=new_order.outlet_code,
        total_price=new_order.total_price,
        status=new_order.status,
        created_at=new_order.created_at.astimezone(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
        order_uid=new_order.order_uid,
        items=response_items,
        delivery_address=new_order.delivery_address
    )



# ✅ Get all orders
@order_router.get("/", response_model=List[schemas.OrderOut])
async def get_all_orders(
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    try:
        Authorize.jwt_required()
        user = Authorize.get_raw_jwt()
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    user_role = user.get("role")
    print(user_role)
    if user_role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can access all orders")

    orders = db.query(models.Order).all()

    return [
        schemas.OrderOut(
            id=order.id,
            customer_id=order.customer_id,
            outlet_code=order.outlet_code,
            total_price=order.total_price,
            status=order.status,
            created_at=to_ist(order.created_at),
            order_uid=order.order_uid,
            items=[
                schemas.OrderItemOut(
                    pizza_id=item.pizza_id,
                    quantity=item.quantity,
                    unit_price=item.price,
                    subtotal=item.price * item.quantity
                ) for item in order.items
            ]
        ) for order in orders
    ]

@order_router.get("/history", response_model=List[schemas.OrderOut])
async def get_my_orders(
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    try:
        Authorize.jwt_required()
        user_claims = Authorize.get_raw_jwt()
        user_id = user_claims.get("user_id")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

    orders = db.query(models.Order).filter(models.Order.customer_id == user_id).order_by(models.Order.created_at.desc()).all()
    response = []

    for order in orders:
        items = [
            schemas.OrderItemOut(
                pizza_id=item.pizza_id,
                quantity=item.quantity,
                unit_price=item.price,
                subtotal=item.price * item.quantity
            ) for item in order.items
        ]

        response.append(schemas.OrderOut(
            id=order.id,
            customer_id=order.customer_id,
            outlet_code=order.outlet_code,
            total_price=order.total_price,
            status=order.status,
            created_at=order.created_at.astimezone(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
            order_uid=order.order_uid,
            items=items
        ))

    return response


# ✅ Get order by ID
@order_router.get("/{order_id}", response_model=schemas.OrderOut)
async def get_order_by_id(
    order_id: int,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    try:
        Authorize.jwt_required()
        user_role = Authorize.get_raw_jwt().get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    if user_role not in ["ADMIN", "STAFF"]:
        raise HTTPException(status_code=403, detail="Access forbidden: only admin or staff allowed")

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return schemas.OrderOut(
        id=order.id,
        customer_id=order.customer_id,
        outlet_code=order.outlet_code,
        total_price=order.total_price,
        status=order.status,
        created_at=to_ist(order.created_at),
        order_uid=order.order_uid,
        items=[
            schemas.OrderItemOut(
                pizza_id=item.pizza_id,
                quantity=item.quantity,
                price=item.price,
                unit_price=item.price,
                subtotal = item.price * item.quantity
            ) for item in order.items
        ]
    )

# ✅ Get order by UID
@order_router.get("/by_uid/{order_uid}", response_model=schemas.OrderOut)
async def get_order_by_uid(
    order_uid: str,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    try:
        Authorize.jwt_required()
        user_role = Authorize.get_raw_jwt().get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    if user_role not in ["ADMIN", "STAFF", "CUSTOMER"]:
        raise HTTPException(status_code=403, detail="Access forbidden: only admin or staff allowed")

    order = db.query(models.Order).filter(models.Order.order_uid == order_uid).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return schemas.OrderOut(
        id=order.id,
        customer_id=order.customer_id,
        outlet_code=order.outlet_code,
        total_price=order.total_price,
        status=order.status,
        created_at=to_ist(order.created_at),
        order_uid=order.order_uid,
        items=[
            schemas.OrderItemOut(
                pizza_id=item.pizza_id,
                quantity=item.quantity,
                price=item.price,
                unit_price=item.price,
                subtotal = item.price * item.quantity
            ) for item in order.items
        ]
    )

# ✅ update order status by UID
@order_router.put("/{order_uid}/status", response_model=schemas.OrderOut)
async def update_order_status(
    order_uid: UUID,
    payload: schemas.UpdateOrderStatus,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    try:
        Authorize.jwt_required()
        user_role = Authorize.get_raw_jwt().get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    if user_role not in ["STAFF", "DELIVERY"]:
        raise HTTPException(status_code=403, detail="Access forbidden: only staff or delivery person allowed")

    order = db.query(models.Order).filter(models.Order.order_uid == str(order_uid)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = payload.new_status
    db.commit()
    db.refresh(order)

    return schemas.OrderOut(
        id=order.id,
        customer_id=order.customer_id,
        outlet_code=order.outlet_code,
        total_price=order.total_price,
        status=order.status,
        created_at=to_ist(order.created_at),
        order_uid=order.order_uid,
        items=[
            schemas.OrderItemOut(
                pizza_id=item.pizza_id,
                quantity=item.quantity,
                price=item.price,
                unit_price=item.price,
                subtotal=item.price * item.quantity
            ) for item in order.items
        ]
    )

# ✅ Get order status by UID
@order_router.get("/{order_uid}/status", response_model=dict)
async def get_order_status(
    order_uid: str,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends(),
):
    try:
        Authorize.jwt_required()
        user_role = Authorize.get_raw_jwt().get("role")

        user_claims = Authorize.get_raw_jwt()
        user_id = user_claims.get("user_id")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    if user_role not in ["ADMIN", "STAFF", "CUSTOMER"]:
        raise HTTPException(status_code=403, detail="Access forbidden: customers, staff, admin only")

    order = db.query(models.Order).filter(models.Order.order_uid == order_uid).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Optional: Ensure customer is viewing only their own order
    if user_role == "CUSTOMER":
        if order.customer_id != int(user_id):
            raise HTTPException(status_code=403, detail="Access denied: not your order")

    return {
        # "outlet_code": order.outlet_code,
        "total_price":order.total_price,
        "status" : order.status,
        "created_at": order.created_at.astimezone(timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"),
        "order_uid": order.order_uid,
        # "items" :order.items
    }

# ✅ Cancel order by UID
@order_router.patch("/{order_uid}/cancel", response_model=schemas.OrderOut)
async def cancel_order(
    order_uid: UUID,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    try:
        Authorize.jwt_required()
        claims = Authorize.get_raw_jwt()
        user_role = claims.get("role")
        user_id = claims.get("user_id")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    if user_role not in ["STAFF", "CUSTOMER"]:
        raise HTTPException(status_code=403, detail="Access forbidden: Respective Customer and Staff only")

    order = db.query(models.Order).filter(models.Order.order_uid == str(order_uid)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # ✅ Only allow cancel if status is PENDING
    if order.status != schemas.OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending orders can be canceled")

    # ✅ Customers can only cancel their own orders
    if user_role == "CUSTOMER" and order.customer_id != int(user_id):
        raise HTTPException(status_code=403, detail="Access denied: not your order")

    # ✅ Cancel the order
    order.status = schemas.OrderStatus.CANCELLED
    db.commit()
    db.refresh(order)

    return schemas.OrderOut(
        outlet_code=order.outlet_code,
        total_price=order.total_price,
        status=order.status,
        created_at=to_ist(order.created_at),
        order_uid=order.order_uid,
        items=[
            schemas.OrderItemOut(
                pizza_id=item.pizza_id,
                quantity=item.quantity,
                unit_price=item.price,
                subtotal=item.price * item.quantity
            ) for item in order.items
        ]
    )

# ✅ Delete an order
@order_router.delete("/{order_id}", response_model=dict)
async def delete_order(
    order_id: int,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    try:
        Authorize.jwt_required()
        user_role = Authorize.get_raw_jwt().get("role")
        if user_role not in ["ADMIN"]:
            raise HTTPException(status_code=403, detail="Access forbidden: only admin, staff, or customer allowed")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(order)
    db.commit()

    return {"message": f"Order with ID {order_id} has been deleted successfully"}