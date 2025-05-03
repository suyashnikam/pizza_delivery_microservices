from fastapi import FastAPI
from fastapi_jwt_auth import AuthJWT
import delivery_routes
from config import Settings
from middleware import AuthMiddleware
from delivery_consumer import start_delivery_consumer

app = FastAPI()

start_delivery_consumer()

@AuthJWT.load_config
def get_config():
    return Settings()

app.add_middleware(AuthMiddleware)
app.include_router(delivery_routes.delivery_router)