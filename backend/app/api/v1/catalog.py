from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.models.catalog import Supplier
from app.schemas.catalog import (
    CategoryOut,
    IngredientCreate,
    IngredientOut,
    ProductCreate,
    ProductOut,
    RecipeCostOut,
    RecipeCreate,
    RecipeVersionOut,
    SupplierOut,
    UnitOut,
    VariantCreate,
    VariantOut,
)
from app.services.catalog_service import CatalogService
from app.services.recipe_service import RecipeService

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _supplier_out(supplier: Supplier) -> SupplierOut:
    return SupplierOut(
        id=supplier.id,
        code=supplier.code,
        name_en=supplier.name,
        name_ar=supplier.name,
        is_active=supplier.is_active,
    )


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: DbSession, _user: CurrentUser) -> list[CategoryOut]:
    return await CatalogService(db).list_categories()


@router.get("/suppliers", response_model=list[SupplierOut])
async def list_suppliers(db: DbSession, _user: CurrentUser) -> list[SupplierOut]:
    suppliers = await CatalogService(db).list_suppliers()
    return [_supplier_out(s) for s in suppliers]


@router.get("/units", response_model=list[UnitOut])
async def list_units(db: DbSession, _user: CurrentUser) -> list[UnitOut]:
    return await CatalogService(db).list_units()


@router.get("/ingredients", response_model=list[IngredientOut])
async def list_ingredients(db: DbSession, _user: CurrentUser) -> list[IngredientOut]:
    return await CatalogService(db).list_ingredients()


@router.post("/ingredients", response_model=IngredientOut, status_code=201)
async def create_ingredient(
    body: IngredientCreate,
    db: DbSession,
    _user: CurrentUser,
) -> IngredientOut:
    ingredient = await CatalogService(db).create_ingredient(body.model_dump())
    await db.commit()
    await db.refresh(ingredient)
    return ingredient


@router.get("/products", response_model=list[ProductOut])
async def list_products(db: DbSession, _user: CurrentUser) -> list[ProductOut]:
    return await CatalogService(db).list_products()


@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(
    body: ProductCreate,
    db: DbSession,
    _user: CurrentUser,
) -> ProductOut:
    product = await CatalogService(db).create_product(body.model_dump())
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/variants", response_model=list[VariantOut])
async def list_variants(
    db: DbSession,
    _user: CurrentUser,
    product_id: UUID | None = None,
) -> list[VariantOut]:
    return await CatalogService(db).list_variants(product_id)


@router.post("/variants", response_model=VariantOut, status_code=201)
async def create_variant(
    body: VariantCreate,
    db: DbSession,
    _user: CurrentUser,
) -> VariantOut:
    variant = await CatalogService(db).create_variant(body.model_dump())
    await db.commit()
    await db.refresh(variant)
    return variant


@router.post("/recipes", response_model=RecipeVersionOut, status_code=201)
async def create_recipe(
    body: RecipeCreate,
    db: DbSession,
    user: CurrentUser,
) -> RecipeVersionOut:
    version = await RecipeService(db).create_version(
        body.variant_id,
        [item.model_dump() for item in body.items],
        created_by_id=user.id,
    )
    await db.commit()
    return version


@router.get("/recipes/{variant_id}/cost", response_model=RecipeCostOut)
async def recipe_cost(
    variant_id: UUID,
    db: DbSession,
    _user: CurrentUser,
) -> RecipeCostOut:
    cost = await RecipeService(db).theoretical_cost(variant_id)
    return RecipeCostOut(variant_id=variant_id, theoretical_cost=cost)


@router.get("/recipes/{variant_id}/history", response_model=list[RecipeVersionOut])
async def recipe_history(
    variant_id: UUID,
    db: DbSession,
    _user: CurrentUser,
) -> list[RecipeVersionOut]:
    return await RecipeService(db).get_history(variant_id)
