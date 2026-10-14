from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import (
    Category,
    Ingredient,
    Modifier,
    ModifierEffect,
    ModifierGroup,
    Product,
    ProductModifierGroup,
    ProductVariant,
    RecipeItem,
    RecipeVersion,
    Supplier,
    Unit,
)


async def seed_catalog(session: AsyncSession) -> None:
    units = await _ensure_units(session)
    suppliers = await _ensure_suppliers(session)
    categories = await _ensure_categories(session)
    ingredients = await _ensure_ingredients(session, units, suppliers)
    products, variants = await _ensure_products(session, categories)
    await _ensure_recipes(session, variants, ingredients, units)
    await _ensure_modifiers(session, products, ingredients, units)
    await session.flush()


async def _ensure_units(session: AsyncSession) -> dict[str, Unit]:
    defaults = [
        ("g", "Gram", "جرام", "mass", Decimal("1"), True),
        ("kg", "Kilogram", "كيلوجرام", "mass", Decimal("1000"), False),
        ("ml", "Milliliter", "ملليلتر", "volume", Decimal("1"), True),
        ("L", "Liter", "لتر", "volume", Decimal("1000"), False),
        ("piece", "Piece", "قطعة", "count", Decimal("1"), True),
        ("scoop", "Scoop", "مكيال", "count", Decimal("1"), False),
        ("bottle", "Bottle", "زجاجة", "count", Decimal("1"), False),
        ("portion", "Portion", "حصة", "count", Decimal("1"), False),
    ]
    units: dict[str, Unit] = {}
    for code, name_en, name_ar, dimension, factor_to_base, is_base in defaults:
        result = await session.execute(select(Unit).where(Unit.code == code))
        unit = result.scalar_one_or_none()
        if unit is None:
            unit = Unit(
                code=code,
                name_en=name_en,
                name_ar=name_ar,
                dimension=dimension,
                factor_to_base=factor_to_base,
                is_base=is_base,
            )
            session.add(unit)
            await session.flush()
        units[code] = unit
    return units


async def _ensure_suppliers(session: AsyncSession) -> dict[str, Supplier]:
    defaults = [
        ("DAIRYCO", "DairyCo"),
        ("PROTEINPLUS", "ProteinPlus"),
        ("PRODUCELOCAL", "ProduceLocal"),
    ]
    suppliers: dict[str, Supplier] = {}
    for code, name in defaults:
        result = await session.execute(select(Supplier).where(Supplier.code == code))
        supplier = result.scalar_one_or_none()
        if supplier is None:
            supplier = Supplier(code=code, name=name)
            session.add(supplier)
            await session.flush()
        suppliers[code] = supplier
    return suppliers


async def _ensure_categories(session: AsyncSession) -> dict[str, Category]:
    defaults = [
        ("COFFEE", "Coffee", "قهوة"),
        ("HEALTHY_DRINKS", "Healthy Drinks", "مشروبات صحية"),
        ("PROTEIN_SHAKES", "Protein Shakes", "مشروبات بروتين"),
        ("SMOOTHIES", "Smoothies", "سموذي"),
        ("HEALTHY_FOOD", "Healthy Food", "طعام صحي"),
        ("WRAPS", "Wraps", "راب"),
        ("SNACKS", "Snacks", "وجبات خفيفة"),
        ("WATER", "Water", "مياه"),
    ]
    categories: dict[str, Category] = {}
    for sort_order, (code, name_en, name_ar) in enumerate(defaults, start=1):
        result = await session.execute(select(Category).where(Category.code == code))
        category = result.scalar_one_or_none()
        if category is None:
            category = Category(
                code=code,
                name_en=name_en,
                name_ar=name_ar,
                sort_order=sort_order,
            )
            session.add(category)
            await session.flush()
        categories[code] = category
    return categories


async def _ensure_ingredients(
    session: AsyncSession,
    units: dict[str, Unit],
    suppliers: dict[str, Supplier],
) -> dict[str, Ingredient]:
    defaults = [
        ("MILK", "Milk", "حليب", "ml", "L", Decimal("0.06"), Decimal("20000"), "DAIRYCO"),
        (
            "LACTOSE_FREE_MILK",
            "Lactose-free Milk",
            "حليب خالي اللاكتوز",
            "ml",
            "L",
            Decimal("0.09"),
            Decimal("5000"),
            "DAIRYCO",
        ),
        ("BANANA", "Banana", "موز", "piece", "piece", Decimal("10"), Decimal("20"), "PRODUCELOCAL"),
        (
            "WHEY",
            "Whey Protein",
            "واي بروتين",
            "scoop",
            "scoop",
            Decimal("40"),
            Decimal("10"),
            "PROTEINPLUS",
        ),
        (
            "COFFEE_BEANS",
            "Coffee Beans",
            "حبوب قهوة",
            "g",
            "kg",
            Decimal("0.80"),
            Decimal("1000"),
            "PRODUCELOCAL",
        ),
        (
            "STRAWBERRY",
            "Strawberry",
            "فراولة",
            "g",
            "kg",
            Decimal("0.18"),
            Decimal("1000"),
            "PRODUCELOCAL",
        ),
        (
            "GREEK_YOGURT",
            "Greek Yogurt",
            "زبادي يوناني",
            "g",
            "kg",
            Decimal("0.12"),
            Decimal("2000"),
            "DAIRYCO",
        ),
        (
            "GRANOLA",
            "Granola",
            "جرانولا",
            "g",
            "kg",
            Decimal("0.15"),
            Decimal("1000"),
            "PRODUCELOCAL",
        ),
        (
            "PEANUT_BUTTER",
            "Peanut Butter",
            "زبدة فول سوداني",
            "g",
            "kg",
            Decimal("0.22"),
            Decimal("1000"),
            "PRODUCELOCAL",
        ),
        (
            "WATER_BOTTLE",
            "Bottled Water",
            "زجاجة مياه",
            "bottle",
            "bottle",
            Decimal("8"),
            Decimal("24"),
            "PRODUCELOCAL",
        ),
        ("CHICKEN", "Chicken", "دجاج", "g", "kg", Decimal("0.18"), Decimal("2000"), "PRODUCELOCAL"),
        (
            "MOZZARELLA",
            "Mozzarella",
            "موتزاريلا",
            "g",
            "kg",
            Decimal("0.20"),
            Decimal("1000"),
            "DAIRYCO",
        ),
        (
            "TORTILLA",
            "Tortilla",
            "تورتيلا",
            "piece",
            "piece",
            Decimal("12"),
            Decimal("20"),
            "PRODUCELOCAL",
        ),
    ]
    ingredients: dict[str, Ingredient] = {}
    for (
        sku,
        name_en,
        name_ar,
        storage_code,
        purchase_code,
        wac,
        min_stock,
        supplier_code,
    ) in defaults:
        result = await session.execute(select(Ingredient).where(Ingredient.sku == sku))
        ingredient = result.scalar_one_or_none()
        if ingredient is None:
            ingredient = Ingredient(
                sku=sku,
                name_en=name_en,
                name_ar=name_ar,
                storage_unit_id=units[storage_code].id,
                purchase_unit_id=units[purchase_code].id,
                wac=wac,
                min_stock=min_stock,
                default_supplier_id=suppliers[supplier_code].id,
            )
            session.add(ingredient)
            await session.flush()
        ingredients[sku] = ingredient
    return ingredients


async def _ensure_products(
    session: AsyncSession,
    categories: dict[str, Category],
) -> tuple[dict[str, Product], dict[str, ProductVariant]]:
    product_defs = [
        ("ESPRESSO", "Espresso", "إسبريسو", "COFFEE", Decimal("45")),
        ("AMERICANO", "Americano", "أمريكانو", "COFFEE", Decimal("55")),
        ("CAPPUCCINO", "Cappuccino", "كابتشينو", "COFFEE", Decimal("85")),
        ("LATTE", "Latte", "لاتيه", "COFFEE", None),
        ("ICED_COFFEE", "Iced Coffee", "قهوة مثلجة", "COFFEE", Decimal("90")),
        ("PROTEIN_COFFEE", "Protein Coffee", "قهوة بروتين", "PROTEIN_SHAKES", Decimal("130")),
        (
            "BANANA_PROTEIN_SHAKE",
            "Banana Protein Shake",
            "مخفوق بروتين بالموز",
            "PROTEIN_SHAKES",
            Decimal("120"),
        ),
        (
            "ICED_COFFEE_PROTEIN",
            "Iced Coffee Protein",
            "قهوة بروتين مثلجة",
            "PROTEIN_SHAKES",
            Decimal("135"),
        ),
        ("STRAWBERRY_SMOOTHIE", "Strawberry Smoothie", "سموذي فراولة", "SMOOTHIES", Decimal("110")),
        (
            "GREEK_YOGURT_BOWL",
            "Greek Yogurt Bowl",
            "وعاء زبادي يوناني",
            "HEALTHY_FOOD",
            Decimal("140"),
        ),
        ("BOTTLED_WATER", "Bottled Water", "مياه معبأة", "WATER", Decimal("25")),
        ("CHICKEN_WRAP", "Chicken Wrap", "راب دجاج", "WRAPS", Decimal("180")),
    ]
    products: dict[str, Product] = {}
    variants: dict[str, ProductVariant] = {}
    for sort_order, (sku, name_en, name_ar, category_code, price) in enumerate(
        product_defs, start=1
    ):
        result = await session.execute(select(Product).where(Product.sku == sku))
        product = result.scalar_one_or_none()
        if product is None:
            product = Product(
                sku=sku,
                name_en=name_en,
                name_ar=name_ar,
                category_id=categories[category_code].id,
                sort_order=sort_order,
            )
            session.add(product)
            await session.flush()
        products[sku] = product
        if price is not None:
            variants[sku] = await _ensure_variant(session, product, sku, "Regular", "عادي", price)

    latte = products["LATTE"]
    variants["LATTE-S"] = await _ensure_variant(
        session, latte, "LATTE-S", "Small", "صغير", Decimal("85")
    )
    variants["LATTE-M"] = await _ensure_variant(
        session, latte, "LATTE-M", "Medium", "وسط", Decimal("100")
    )
    variants["LATTE-L"] = await _ensure_variant(
        session, latte, "LATTE-L", "Large", "كبير", Decimal("115")
    )
    return products, variants


async def _ensure_variant(
    session: AsyncSession,
    product: Product,
    sku: str,
    name_en: str,
    name_ar: str,
    price: Decimal,
) -> ProductVariant:
    result = await session.execute(
        select(ProductVariant).where(
            ProductVariant.product_id == product.id,
            ProductVariant.sku == sku,
        )
    )
    variant = result.scalar_one_or_none()
    if variant is None:
        variant = ProductVariant(
            product_id=product.id,
            sku=sku,
            name_en=name_en,
            name_ar=name_ar,
            price=price,
        )
        session.add(variant)
        await session.flush()
    return variant


async def _ensure_recipes(
    session: AsyncSession,
    variants: dict[str, ProductVariant],
    ingredients: dict[str, Ingredient],
    units: dict[str, Unit],
) -> None:
    recipes = {
        "ESPRESSO": [("COFFEE_BEANS", Decimal("18"), "g")],
        "AMERICANO": [("COFFEE_BEANS", Decimal("18"), "g")],
        "CAPPUCCINO": [("MILK", Decimal("150"), "ml"), ("COFFEE_BEANS", Decimal("18"), "g")],
        "LATTE-S": [("MILK", Decimal("150"), "ml")],
        "LATTE-M": [("MILK", Decimal("200"), "ml")],
        "LATTE-L": [("MILK", Decimal("300"), "ml")],
        "ICED_COFFEE": [("MILK", Decimal("150"), "ml"), ("COFFEE_BEANS", Decimal("18"), "g")],
        "PROTEIN_COFFEE": [
            ("MILK", Decimal("100"), "ml"),
            ("COFFEE_BEANS", Decimal("18"), "g"),
            ("WHEY", Decimal("1"), "scoop"),
        ],
        "BANANA_PROTEIN_SHAKE": [
            ("MILK", Decimal("200"), "ml"),
            ("BANANA", Decimal("1"), "piece"),
            ("WHEY", Decimal("1"), "scoop"),
        ],
        "ICED_COFFEE_PROTEIN": [
            ("MILK", Decimal("150"), "ml"),
            ("COFFEE_BEANS", Decimal("18"), "g"),
            ("WHEY", Decimal("1"), "scoop"),
        ],
        "STRAWBERRY_SMOOTHIE": [
            ("MILK", Decimal("200"), "ml"),
            ("STRAWBERRY", Decimal("150"), "g"),
            ("GREEK_YOGURT", Decimal("100"), "g"),
        ],
        "GREEK_YOGURT_BOWL": [
            ("GREEK_YOGURT", Decimal("200"), "g"),
            ("BANANA", Decimal("1"), "piece"),
            ("GRANOLA", Decimal("50"), "g"),
        ],
        "BOTTLED_WATER": [("WATER_BOTTLE", Decimal("1"), "bottle")],
        "CHICKEN_WRAP": [
            ("TORTILLA", Decimal("1"), "piece"),
            ("CHICKEN", Decimal("50"), "g"),
            ("MOZZARELLA", Decimal("50"), "g"),
        ],
    }
    for variant_sku, items in recipes.items():
        variant = variants[variant_sku]
        result = await session.execute(
            select(RecipeVersion).where(RecipeVersion.variant_id == variant.id).limit(1)
        )
        if result.scalar_one_or_none() is not None:
            continue
        version = RecipeVersion(variant_id=variant.id, version_number=1, is_active=True)
        session.add(version)
        await session.flush()
        for ingredient_sku, quantity, unit_code in items:
            session.add(
                RecipeItem(
                    recipe_version_id=version.id,
                    ingredient_id=ingredients[ingredient_sku].id,
                    quantity=quantity,
                    unit_id=units[unit_code].id,
                )
            )


async def _ensure_modifiers(
    session: AsyncSession,
    products: dict[str, Product],
    ingredients: dict[str, Ingredient],
    units: dict[str, Unit],
) -> None:
    result = await session.execute(select(ModifierGroup).where(ModifierGroup.code == "NUTRITION"))
    group = result.scalar_one_or_none()
    if group is None:
        group = ModifierGroup(
            code="NUTRITION",
            name_en="Nutrition Options",
            name_ar="خيارات التغذية",
            min_select=0,
            max_select=4,
        )
        session.add(group)
        await session.flush()

    for sku in [
        "LATTE",
        "PROTEIN_COFFEE",
        "BANANA_PROTEIN_SHAKE",
        "ICED_COFFEE_PROTEIN",
        "STRAWBERRY_SMOOTHIE",
    ]:
        result = await session.execute(
            select(ProductModifierGroup).where(
                ProductModifierGroup.product_id == products[sku].id,
                ProductModifierGroup.modifier_group_id == group.id,
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(
                ProductModifierGroup(
                    product_id=products[sku].id,
                    modifier_group_id=group.id,
                )
            )

    await _ensure_modifier(
        session,
        group,
        "DOUBLE_WHEY",
        "Double Whey",
        "واي مضاعف",
        Decimal("40"),
        [
            {
                "effect_type": "MULTIPLY",
                "ingredient_id": ingredients["WHEY"].id,
                "multiply_factor": Decimal("2"),
            }
        ],
    )
    await _ensure_modifier(
        session,
        group,
        "NO_BANANA",
        "No Banana",
        "بدون موز",
        Decimal("0"),
        [{"effect_type": "REMOVE", "ingredient_id": ingredients["BANANA"].id}],
    )
    await _ensure_modifier(
        session,
        group,
        "LACTOSE_FREE",
        "Lactose-free Milk",
        "حليب خالي اللاكتوز",
        Decimal("10"),
        [
            {
                "effect_type": "REPLACE",
                "ingredient_id": ingredients["MILK"].id,
                "replace_with_ingredient_id": ingredients["LACTOSE_FREE_MILK"].id,
            }
        ],
    )
    await _ensure_modifier(
        session,
        group,
        "ADD_PEANUT_BUTTER",
        "Add Peanut Butter",
        "إضافة زبدة فول سوداني",
        Decimal("25"),
        [
            {
                "effect_type": "ADD",
                "ingredient_id": ingredients["PEANUT_BUTTER"].id,
                "quantity": Decimal("30"),
                "unit_id": units["g"].id,
            }
        ],
    )


async def _ensure_modifier(
    session: AsyncSession,
    group: ModifierGroup,
    code: str,
    name_en: str,
    name_ar: str,
    price_delta: Decimal,
    effects: list[dict],
) -> Modifier:
    result = await session.execute(
        select(Modifier).where(Modifier.modifier_group_id == group.id, Modifier.code == code)
    )
    modifier = result.scalar_one_or_none()
    if modifier is None:
        modifier = Modifier(
            modifier_group_id=group.id,
            code=code,
            name_en=name_en,
            name_ar=name_ar,
            price_delta=price_delta,
        )
        session.add(modifier)
        await session.flush()
    result = await session.execute(
        select(ModifierEffect.id).where(ModifierEffect.modifier_id == modifier.id).limit(1)
    )
    if result.scalar_one_or_none() is None:
        for effect in effects:
            session.add(ModifierEffect(modifier_id=modifier.id, **effect))
    return modifier
