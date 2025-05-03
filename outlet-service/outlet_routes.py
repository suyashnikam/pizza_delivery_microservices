from fastapi import APIRouter, HTTPException, Depends, status, Header
from sqlalchemy.orm import Session
from fastapi_jwt_auth import AuthJWT
from typing import Optional
import requests
import os
from dotenv import load_dotenv
from redis_client import redis_client
import models, schemas, database
from models import Outlet
import json
load_dotenv()

outlet_router = APIRouter(prefix="/api/v1/outlet", tags=["Outlet"])

# ✅ Auth & Role utilities (kept inline as you requested)
def jwt_required(Authorize: AuthJWT = Depends()):
    try:
        Authorize.jwt_required()
        return Authorize.get_raw_jwt()
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized access")

def role_required(required_role: str):
    def checker(payload=Depends(jwt_required)):
        role = payload.get("role")
        if role != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Requires '{required_role}' role."
            )
    return checker

# ✅ Create new outlet (Admin only)
@outlet_router.post("/create", response_model=schemas.OutletOut, status_code=status.HTTP_201_CREATED)
def create_outlet(
    outlet: schemas.OutletCreate,
    db: Session = Depends(database.get_db),
    _: str = Depends(role_required("ADMIN"))
):
    new_outlet = Outlet(**outlet.dict())
    db.add(new_outlet)
    db.commit()
    db.refresh(new_outlet)
    redis_client.delete("all_outlets")
    return new_outlet

# ✅ Get all outlets (open access)
@outlet_router.get("/", response_model=list[schemas.OutletOut])
def list_outlets(
    db: Session = Depends(database.get_db),
):
    cache_key = "all_outlets"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    outlets = db.query(Outlet).all()
    # Use from_orm to convert models to dicts
    data = [json.loads(schemas.OutletOut.from_orm(outlet).json()) for outlet in outlets]

    redis_client.set(cache_key, json.dumps(data), ex=300)  # Cache for 5 mins
    return data

# ✅ Get outlet by outlet_code
@outlet_router.get("/{outlet_code}", response_model=schemas.OutletOut)
def get_outlet(
    outlet_code: str,
    db: Session = Depends(database.get_db),
):
    outlet = db.query(Outlet).filter(Outlet.code == outlet_code).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found with this code!!")
    return outlet

# ✅ Update outlet (Admin only)
@outlet_router.put("/{outlet_id}", response_model=schemas.OutletOut)
def update_outlet(
    outlet_id: int,
    outlet_data: schemas.OutletCreate,
    db: Session = Depends(database.get_db),
    _: str = Depends(role_required("ADMIN"))
):
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    for field, value in outlet_data.dict().items():
        setattr(outlet, field, value)

    db.commit()
    db.refresh(outlet)
    redis_client.delete("all_outlets")
    return outlet

# ✅ Delete outlet (Admin only)
@outlet_router.delete("/{outlet_id}", response_model=dict, status_code=status.HTTP_200_OK)
def delete_outlet(
    outlet_id: int,
    db: Session = Depends(database.get_db),
    _: str = Depends(role_required("ADMIN"))
):
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    db.delete(outlet)
    db.commit()
    redis_client.delete("all_outlets")
    return {"message": f"Outlet with ID {outlet_id} has been deleted successfully"}

# ✅ Get available pizzas at outlet (auth optional, for inter-service)
@outlet_router.get("/{outlet_code}/pizzas", response_model=list[dict])
def get_outlet_pizzas(
    outlet_code: str,
    db: Session = Depends(database.get_db),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    outlet = db.query(Outlet).filter(Outlet.code == outlet_code).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    try:
        headers = {"Authorization": authorization} if authorization else {}
        pizza_service_url = os.getenv("PIZZA_SERVICE_BASE_URL", "http://127.0.0.1:8005")
        response = requests.get(f"{pizza_service_url}/api/v1/pizza/for-outlet/{outlet_code}", headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Pizza service error: {str(e)}")