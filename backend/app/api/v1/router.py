from fastapi import APIRouter

from app.api.v1 import auth, catalog, health, inventory, reports, sales, scanner, settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(inventory.router)
api_router.include_router(reports.router)
api_router.include_router(sales.router)
api_router.include_router(scanner.router)
api_router.include_router(settings.router)
