from pathlib import Path

from scripts.seed_data import PRODUCT_PHOTOS, PRODUCTS, product_img


def test_seed_photos_cover_twenty_distinct_demo_products():
    assert len(PRODUCT_PHOTOS) == 20
    assert len(set(PRODUCT_PHOTOS.values())) == 20
    assert set(PRODUCT_PHOTOS).issubset({product["slug"] for product in PRODUCTS})


def test_seed_photo_url_is_pexels_for_curated_products_and_picsum_for_rest():
    curated = next(
        product for product in PRODUCTS if product["slug"] == "samsung-galaxy-a34-5g"
    )
    uncurated = next(
        product for product in PRODUCTS if product["slug"] == "solar-led-lantern-30w"
    )

    assert product_img(curated).startswith("https://images.pexels.com/photos/")
    assert product_img(uncurated).startswith("https://picsum.photos/seed/")


def test_homepage_has_five_photo_promotion_cards():
    template = (
        Path(__file__).resolve().parents[2]
        / "bot"
        / "web_app"
        / "templates"
        / "index.html"
    )
    content = template.read_text(encoding="utf-8")

    assert content.count('class="promo-card') == 5
    assert content.count("images.pexels.com/photos/") >= 5
