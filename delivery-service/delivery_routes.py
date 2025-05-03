from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from fastapi_jwt_auth import AuthJWT
from typing import List, Optional
from datetime import datetime
import os
import models
import schemas
import database
import requests

delivery_router = APIRouter(prefix="/api/v1/delivery", tags=["Delivery"])


# --- Utility functions ---
def get_user_role(Authorize: AuthJWT) -> str:
    try:
        Authorize.jwt_required()
        return Authorize.get_raw_jwt().get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")


# --- Routes ---

@delivery_router.post("/create", response_model=schemas.DeliveryOut)
async def create_delivery(
    delivery_data: schemas.DeliveryCreate,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    role = get_user_role(Authorize)

    if role not in {"ADMIN", "STAFF"}:
        raise HTTPException(status_code=403, detail="Only staff or admin can create deliveries")

    existing_delivery = db.query(models.Delivery).filter_by(order_uid=delivery_data.order_uid).first()
    if existing_delivery:
        raise HTTPException(
            status_code=400,
            detail=f"Delivery already exists for order_uid: {delivery_data.order_uid}"
        )

    new_delivery = models.Delivery(
        order_uid=delivery_data.order_uid,
        status=delivery_data.status or "PENDING",
    )

    db.add(new_delivery)
    db.commit()
    db.refresh(new_delivery)
    return new_delivery



@delivery_router.put("/update-status", response_model=schemas.DeliveryOut)
async def update_status_by_delivery_person(
    update_data: schemas.DeliveryStatusUpdateIn,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    try:
        Authorize.jwt_required()
        user_id = Authorize.get_raw_jwt().get("user_id")
        role = Authorize.get_raw_jwt().get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    if role != "DELIVERY":
        raise HTTPException(status_code=403, detail="Only Delivery Person can update the status")

    # Find delivery and verify ownership
    delivery = db.query(models.Delivery).filter(
        models.Delivery.delivery_uid == update_data.delivery_uid,
        models.Delivery.delivery_person_id == user_id
    ).first()

    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found or not assigned to you")

    # Update status
    delivery.status = update_data.status
    delivery.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(delivery)

    return delivery


@delivery_router.get("/{identifier}", response_model=schemas.DeliveryOut)
async def get_delivery(
    identifier: str,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    get_user_role(Authorize)

    if identifier.isdigit():
        delivery = db.query(models.Delivery).filter(models.Delivery.id == int(identifier)).first()
    else:
        delivery = db.query(models.Delivery).filter(models.Delivery.delivery_uid == identifier).first()

    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    return delivery

##get all deliveries
@delivery_router.get("/", response_model=List[schemas.DeliveryOut])
async def get_all_deliveries(
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    role = get_user_role(Authorize)

    if role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can access all deliveries")

    return db.query(models.Delivery).all()

##track your order by order_uid
@delivery_router.get("/order/{order_uid}", response_model=schemas.DeliveryOut)
async def get_delivery_by_order_uid(
    order_uid: str,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    get_user_role(Authorize)

    delivery = db.query(models.Delivery).filter(models.Delivery.order_uid == order_uid).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found for this order")

    return delivery


@delivery_router.delete("/{delivery_id}")
async def delete_delivery(
    delivery_id: int,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends()
):
    role = get_user_role(Authorize)

    if role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admins can delete deliveries")

    delivery = db.query(models.Delivery).filter(models.Delivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")

    db.delete(delivery)
    db.commit()
    return {"detail": "Delivery deleted successfully"}

##assing delivery person to delivery order
@delivery_router.put("/assign", response_model=schemas.DeliveryOut)
async def assign_delivery_person(
    assign_data: schemas.DeliveryAssignIn,
    db: Session = Depends(database.get_db),
    Authorize: AuthJWT = Depends(),
    Authorization: Optional[str] = Header(None)
):
    # Step 1: Auth check
    try:
        Authorize.jwt_required()
        role = Authorize.get_raw_jwt().get("role")
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    if role not in ["ADMIN", "STAFF"]:
        raise HTTPException(status_code=403, detail="Only Admin or Staff can assign delivery person to delivery. ")

    # Step 2: Fetch delivery record
    delivery = db.query(models.Delivery).filter(
        models.Delivery.delivery_uid == assign_data.delivery_uid
    ).first()

    if not delivery:
        raise HTTPException(status_code=404, detail=f"Delivery not found for UID: {assign_data.delivery_uid}")

    if assign_data.status != "DISPATCHED":
        raise HTTPException(status_code=400, detail="Only DISPATCHED status allowed for assignment")

    # Step 3: Validate delivery person
    auth_service_url = os.getenv("USER_SERVICE_BASE_URL", "http://127.0.0.1:8001")
    validate_url = f"{auth_service_url}/api/v1/auth/validate-user/{assign_data.delivery_person_id}"

    headers = {"Authorization": f"{Authorization}"}

    try:
        response = requests.get(validate_url, headers=headers, timeout=5)
        print(response)
        if response.status_code != 200 or not response.json().get("is_valid_delivery_person", False):
            raise HTTPException(status_code=400, detail="Invalid or inactive delivery person")
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    # Step 4: Assign person & update
    if delivery.delivery_person_id is None:
        delivery.assigned_at = datetime.utcnow()
    delivery.delivery_person_id = assign_data.delivery_person_id
    delivery.status = assign_data.status
    delivery.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(delivery)

    return delivery

