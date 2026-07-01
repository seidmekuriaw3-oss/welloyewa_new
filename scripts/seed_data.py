"""
Wolloyewa Store — Database Seed Script
=======================================
Populates the database with:
  - 1 system vendor user + vendor account
  - 10 categories (6 root + 4 sub)
  - 30 Ethiopian sample products across categories
  - 1 product image per product

Run:
    python3 scripts/seed_data.py
"""

import asyncio
import sys
import os
from decimal import Decimal
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, text

from core.config import settings

# Import ALL models so SQLAlchemy can resolve cross-model relationships
import apps.users.models        # noqa: F401 — User, Vendor, UserAddress
import apps.orders.models       # noqa: F401 — Order, OrderItem
import apps.products.models     # noqa: F401 — Product, Category, Review, ProductImage
import apps.inventory.models    # noqa: F401 — Inventory
import apps.marketing.models    # noqa: F401 — Coupon, Campaign
import apps.support.models      # noqa: F401 — Ticket

from apps.users.models import User, Vendor
from apps.products.models import Category, Product, ProductImage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_utc() -> datetime:
    # Use naive datetime — DB columns are TIMESTAMP WITHOUT TIME ZONE
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

CATEGORIES = [
    dict(name="Electronics",       name_am="ኤሌክትሮኒክስ",   slug="electronics",    description="Phones, TVs, and gadgets",            description_am="ስልኮች፣ ቴሌቪዥኖች እና ጂንጅሮ",      display_order=1, is_featured=True,  icon="📱"),
    dict(name="Clothing",          name_am="ልብስ",          slug="clothing",        description="Traditional and modern clothing",       description_am="ባህላዊ እና ዘመናዊ ልብስ",          display_order=2, is_featured=True,  icon="👗"),
    dict(name="Food & Spices",     name_am="ምግብ እና ቅመማ",   slug="food",            description="Ethiopian food and spices",             description_am="የኢትዮጵያ ምግቦች እና ቅመሞች",      display_order=3, is_featured=True,  icon="🌶️"),
    dict(name="Beauty & Care",     name_am="ውበት",          slug="beauty",          description="Skin care and cosmetics",               description_am="የቆዳ ክብካቤ እና ሜካፕ",          display_order=4, is_featured=False, icon="💄"),
    dict(name="Home & Kitchen",    name_am="ቤት እና ወጥቤት",  slug="home",            description="Furniture and kitchen appliances",      description_am="የቤት እቃዎች እና የኮሽና ዕቃዎች",    display_order=5, is_featured=True,  icon="🏠"),
    dict(name="Sports & Fitness",  name_am="ስፖርት",         slug="sports",          description="Sporting goods and fitness equipment",  description_am="የስፖርት ዕቃዎች",                display_order=6, is_featured=False, icon="⚽"),
    dict(name="Smartphones",       name_am="ስማርት ስልኮች",   slug="smartphones",     description="Mobile phones",                         description_am="የሞባይል ስልኮች",                display_order=7, is_featured=False, icon="📱", parent_slug="electronics"),
    dict(name="Habesha Kemis",     name_am="ሀበሻ ቀሚስ",     slug="habesha-kemis",   description="Traditional Ethiopian dresses",         description_am="ባህላዊ ሀበሻ ቀሚሶች",            display_order=8, is_featured=True,  icon="👘", parent_slug="clothing"),
    dict(name="Injera & Teff",     name_am="እንጀራ እና ጤፍ",  slug="injera-teff",     description="Injera, teff, and related products",   description_am="እንጀራ፣ ጤፍ እና ተዛማጅ ምርቶች", display_order=9, is_featured=False, icon="🫓", parent_slug="food"),
    dict(name="Coffee",            name_am="ቡና",           slug="coffee",          description="Ethiopian coffee varieties",             description_am="የኢትዮጵያ ቡና ዓይነቶች",          display_order=10, is_featured=True, icon="☕", parent_slug="food"),
]

# product images — curated free public URLs that work reliably
# Using picsum.photos with seeds for consistent results
def img(seed: int, w: int = 400, h: int = 400) -> str:
    return f"https://picsum.photos/seed/{seed}/{w}/{h}"


PRODUCTS = [
    # ── Electronics ──────────────────────────────────────────────────────────
    dict(
        name="Samsung Galaxy A34 5G",        name_am="ሳምሱንግ ጋላክሲ A34 5G",
        slug="samsung-galaxy-a34-5g",
        description="Latest Samsung smartphone with 5G connectivity, 128GB storage and 50MP camera.",
        description_am="5G ኔትወርክ፣ 128GB ማህደረ ትዝታ እና 50MP ካሜራ ያለው ሳምሱንግ ስልክ።",
        short_description="5G ስማርት ፎን — 128GB / 50MP",
        category_slug="smartphones", category_type="electronics",
        price=Decimal("18500.00"), stock_quantity=25, sku="ELEC-SAM-A34",
        is_featured=True, tags=["samsung", "smartphone", "5g"],
        image_seed=10,
    ),
    dict(
        name="Tecno Spark 20 Pro",            name_am="ቴክኖ ስፓርክ 20 ፕሮ",
        slug="tecno-spark-20-pro",
        description="Affordable Tecno smartphone with 256GB storage and 108MP camera.",
        description_am="256GB ማህደረ ትዝታ እና 108MP ካሜራ ያለው ቴክኖ ስልክ።",
        short_description="256GB / 108MP ካሜራ",
        category_slug="smartphones", category_type="electronics",
        price=Decimal("12800.00"), stock_quantity=40, sku="ELEC-TECNO-S20",
        is_featured=False, tags=["tecno", "smartphone", "affordable"],
        image_seed=20,
    ),
    dict(
        name="Itel Vision 3 Plus",            name_am="ኢቴል ቪዥን 3 ፕሉስ",
        slug="itel-vision-3-plus",
        description="Budget-friendly smartphone with large 5000mAh battery and 6.6-inch display.",
        description_am="ትልቅ 5000mAh ባትሪ እና 6.6 ኢንች ስክሪን ያለው ስልክ።",
        short_description="5000mAh ባትሪ — ዋጋ ቆጣቢ",
        category_slug="smartphones", category_type="electronics",
        price=Decimal("6500.00"), stock_quantity=60, sku="ELEC-ITEL-V3",
        is_featured=False, tags=["itel", "budget", "smartphone"],
        image_seed=30,
    ),
    dict(
        name="Sony 43-inch Smart TV",         name_am="ሶኒ 43 ኢንች ስማርት ቲቪ",
        slug="sony-43-smart-tv",
        description="Sony Bravia 43-inch Full HD Smart LED TV with built-in Wi-Fi and Netflix.",
        description_am="ሶኒ ብራቪያ 43 ኢንች ስማርት ቲቪ፣ Wi-Fi እና Netflix ቀጥተኛ ድጋፍ።",
        short_description="43ኢ FullHD Smart TV",
        category_slug="electronics", category_type="electronics",
        price=Decimal("32000.00"), stock_quantity=10, sku="ELEC-SONY-TV43",
        is_featured=True, tags=["tv", "smart tv", "sony"],
        image_seed=40,
    ),
    dict(
        name="HP Laptop 15s (Intel i5)",      name_am="HP ላፕቶፕ 15s (Intel i5)",
        slug="hp-laptop-15s-i5",
        description="HP 15s laptop with Intel Core i5, 8GB RAM, 512GB SSD, Windows 11.",
        description_am="Intel Core i5፣ 8GB RAM፣ 512GB SSD እና Windows 11 ያለው HP ላፕቶፕ።",
        short_description="i5 / 8GB / 512GB SSD",
        category_slug="electronics", category_type="electronics",
        price=Decimal("68000.00"), stock_quantity=8, sku="ELEC-HP-15S-I5",
        is_featured=True, tags=["laptop", "hp", "intel"],
        image_seed=50,
    ),

    # ── Clothing / Habesha Kemis ─────────────────────────────────────────────
    dict(
        name="White Habesha Kemis (Women)",   name_am="ነጭ ሀበሻ ቀሚስ (ሴቶች)",
        slug="white-habesha-kemis-women",
        description="Traditional Ethiopian hand-woven white dress with Tilet border pattern. Sizes S–XL.",
        description_am="ባህላዊ የእጅ ሥራ ነጭ ሀበሻ ቀሚስ፣ ቲሌት ጥለት። ሳይዝ S–XL።",
        short_description="የቲሌት ጥለት ሀበሻ ቀሚስ",
        category_slug="habesha-kemis", category_type="clothing",
        price=Decimal("3500.00"), stock_quantity=50, sku="CLTH-HK-W-001",
        is_featured=True, is_on_sale=False, tags=["habesha", "kemis", "traditional", "women"],
        image_seed=60,
    ),
    dict(
        name="Habesha Netela Shawl",          name_am="ሀበሻ ነጠላ",
        slug="habesha-netela-shawl",
        description="Lightweight traditional Ethiopian netela shawl with decorative border.",
        description_am="ቀላል ክብደት ያለው ባህላዊ ሀበሻ ነጠላ።",
        short_description="ባህላዊ ሀበሻ ነጠላ",
        category_slug="habesha-kemis", category_type="clothing",
        price=Decimal("1200.00"), stock_quantity=80, sku="CLTH-NT-001",
        is_featured=False, tags=["netela", "shawl", "traditional"],
        image_seed=70,
    ),
    dict(
        name="Men's Habesha Suit (Suit & Gabi)", name_am="የወንዶች ሀበሻ ካባ (ጋቢ)",
        slug="mens-habesha-gabi-suit",
        description="Traditional men's suit with white Gabi and matching pants. Perfect for holidays.",
        description_am="ባህላዊ የወንዶች ሀበሻ ካባ እና ሱሪ፣ ለበዓላት ተስማሚ።",
        short_description="የወንዶች ሀበሻ ካባ ዕቃ",
        category_slug="habesha-kemis", category_type="clothing",
        price=Decimal("4800.00"), stock_quantity=30, sku="CLTH-HG-M-001",
        is_featured=True, tags=["habesha", "gabi", "men", "traditional"],
        image_seed=80,
    ),
    dict(
        name="Nike Air Max 270 (Sneakers)",   name_am="ናይኪ አየር ማክስ 270",
        slug="nike-air-max-270",
        description="Nike Air Max 270 running sneakers. Sizes 39–45. Black/White.",
        description_am="ናይኪ አየር ማክስ 270 ሩጫ ጫማዎች። ሳይዝ 39–45።",
        short_description="ናይኪ ሩጫ ጫማ ሳይዝ 39–45",
        category_slug="clothing", category_type="clothing",
        price=Decimal("7200.00"), stock_quantity=35, sku="CLTH-NK-AM270",
        is_featured=False, tags=["nike", "sneakers", "shoes"],
        image_seed=90,
    ),
    dict(
        name="Adidas Trefoil T-Shirt (Men)",  name_am="አዲዳስ ቲሸርት (ወንዶች)",
        slug="adidas-trefoil-tshirt-men",
        description="Classic Adidas Originals Trefoil men's t-shirt. Sizes S–XXL.",
        description_am="ክላሲክ አዲዳስ ቲሸርት ለወንዶች። ሳይዝ S–XXL።",
        short_description="አዲዳስ ክላሲክ ቲሸርት",
        category_slug="clothing", category_type="clothing",
        price=Decimal("1800.00"), stock_quantity=70, sku="CLTH-ADI-TS-M",
        is_featured=False, is_on_sale=True, tags=["adidas", "t-shirt", "men"],
        image_seed=100,
    ),

    # ── Food & Spices ────────────────────────────────────────────────────────
    dict(
        name="Teff Flour (5kg)",              name_am="ጤፍ ዱቄት (5 ኪሎ)",
        slug="teff-flour-5kg",
        description="100% pure Ethiopian teff flour, stone-ground. 5kg bag.",
        description_am="100% ንጹህ የኢትዮጵያ ጤፍ ዱቄት፣ ድንጋይ ወፍጮ። 5 ኪሎ ቦርሳ።",
        short_description="ንጹህ ጤፍ ዱቄት — 5 ኪሎ",
        category_slug="injera-teff", category_type="food",
        price=Decimal("320.00"), stock_quantity=200, sku="FOOD-TEFF-5KG",
        is_featured=True, tags=["teff", "flour", "injera", "gluten-free"],
        image_seed=110,
    ),
    dict(
        name="Berbere Spice Mix (500g)",       name_am="በርበሬ (500ግ)",
        slug="berbere-spice-mix-500g",
        description="Authentic Ethiopian berbere spice blend. Hot and aromatic. 500g.",
        description_am="ቀጥተኛ የኢትዮጵያ በርበሬ ቅምሻ። ቀይ እና መዓዛ ያለው። 500ግ።",
        short_description="ቀጥተኛ ኢትዮጵያ በርበሬ",
        category_slug="food", category_type="food",
        price=Decimal("180.00"), stock_quantity=300, sku="FOOD-BERB-500G",
        is_featured=True, tags=["berbere", "spice", "traditional", "hot"],
        image_seed=120,
    ),
    dict(
        name="Mitmita Spice (250g)",           name_am="ሚጥሚጣ (250ግ)",
        slug="mitmita-spice-250g",
        description="Ethiopian mitmita — fiery bird's eye chili blend. 250g.",
        description_am="የኢትዮጵያ ሚጥሚጣ — ጥሩ ቅምሻ። 250ግ።",
        short_description="ሚጥሚጣ ቅምሻ 250ግ",
        category_slug="food", category_type="food",
        price=Decimal("120.00"), stock_quantity=250, sku="FOOD-MITM-250G",
        is_featured=False, tags=["mitmita", "spice", "chili", "hot"],
        image_seed=130,
    ),
    dict(
        name="Yirgacheffe Coffee Beans (1kg)", name_am="ዮርጋጨፈ ቡና (1 ኪሎ)",
        slug="yirgacheffe-coffee-beans-1kg",
        description="Single-origin Yirgacheffe whole coffee beans. Light roast. 1kg.",
        description_am="ዮርጋጨፈ ቡና ፍሬ፣ ቀለል ያለ ቃጠሎ። 1 ኪሎ።",
        short_description="ዮርጋጨፈ ቡና — 1 ኪሎ",
        category_slug="coffee", category_type="food",
        price=Decimal("850.00"), stock_quantity=150, sku="FOOD-YRG-1KG",
        is_featured=True, tags=["coffee", "yirgacheffe", "beans", "light roast"],
        image_seed=140,
    ),
    dict(
        name="Sidama Coffee Ground (500g)",    name_am="ሲዳማ ቡና ዱቄት (500ግ)",
        slug="sidama-coffee-ground-500g",
        description="Sidama single-origin ground coffee. Medium roast. 500g bag.",
        description_am="ሲዳማ ቡና ዱቄት፣ መካከለኛ ቃጠሎ። 500ግ ቦርሳ።",
        short_description="ሲዳማ ቡና ዱቄት 500ግ",
        category_slug="coffee", category_type="food",
        price=Decimal("480.00"), stock_quantity=180, sku="FOOD-SID-GND-500G",
        is_featured=False, tags=["coffee", "sidama", "ground"],
        image_seed=150,
    ),
    dict(
        name="Niter Kibbeh (Spiced Butter 500g)", name_am="ንጥር ቅቤ (500ግ)",
        slug="niter-kibbeh-500g",
        description="Traditional Ethiopian spiced clarified butter (Niter Kibbeh). 500g jar.",
        description_am="ባህላዊ ኢትዮጵያ ንጥር ቅቤ። 500ግ ዕቃ።",
        short_description="ባህላዊ ንጥር ቅቤ 500ግ",
        category_slug="food", category_type="food",
        price=Decimal("290.00"), stock_quantity=100, sku="FOOD-NITK-500G",
        is_featured=False, tags=["niter kibbeh", "butter", "traditional", "cooking"],
        image_seed=160,
    ),

    # ── Beauty & Care ────────────────────────────────────────────────────────
    dict(
        name="Argan Oil Shampoo (400ml)",      name_am="አርጋን ኦይል ሻምፑ (400ml)",
        slug="argan-oil-shampoo-400ml",
        description="Nourishing argan oil shampoo for all hair types. Sulfate-free.",
        description_am="ለሁሉም የጸጉር ዓይነቶች ተስማሚ አርጋን ኦይል ሻምፑ።",
        short_description="አርጋን ሻምፑ — ሰልፌት ነፃ",
        category_slug="beauty", category_type="beauty",
        price=Decimal("420.00"), stock_quantity=90, sku="BEAU-ARGSH-400",
        is_featured=False, tags=["shampoo", "argan", "hair care"],
        image_seed=170,
    ),
    dict(
        name="Ethiopian Rose Face Cream (50ml)", name_am="ኢትዮጵያ ጸዳ ቅባት (50ml)",
        slug="ethiopian-rose-face-cream-50ml",
        description="Natural Ethiopian rose water face moisturizer. For all skin types.",
        description_am="ተፈጥሯዊ የኢትዮጵያ ጸዳ ቅባት። ለሁሉም የቆዳ ዓይነቶች።",
        short_description="ጸዳ ቅባት — ሁሉም ቆዳ",
        category_slug="beauty", category_type="beauty",
        price=Decimal("280.00"), stock_quantity=120, sku="BEAU-ROFC-50",
        is_featured=True, tags=["face cream", "rose water", "natural", "skin care"],
        image_seed=180,
    ),
    dict(
        name="Black Seed (Tikur Azmud) Oil 250ml", name_am="ጥቁር አዝሙድ ዘይት (250ml)",
        slug="black-seed-oil-250ml",
        description="Cold-pressed Ethiopian black seed oil. 250ml bottle.",
        description_am="ቀዝቃዛ ቅዝቃዜ ጥቁር አዝሙድ ዘይት። 250ml ጠርሙስ።",
        short_description="ጥቁር አዝሙድ ዘይት 250ml",
        category_slug="beauty", category_type="beauty",
        price=Decimal("350.00"), stock_quantity=80, sku="BEAU-BSO-250",
        is_featured=False, tags=["black seed", "oil", "natural", "health"],
        image_seed=190,
    ),

    # ── Home & Kitchen ───────────────────────────────────────────────────────
    dict(
        name="Ethiopian Coffee Ceremony Set",  name_am="የቡና ሥርዓት ዕቃ ስብስብ",
        slug="ethiopian-coffee-ceremony-set",
        description="Complete Ethiopian coffee ceremony set: Jebena, 6 Sini cups, and Rekebot stand.",
        description_am="ሙሉ የቡና ሥርዓት ዕቃ፣ ጀበና፣ 6 ሲኒ እና ርቀቦት ጨምሮ።",
        short_description="ጀበና፣ ሲኒ እና ርቀቦት ስብስብ",
        category_slug="home", category_type="home",
        price=Decimal("1850.00"), stock_quantity=40, sku="HOME-COFF-SET-01",
        is_featured=True, tags=["coffee ceremony", "jebena", "traditional", "home"],
        image_seed=200,
    ),
    dict(
        name="Injera Basket (Mesob)",          name_am="መሶብ",
        slug="injera-mesob-basket",
        description="Handmade traditional Ethiopian Mesob woven straw basket for injera.",
        description_am="ባህላዊ የኢትዮጵያ መሶብ — የእጅ ሥራ።",
        short_description="ባህላዊ የእጅ ሥራ መሶብ",
        category_slug="home", category_type="home",
        price=Decimal("950.00"), stock_quantity=55, sku="HOME-MESOB-001",
        is_featured=False, tags=["mesob", "basket", "traditional", "handmade"],
        image_seed=210,
    ),
    dict(
        name="Non-stick Cooking Pot (3L)",     name_am="ኖን-ስቲክ ድስት (3 ሊትር)",
        slug="nonstick-cooking-pot-3l",
        description="Heavy-gauge aluminum non-stick cooking pot. 3 liters. Induction compatible.",
        description_am="ጠንካራ አልሙኒየም ኖን-ስቲክ ድስት። 3 ሊትር።",
        short_description="3ሊ ኖን-ስቲክ ድስት",
        category_slug="home", category_type="home",
        price=Decimal("680.00"), stock_quantity=75, sku="HOME-NSP-3L",
        is_featured=False, tags=["pot", "cooking", "kitchen", "non-stick"],
        image_seed=220,
    ),
    dict(
        name="Solar LED Lantern (30W)",        name_am="ሶላር LED ፋኖስ (30W)",
        slug="solar-led-lantern-30w",
        description="30W solar-powered rechargeable LED lantern with USB charging port. 12hr runtime.",
        description_am="30W ሶላር LED ፋኖስ፣ USB ቻርጅ ወደብ ያለው። 12 ሰዓት ሥራ።",
        short_description="ሶላር LED ፋኖስ — 12ሰ ዕድሜ",
        category_slug="home", category_type="home",
        price=Decimal("1200.00"), stock_quantity=60, sku="HOME-SOLLED-30",
        is_featured=True, tags=["solar", "lantern", "light", "usb"],
        image_seed=230,
    ),

    # ── Sports & Fitness ─────────────────────────────────────────────────────
    dict(
        name="Adjustable Dumbbell Set (20kg)", name_am="ዳምቤል ስብስብ (20 ኪሎ)",
        slug="adjustable-dumbbell-set-20kg",
        description="Adjustable cast-iron dumbbell set. Total 20kg. Includes carrying case.",
        description_am="20 ኪሎ ዳምቤል ስብስብ። ቦርሳ ጨምሮ።",
        short_description="20ኪሎ ዳምቤል ስብስብ",
        category_slug="sports", category_type="sports",
        price=Decimal("3200.00"), stock_quantity=20, sku="SPRT-DUMB-20KG",
        is_featured=False, tags=["dumbbell", "fitness", "gym", "weights"],
        image_seed=240,
    ),
    dict(
        name="Yoga Mat (6mm, Non-slip)",       name_am="ዮጋ ምንጣፍ (6mm)",
        slug="yoga-mat-6mm-nonslip",
        description="Eco-friendly 6mm thick non-slip yoga mat. 183×61cm. Carry strap included.",
        description_am="ኤኮ-ፍሬንድሊ 6mm ዮጋ ምንጣፍ። 183×61cm። ማሰሪያ ጨምሮ።",
        short_description="6mm ዮጋ ምንጣፍ — ኤኮ",
        category_slug="sports", category_type="sports",
        price=Decimal("650.00"), stock_quantity=85, sku="SPRT-YOGA-6MM",
        is_featured=False, tags=["yoga", "mat", "fitness", "eco"],
        image_seed=250,
    ),
    dict(
        name="Football (Size 5)",              name_am="እግር ኳስ (ሳይዝ 5)",
        slug="football-size-5",
        description="FIFA-approved size 5 football. Durable PU leather. Training and match.",
        description_am="FIFA ሳይዝ 5 እግር ኳስ። ጠንካራ PU ቆዳ።",
        short_description="FIFA ሳይዝ 5 ኳስ",
        category_slug="sports", category_type="sports",
        price=Decimal("420.00"), stock_quantity=100, sku="SPRT-FTBL-S5",
        is_featured=True, tags=["football", "soccer", "size 5", "sports"],
        image_seed=260,
    ),
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------

async def seed(session: AsyncSession) -> None:
    print("🌱 Starting Wolloyewa seed...")

    # ── 1. Check existing data ────────────────────────────────────────────────
    existing_products = (await session.execute(select(Product))).scalars().all()
    if existing_products:
        print(f"   ⚠️  Database already has {len(existing_products)} products — skipping (run with --force to re-seed).")
        if "--force" not in sys.argv:
            return

    # ── 2. Vendor user ───────────────────────────────────────────────────────
    print("   👤 Creating system vendor user…")
    existing_user = (await session.execute(
        select(User).where(User.telegram_id == 999_999_999)
    )).scalars().first()

    if not existing_user:
        vendor_user = User(
            telegram_id=999_999_999,
            username="wolloyewa_system",
            first_name="ወሎየዋ",
            last_name="ሱቅ",
            role="vendor",
            status="active",
            language="am",
            is_verified=True,
        )
        session.add(vendor_user)
        await session.flush()
        print(f"      ✅ User created (id={vendor_user.id})")
    else:
        vendor_user = existing_user
        print(f"      ♻️  User exists (id={vendor_user.id})")

    # ── 3. Vendor record ─────────────────────────────────────────────────────
    existing_vendor = (await session.execute(
        select(Vendor).where(Vendor.user_id == vendor_user.id)
    )).scalars().first()

    if not existing_vendor:
        print("   🏪 Creating system vendor…")
        vendor = Vendor(
            user_id=vendor_user.id,
            business_name="ወሎየዋ ዋና ሱቅ",
            description="የወሎየዋ ዋና ሱቅ — የኢትዮጵያ ምርጥ ምርቶች ያሉበት ቦታ",
            business_address="አዲስ አበባ፣ ኢትዮጵያ",
            business_phone="+251911000000",
            business_email="store@wolloyewa.et",
            is_approved=True,
            approved_at=now_utc(),
            rating=5.0,
            total_products=0,
        )
        session.add(vendor)
        await session.flush()
        print(f"      ✅ Vendor created (id={vendor.id})")
    else:
        vendor = existing_vendor
        print(f"      ♻️  Vendor exists (id={vendor.id})")

    # ── 4. Categories ────────────────────────────────────────────────────────
    print("   📂 Seeding categories…")
    cat_by_slug: dict[str, Category] = {}

    # Build root cats first, then children
    root_cats = [c for c in CATEGORIES if "parent_slug" not in c]
    child_cats = [c for c in CATEGORIES if "parent_slug" in c]

    for c_data in root_cats + child_cats:
        existing = (await session.execute(
            select(Category).where(Category.slug == c_data["slug"])
        )).scalars().first()

        if existing:
            cat_by_slug[c_data["slug"]] = existing
            print(f"      ♻️  {c_data['name']}")
            continue

        parent_id = None
        if "parent_slug" in c_data:
            parent = cat_by_slug.get(c_data["parent_slug"])
            parent_id = parent.id if parent else None

        cat = Category(
            name=c_data["name"],
            name_am=c_data["name_am"],
            slug=c_data["slug"],
            description=c_data.get("description"),
            description_am=c_data.get("description_am"),
            parent_id=parent_id,
            display_order=c_data.get("display_order", 0),
            is_active=True,
            is_featured=c_data.get("is_featured", False),
            product_count=0,
        )
        session.add(cat)
        await session.flush()
        cat_by_slug[c_data["slug"]] = cat
        print(f"      ✅ {c_data['name']} (id={cat.id})")

    # ── 5. Products ──────────────────────────────────────────────────────────
    print("   📦 Seeding products…")
    created_count = 0

    for p in PRODUCTS:
        existing = (await session.execute(
            select(Product).where(Product.slug == p["slug"])
        )).scalars().first()

        if existing:
            print(f"      ♻️  {p['name']}")
            continue

        cat = cat_by_slug.get(p["category_slug"])
        cat_id = cat.id if cat else None

        seed_num = p.get("image_seed", 1)
        product = Product(
            vendor_id=vendor.id,
            name=p["name"],
            name_am=p.get("name_am"),
            slug=p["slug"],
            description=p.get("description"),
            description_am=p.get("description_am"),
            short_description=p.get("short_description"),
            category_id=cat_id,
            category_type=p.get("category_type"),
            price=p["price"],
            stock_quantity=p["stock_quantity"],
            low_stock_threshold=5,
            sku=p["sku"],
            status="active",
            is_featured=p.get("is_featured", False),
            is_on_sale=p.get("is_on_sale", False),
            tags=p.get("tags", []),
            images=[img(seed_num, 600, 600)],
            rating=0.0,
            reviews_count=0,
            views_count=0,
            sales_count=0,
        )
        session.add(product)
        await session.flush()

        # Product image
        seed_num = p.get("image_seed", 1)
        image = ProductImage(
            product_id=product.id,
            image_url=img(seed_num, 600, 600),
            thumbnail_url=img(seed_num, 200, 200),
            alt_text=p["name"],
            display_order=0,
            is_primary=True,
        )
        session.add(image)

        print(f"      ✅ {p['name']} — {p['price']} ETB")
        created_count += 1

    # ── 6. Update category product counts ───────────────────────────────────
    print("   🔢 Updating category product counts…")
    for slug, cat in cat_by_slug.items():
        count_result = await session.execute(
            select(Product).where(Product.category_id == cat.id, Product.status == "active")
        )
        count = len(count_result.scalars().all())
        cat.product_count = count

    await session.commit()
    print(f"\n✅ Seed complete! Created {created_count} products across {len(cat_by_slug)} categories.")
    print(f"   Vendor: '{vendor.business_name}' (id={vendor.id})")


async def main() -> None:
    import re
    db_url = str(settings.DATABASE_URL)
    # Strip sslmode (asyncpg uses connect_args, not URL params)
    db_url = re.sub(r'[?&]sslmode=[^&]*', '', db_url).rstrip('?')
    db_url = (db_url
              .replace("postgresql+asyncpg://", "postgresql+asyncpg://")
              .replace("postgresql://", "postgresql+asyncpg://")
              .replace("postgres://", "postgresql+asyncpg://"))

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
