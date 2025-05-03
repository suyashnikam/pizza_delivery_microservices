from fastapi import FastAPI
from fastapi_jwt_auth import AuthJWT
import outlet_routes
from config import Settings
from middleware import AuthMiddleware
app = FastAPI()

@AuthJWT.load_config
def get_config():
    return Settings()

app.add_middleware(AuthMiddleware)
app.include_router(outlet_routes.outlet_router)