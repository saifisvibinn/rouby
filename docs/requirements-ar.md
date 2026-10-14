# متطلبات نظام نقاط البيع والمخزون الذكي — مطعم Healthy Food & Coffee

> المصدر: وثيقة المتطلبات العربية الأصلية. المواصفات التقنية الإنجليزية في برومبت المشروع هي الحاكمة عند التعارض.

## 1. System Overview — فكرة السيستم

السيستم مسؤول عن 5 أجزاء أساسية:

1. **POS System**: تسجيل الأوردرات، الحسابات، الدفع، وطباعة الفواتير.
2. **Smart Inventory**: إدارة المخزون وخصم المكونات تلقائيًا.
3. **Recipe Management**: تحديد مكونات كل منتج وكمياتها.
4. **Cost & Profit Management**: حساب تكلفة كل منتج والمكسب الفعلي.
5. **Reports & Analytics**: تقارير المبيعات والمخزون والأرباح.

الأهم أن السيستم يكون قابلًا للتطوير: تبدأ بالمشروبات والأكل الصحي، وبعدها تضيف Wraps وSandwiches وSalads وأي منتجات جديدة من غير ما تحتاج تعيد بناء السيستم.

## 2. Smart Inventory Management — إدارة المخزون الذكية

المخزن يتابع كل مكون خام (وليس المنتجات النهائية فقط). أمثلة: Milk 20,000 ml، Whey Protein 100 scoops، Bananas 50 pieces، Yogurt 5,000 g، Coffee Beans 2,000 g، Mozzarella 3,000 g، Chicken Breast 5,000 g، Tortilla 100 pieces، Bottled Water 48 bottles.

كل مكون: اسم، SKU، كمية، وحدة قياس، تكلفة الوحدة، حد أدنى، صلاحية (إن وجدت)، مورد، مكان تخزين.

**Requirement:** Every ingredient must be tracked independently, and inventory must be deducted automatically based on the recipe of each sold product.

القدرات: إضافة مخزون، تعديل بصلاحيات، مشتريات، هالك، استهلاك داخلي، جرد فعلي، متابعة صلاحية، مكونات قربت تخلص.

## 3. Recipe Management — نظام الوصفات

صاحب المطعم يضيف منتجًا ويحدد مكوناته من غير مبرمج.

مثال Banana Protein Shake: Milk 200 ml + Banana 1 + Whey 1 scoop → خصم تلقائي عند البيع، تحديث مخزون، حساب تكلفة وإيراد وربح.

تغيير الوصفة (مثل اللبن 200→250 ml) يؤثر على الأوردرات الجديدة فقط مع الاحتفاظ بسجل الإصدارات للحسابات التاريخية.

## 4. Product Management

Product ≠ Ingredient. مثال: Chicken Wrap منتج؛ Chicken Breast وMozzarella مكونات. إضافة منتج جديد = بيانات فقط (منتج + وصفة + سعر).

## 5. Units & Measurements

kg, g, Liter, ml, Piece, Scoop, Bottle, Portion. تحويل تلقائي داخل نفس البعد. وحدة شراء / تخزين / استخدام منفصلة. رفض تحويل g↔ml بدون كثافة.

## 6. POS System

واجهة سريعة بفئات قابلة للتكوين. دفع: Cash, Card, Wallet, Split. حالات: Draft → Confirmed → Preparing → Completed / Cancelled. الخصم مرة واحدة عند Confirmed؛ إلغاء يعكس حسب سياسة الهالك.

## 7. Product Customization

معدّلات: إزالة، استبدال، مضاعفة، إضافات مدفوعة/مجانية، أحجام (S/M/L) بوصفات مختلفة. الخصم على الوصفة الفعلية.

## 8. Automatic Cost Calculation

تكلفة المنتج = Σ (كمية × تكلفة وحدة). مجمل الربح = صافي مبيعات − COGS. هامش مجمل الربح = مجمل الربح ÷ صافي المبيعات × 100. لقطة تكلفة عند البيع لا تتغير لاحقًا.

## 9. Purchasing & Suppliers

PO لا يزيد المخزون؛ الاستلام المؤكد يزيده. تتبع موردين وأسعار تاريخية.

## 10. Inventory Alerts

Low stock، صلاحية، منتجات غير متاحة، اقتراحات شراء، FEFO للباتشات.

## 11. Waste & Stock Adjustments

هالك بأسباب، فرق جرد، حركات عكسية فقط (لا حذف حركات قديمة).

## 12. Reports

مبيعات، مخزون، ربح (مجمل)، موظفين.

## 13. Database

Users, Roles, Products, Categories, Ingredients, Units, Recipes, Inventory, Stock Movements, Suppliers, POs, Goods Receipts, Sales, Payments, Waste, Stock Counts, Expenses — مع معاملات متكاملة ومنع تكرار الخصم.

## 14. Roles

Owner, Manager, Cashier, Inventory Staff + Audit Log.

## 15. Advanced / Future

Recipe versioning, multi-branch, multi-location, barcode, expiry, offline, kitchen display, menu availability.

## 16. Theoretical vs Actual

جرد يقارن النظري بالفعلي ويسجل الفرق وسببه.

## 17. Functional Requirements (ملخص)

FR-01…FR-14 Must Have؛ FR-15/16 Should Have؛ FR-17…20 Future في الوثيقة العربية (البرومبت الإنجليزي يرفع الباركود/الماسح لمرحلة 3B).

## 18. Non-Functional

Fast, Reliable, Secure, Auditable, Scalable, Consistent, Maintainable, Backup-ready.

## 19. Suggested Stack (عربي)

React + FastAPI + PostgreSQL (البرومبت الإنجليزي يثبت التفاصيل).

## 20. Workflow

استلام مكونات → وصفات → بيع → خصم مرة → تكلفة وإيراد → تقارير.

## 21. قرارات ما قبل البرمجة

أجهزة الكاشير/تابلت/موبايل؛ Offline لاحقًا؛ فرع واحد مع جاهزية تعدد؛ مجمل ربح أولاً؛ دورة مشتريات كاملة في الـ MVP.
