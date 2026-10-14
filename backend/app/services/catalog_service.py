from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.models.catalog import Category, Ingredient, Product, ProductVariant, Supplier, Unit


class CatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_units(self) -> list[Unit]:
        result = await self._session.execute(select(Unit).order_by(Unit.code))
        return list(result.scalars().all())

    async def list_categories(self) -> list[Category]:
        result = await self._session.execute(
            select(Category).order_by(Category.sort_order, Category.name_en)
        )
        return list(result.scalars().all())

    async def list_suppliers(self) -> list[Supplier]:
        result = await self._session.execute(select(Supplier).order_by(Supplier.code))
        return list(result.scalars().all())

    async def list_ingredients(self) -> list[Ingredient]:
        result = await self._session.execute(
            select(Ingredient)
            .options(
                selectinload(Ingredient.storage_unit),
                selectinload(Ingredient.purchase_unit),
            )
            .order_by(Ingredient.name_en)
        )
        return list(result.scalars().all())

    async def create_ingredient(self, data: dict) -> Ingredient:
        await self._require_unit(data["storage_unit_id"])
        await self._require_unit(data["purchase_unit_id"])
        supplier_id = data.get("default_supplier_id")
        if supplier_id is not None:
            await self._require_supplier(supplier_id)

        ingredient = Ingredient(**data)
        self._session.add(ingredient)
        await self._session.flush()
        return ingredient

    async def list_products(self) -> list[Product]:
        result = await self._session.execute(
            select(Product)
            .options(selectinload(Product.variants), selectinload(Product.category))
            .order_by(Product.sort_order, Product.name_en)
        )
        return list(result.scalars().all())

    async def create_product(self, data: dict) -> Product:
        await self._require_category(data["category_id"])
        product = Product(**data)
        self._session.add(product)
        await self._session.flush()
        return product

    async def list_variants(self, product_id: UUID | None = None) -> list[ProductVariant]:
        query = select(ProductVariant).options(selectinload(ProductVariant.product))
        if product_id is not None:
            query = query.where(ProductVariant.product_id == product_id)
        result = await self._session.execute(query.order_by(ProductVariant.name_en))
        return list(result.scalars().all())

    async def create_variant(self, data: dict) -> ProductVariant:
        await self._require_product(data["product_id"])
        variant = ProductVariant(**data)
        self._session.add(variant)
        await self._session.flush()
        return variant

    async def _require_unit(self, unit_id: UUID) -> Unit:
        unit = await self._session.get(Unit, unit_id)
        if unit is None:
            raise NotFoundError("Unit not found")
        return unit

    async def _require_supplier(self, supplier_id: UUID) -> Supplier:
        supplier = await self._session.get(Supplier, supplier_id)
        if supplier is None:
            raise NotFoundError("Supplier not found")
        return supplier

    async def _require_category(self, category_id: UUID) -> Category:
        category = await self._session.get(Category, category_id)
        if category is None:
            raise NotFoundError("Category not found")
        return category

    async def _require_product(self, product_id: UUID) -> Product:
        product = await self._session.get(Product, product_id)
        if product is None:
            raise NotFoundError("Product not found")
        return product
