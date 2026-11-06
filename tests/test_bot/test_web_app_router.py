"""Focused tests for Telegram Mini App router primitives and page routes."""

import hashlib
import hmac
import json
import time
import urllib.parse
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError


def make_init_data(bot_token="test-token", user=None, auth_date=None):
    values = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "query-1",
        "user": json.dumps(user or {"id": 42, "first_name": "Test"}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urllib.parse.urlencode(values)


def test_verify_telegram_init_data_accepts_valid_payload():
    from bot.web_app.router import _verify_telegram_init_data

    payload = make_init_data(user={"id": 42, "first_name": "A"})

    assert _verify_telegram_init_data(payload, "test-token") == {"id": 42, "first_name": "A"}
    assert _verify_telegram_init_data(payload, "") is None


def test_verify_telegram_init_data_rejects_bad_hash_old_and_malformed_payloads():
    from bot.web_app.router import _verify_telegram_init_data

    valid = make_init_data()
    assert _verify_telegram_init_data(valid.replace("hash=", "hash=bad"), "test-token") is None
    assert _verify_telegram_init_data("not-valid-query", "test-token") is None
    assert _verify_telegram_init_data("auth_date=abc&hash=bad", "test-token") is None
    assert _verify_telegram_init_data(
        make_init_data(auth_date=int(time.time()) - 7200), "test-token"
    ) is None


@pytest.mark.parametrize("user_id", [True, 0, "42", -1])
def test_verify_telegram_init_data_rejects_invalid_user_ids(user_id):
    from bot.web_app.router import _verify_telegram_init_data

    payload = make_init_data(user={"id": user_id})

    assert _verify_telegram_init_data(payload, "test-token") is None


def test_verify_telegram_init_data_rejects_duplicate_fields():
    from bot.web_app.router import _verify_telegram_init_data

    payload = make_init_data()

    assert _verify_telegram_init_data(f"{payload}&user=%7B%22id%22%3A99%7D", "test-token") is None


def test_verify_telegram_init_data_handles_missing_user_and_invalid_json():
    from bot.web_app.router import _verify_telegram_init_data

    values = {"auth_date": str(int(time.time())), "query_id": "query-1"}
    check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", b"test-token", hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    no_user = urllib.parse.urlencode(values)
    assert _verify_telegram_init_data(no_user, "test-token") is None

    values = {"auth_date": str(int(time.time())), "user": "not-json"}
    check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", b"test-token", hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    assert _verify_telegram_init_data(urllib.parse.urlencode(values), "test-token") is None


def test_verify_telegram_init_data_rejects_missing_auth_date():
    from bot.web_app.router import _verify_telegram_init_data

    values = {"query_id": "query-1", "user": json.dumps({"id": 42})}
    check = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", b"test-token", hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()

    assert _verify_telegram_init_data(urllib.parse.urlencode(values), "test-token") is None


def test_checkout_schemas_validate_cart_constraints():
    from bot.web_app.router import CartItemIn, CheckoutRequest, MyOrdersRequest

    item = CartItemIn(id=1, name="Phone", price=10.5, qty=2)
    request = CheckoutRequest(
        items=[item],
        full_name="Test User",
        phone="0912345678",
        city="Addis Ababa",
        address="Main street",
        payment_method="cod",
    )

    assert request.items[0].qty == 2
    assert MyOrdersRequest().init_data is None

    with pytest.raises(ValidationError):
        CartItemIn(id=1, name="Phone", price=-1, qty=1)
    with pytest.raises(ValidationError):
        CartItemIn(id=1, name="Phone", price=1, qty=0)
    with pytest.raises(ValidationError):
        CheckoutRequest(
            items=[item],
            full_name="Test User",
            phone="0912345678",
            city="Addis Ababa",
            address="Main street",
            payment_method="unknown",
        )
def test_admin_product_payload_normalizes_and_validates_catalog_fields():
    from bot.web_app.router import WebAdminProductCreate

    product = WebAdminProductCreate(
        vendor_id=3,
        name="  Kettle ",
        name_am="  ማፍያ ",
        price="125.00",
        stock_quantity=4,
        sku="  kt-1 ",
    )

    assert product.name == "Kettle"
    assert product.name_am == "ማፍያ"
    assert product.sku == "kt-1"

    with pytest.raises(ValidationError):
        WebAdminProductCreate(
            vendor_id=3,
            name=" ",
            price="-1",
            stock_quantity=0,
            sku="SKU",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("function_name", "template_name"),
    [
        ("index_page", "index.html"),
        ("login_page", "login.html"),
        ("register_page", "register.html"),
        ("forgot_password_page", "forgot_password.html"),
        ("categories_page", "categories.html"),
        ("dashboard_page", "profile.html"),
        ("vendor_products_page", "vendor_products.html"),
        ("admin_page", "admin.html"),
        ("profile_page", "profile.html"),
        ("cart_page", "cart.html"),
        ("checkout_page", "checkout.html"),
        ("orders_page", "orders.html"),
    ],
)
async def test_page_routes_render_expected_templates(function_name, template_name):
    import bot.web_app.router as router

    request = Mock()
    response = await getattr(router, function_name)(request)

    assert response.template.name == template_name
    if function_name == "dashboard_page":
        assert response.context["page"] == "profile"
    assert response.context["request"] is request


@pytest.mark.asyncio
async def test_product_page_includes_product_id():
    from bot.web_app.router import product_page

    request = Mock()
    response = await product_page(request, 17)

    assert response.template.name == "product.html"
    assert response.context["product_id"] == 17


@pytest.mark.asyncio
async def test_login_page_uses_requested_supported_language():
    from types import SimpleNamespace

    from bot.web_app.router import login_page

    request = SimpleNamespace(query_params={"lang": "en"})
    response = await login_page(request)

    assert response.context["page_language"] == "en"
    assert response.context["login_text"]["heading"] == "Sign in to your account"


@pytest.mark.asyncio
async def test_login_page_supports_afaan_oromoo():
    from types import SimpleNamespace

    from bot.web_app.router import login_page

    request = SimpleNamespace(query_params={"lang": "om"})
    response = await login_page(request)

    assert response.context["page_language"] == "om"
    assert response.context["login_text"]["heading"] == "Herrega kee seeni"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "expected", "expected_title"),
    [
        ("en", "Your account", "Profile and settings — Wolloyewa Store"),
        ("om", "Herrega kee", "Profaayilii fi qindaa'inoota — Wolloyewa"),
        ("unsupported", "የእርስዎ መለያ", "ፕሮፋይል እና ቅንብሮች — ወሎዮ ሱቅ"),
    ],
)
async def test_profile_page_uses_supported_localization(language, expected, expected_title):
    from html import unescape

    from starlette.requests import Request

    from bot.web_app.router import profile_page

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/profile",
        "raw_path": b"/profile",
        "query_string": f"lang={language}".encode(),
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }
    request = Request(scope)
    response = await profile_page(request)

    assert response.context["page_language"] in {"am", "en", "om"}
    assert response.context["profile_text"]["የእርስዎ መለያ"] == expected
    html = unescape(response.body.decode("utf-8"))
    assert f"<title>{expected_title}</title>" in html
    expected_orders = {
        "en": "Total orders",
        "om": "Ajajawwan waliigalaa",
        "unsupported": "ጠቅላላ ትዕዛዞች",
    }
    assert response.context["profile_text"]["ጠቅላላ ትዕዛዞች"] == expected_orders[language]
    assert 'id="accountOverview"' in html
    assert 'id="customerDashboardContent"' in html
    assert 'class="profile-section-nav"' in html
    assert 'id="customerWishlistSection"' in html
    assert 'id="customerCouponsSection"' in html
    assert 'id="accountSettings"' in html
    assert 'aria-label="የመገለጫ ፎቶ"' in html


def test_profile_hides_notification_channels_without_delivery_integration():
    from pathlib import Path

    profile = (
        Path(__file__).parents[2] / "bot" / "web_app" / "templates" / "profile.html"
    ).read_text(encoding="utf-8")

    assert "ማድረሻ መቆጣጠሪያዎች አልታዩም" in profile
    assert 'name="email_notifications"' not in profile
    assert 'name="sms_notifications"' not in profile
    assert 'name="push_notifications"' not in profile


def test_vendor_product_payload_validates_price_and_normalizes_input():
    from bot.web_app.router import WebVendorProductPayload

    product = WebVendorProductPayload.model_validate(
        {
            "name": "  Wooden table ",
            "sku": " TABLE-1 ",
            "price": "250.00",
            "compare_price": "300.00",
            "stock_quantity": 3,
        }
    )
    assert product.name == "Wooden table"
    assert product.sku == "TABLE-1"
    assert product.compare_price > product.price

    with pytest.raises(ValidationError):
        WebVendorProductPayload.model_validate(
            {
                "name": "Table",
                "sku": "TABLE-1",
                "price": "300.00",
                "compare_price": "250.00",
            }
        )


def test_web_profile_update_validates_supported_language_and_notification_preferences():
    from bot.web_app.router import WebProfileUpdate

    data = WebProfileUpdate(
        language="en",
        notification_settings={"email_notifications": False, "marketing_emails": True},
    )

    assert data.language == "en"
    assert data.notification_settings == {
        "email_notifications": False,
        "marketing_emails": True,
    }

    with pytest.raises(ValidationError):
        WebProfileUpdate(language="fr")
    with pytest.raises(ValidationError):
        WebProfileUpdate(notification_settings={"admin_alerts": False})


def test_web_address_schemas_validate_types_and_normalize_ethiopian_phone():
    from bot.web_app.router import WebAddressCreate

    address = WebAddressCreate(
        address_line1="  Bole Road  ",
        city=" Addis Ababa ",
        recipient_name=" Aster Tesfaye ",
        recipient_phone="0911234567",
        address_type="work",
    )

    assert address.address_line1 == "Bole Road"
    assert address.city == "Addis Ababa"
    assert address.recipient_name == "Aster Tesfaye"
    assert address.recipient_phone == "0911234567"
    with pytest.raises(ValidationError):
        WebAddressCreate(
            address_line1="Bole",
            city="Addis Ababa",
            recipient_name="Aster",
            recipient_phone="123",
            address_type="warehouse",
        )


@pytest.mark.asyncio
async def test_list_web_addresses_scopes_query_to_authenticated_user():
    from bot.web_app.router import list_web_user_addresses

    address = SimpleNamespace(
        id=17,
        address_line1="Bole Road",
        address_line2="",
        city="Addis Ababa",
        subcity="",
        woreda="",
        house_number="",
        landmark="",
        recipient_name="Aster",
        recipient_phone="0911234567",
        address_type="home",
        is_default=True,
        created_at=None,
    )
    db = Mock()
    db.execute = AsyncMock(
        return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[address]))))
    )

    result = await list_web_user_addresses(current_user={"id": 42}, db=db)

    query = str(db.execute.await_args.args[0])
    assert "user_addresses.user_id" in query
    assert result["items"] == [
        {
            "id": 17,
            "address_line1": "Bole Road",
            "address_line2": "",
            "city": "Addis Ababa",
            "subcity": "",
            "woreda": "",
            "house_number": "",
            "landmark": "",
            "recipient_name": "Aster",
            "recipient_phone": "0911234567",
            "address_type": "home",
            "is_default": True,
            "created_at": None,
        }
    ]


@pytest.mark.asyncio
async def test_create_web_address_makes_first_address_default_and_normalizes_phone():
    from bot.web_app.router import WebAddressCreate, create_web_user_address

    address_result = Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))
    preferences_result = Mock(scalar_one_or_none=Mock(return_value=None))
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=42)),
            address_result,
            preferences_result,
        ]
    )
    db.add = Mock(side_effect=lambda address: setattr(address, "id", 17))
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    result = await create_web_user_address(
        WebAddressCreate(
            address_line1="Bole Road",
            city="Addis Ababa",
            recipient_name="Aster Tesfaye",
            recipient_phone="0911234567",
        ),
        current_user={"id": 42},
        db=db,
    )

    saved_address = db.add.call_args.args[0]
    assert result["id"] == 17
    assert result["recipient_phone"] == "0911234567"
    assert saved_address.is_default is True
    assert saved_address.user_id == 42
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_web_address_changes_default_only_for_its_owner():
    from bot.web_app.router import WebAddressUpdate, update_web_user_address

    address = SimpleNamespace(
        id=17,
        address_line1="Bole",
        address_line2="",
        city="Addis Ababa",
        subcity="",
        woreda="",
        house_number="",
        landmark="",
        recipient_name="Aster",
        recipient_phone="+251911234567",
        address_type="home",
        is_default=False,
        created_at=None,
    )
    existing_default = SimpleNamespace(id=12, is_default=True)
    preferences = SimpleNamespace(default_shipping_address_id=12)
    target_result = Mock(scalar_one_or_none=Mock(return_value=address))
    addresses_result = Mock(
        scalars=Mock(return_value=Mock(all=Mock(return_value=[existing_default, address])))
    )
    preferences_result = Mock(scalar_one_or_none=Mock(return_value=preferences))
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=42)),
            target_result,
            addresses_result,
            preferences_result,
        ]
    )
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    result = await update_web_user_address(
        17,
        WebAddressUpdate(is_default=True),
        current_user={"id": 42},
        db=db,
    )

    assert result["is_default"] is True
    assert address.is_default is True
    assert existing_default.is_default is False
    assert preferences.default_shipping_address_id == 17
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_web_address_promotes_replacement_and_rejects_other_users():
    from fastapi import HTTPException

    from bot.web_app.router import delete_web_user_address

    deleted = SimpleNamespace(id=17, is_default=True)
    replacement = SimpleNamespace(id=12, is_default=False)
    addresses_result = Mock(
        scalars=Mock(return_value=Mock(all=Mock(return_value=[deleted, replacement])))
    )
    preferences = SimpleNamespace(default_shipping_address_id=17)
    preferences_result = Mock(scalar_one_or_none=Mock(return_value=preferences))
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=42)),
            addresses_result,
            preferences_result,
        ]
    )
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    response = await delete_web_user_address(
        17,
        current_user={"id": 42},
        db=db,
    )

    assert response.status_code == 204
    assert replacement.is_default is True
    assert preferences.default_shipping_address_id == 12
    db.delete.assert_awaited_once_with(deleted)

    db.execute = AsyncMock(
        side_effect=[
            Mock(scalar_one_or_none=Mock(return_value=99)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
        ]
    )
    with pytest.raises(HTTPException) as exc:
        await delete_web_user_address(17, current_user={"id": 99}, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_user_profile_returns_role_status_and_saved_preferences():
    from bot.web_app.router import get_user_profile

    user = SimpleNamespace(
        id=42,
        first_name="Aster",
        last_name="Tesfaye",
        username="aster",
        telegram_id=42,
        phone_number="0912345678",
        email="aster@example.com",
        language="en",
        role="vendor",
        status="active",
        city="Addis Ababa",
        created_at=None,
        password_hash="hashed",
    )
    vendor = SimpleNamespace(
        business_name="Aster Crafts",
        is_approved=False,
        rejected_at=None,
    )
    preferences = SimpleNamespace(
        email_notifications=False,
        sms_notifications=True,
        push_notifications=True,
        marketing_emails=True,
        promotional_sms=False,
    )
    service = Mock()
    service.get_user = AsyncMock(return_value=user)
    with patch("bot.web_app.router.UserService", return_value=service):
        db = Mock()
        db.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=None)),
                Mock(scalar_one_or_none=Mock(return_value=preferences)),
                Mock(scalar_one_or_none=Mock(return_value=vendor)),
            ]
        )

        profile = await get_user_profile(current_user={"id": 42}, db=db)

    assert profile["role"] == "vendor"
    assert profile["status"] == "active"
    assert profile["has_password"] is True
    assert profile["vendor"] == {
        "business_name": "Aster Crafts",
        "is_approved": False,
        "is_rejected": False,
    }
    assert profile["notification_settings"]["email_notifications"] is False
    assert profile["notification_settings"]["marketing_emails"] is True


@pytest.mark.asyncio
async def test_logout_increments_user_token_version():
    from bot.web_app.router import web_app_logout

    db = Mock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    response = await web_app_logout(current_user={"id": 42}, db=db)

    assert response == {"success": True}
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_current_user_rejects_revoked_token_version(monkeypatch):
    from fastapi.security import HTTPAuthorizationCredentials

    import core.dependencies as dependencies
    from core.exceptions import AuthenticationError

    user_repo = Mock()
    user_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(id=42, token_version=3, status="active")
    )
    monkeypatch.setattr(
        "apps.users.repository.UserRepository",
        lambda _db: user_repo,
    )
    monkeypatch.setattr(
        dependencies,
        "verify_token",
        lambda _token: {"sub": "42", "token_version": 2},
    )

    with pytest.raises(AuthenticationError, match="revoked"):
        await dependencies.get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="stale-token"),
            db=Mock(),
        )

    user_repo.get_by_id.assert_awaited_once_with(42)


@pytest.mark.asyncio
async def test_admin_can_reactivate_discount_and_delete_unused_discount():
    from bot.web_app.router import (
        web_admin_activate_discount,
        web_admin_delete_discount,
    )

    coupon = SimpleNamespace(id=12, is_active=False, used_count=0)
    db = Mock()
    db.get = AsyncMock(return_value=coupon)
    db.scalar = AsyncMock(return_value=None)
    db.flush = AsyncMock()
    db.delete = AsyncMock()

    result = await web_admin_activate_discount(
        12,
        current_user={"id": 1, "role": "admin"},
        db=db,
    )
    assert result == {"success": True, "id": 12, "is_active": True}
    assert coupon.is_active is True

    result = await web_admin_delete_discount(
        12,
        current_user={"id": 1, "role": "admin"},
        db=db,
    )
    assert result == {"success": True, "id": 12}
    db.delete.assert_awaited_once_with(coupon)


@pytest.mark.asyncio
async def test_admin_cannot_permanently_delete_discount_with_usage_history():
    from fastapi import HTTPException

    from bot.web_app.router import web_admin_delete_discount

    coupon = SimpleNamespace(id=12, used_count=1)
    db = Mock()
    db.get = AsyncMock(return_value=coupon)
    db.scalar = AsyncMock(return_value=8)
    db.delete = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await web_admin_delete_discount(
            12,
            current_user={"id": 1, "role": "admin"},
            db=db,
        )

    assert exc.value.status_code == 409
    db.delete.assert_not_called()


def test_role_dashboard_and_admin_coupon_controls_are_present_and_initially_gated():
    from pathlib import Path

    templates = Path(__file__).parents[2] / "bot" / "web_app" / "templates"
    profile = (templates / "profile.html").read_text(encoding="utf-8")
    admin = (templates / "admin.html").read_text(encoding="utf-8")

    assert 'id="accountOverview" hidden' in profile
    assert 'id="customerDashboardContent" hidden' in profile
    assert 'id="vendorDashboardContent" hidden' in profile
    assert 'id="adminRoleDashboard" hidden' in profile
    assert "/app/api/admin/session" in profile
    assert 'href="#accountSettings"' in profile
    assert 'id="adminDashboard" hidden' in admin
    assert 'id="adminDiscountForm"' in admin
    assert 'id="adminDiscountsPanel"' in admin
    assert 'data-toggle-discount' in admin
    assert 'data-delete-discount' in admin


def test_login_and_registration_open_the_single_profile_page():
    from pathlib import Path

    templates = Path(__file__).parents[2] / "bot" / "web_app" / "templates"
    login = (templates / "login.html").read_text(encoding="utf-8")
    register = (templates / "register.html").read_text(encoding="utf-8")
    navigation = (templates / "base.html").read_text(encoding="utf-8")

    assert "window.location.assign('/app/profile')" in login
    assert "window.location.href = '/app/profile'" in register
    assert 'href="/app/profile?lang={{ page_language|default(\'am\') }}" class="nav-primary-link' in navigation
    assert 'href="/app/profile?lang={{ page_language|default(\'am\') }}" class="bnav-item' in navigation
    assert 'href="/app/cart?lang={{ page_language|default(\'am\') }}" class="nav-cart-btn' in navigation
    assert 'href="/app/cart?lang={{ page_language|default(\'am\') }}" class="bnav-item' not in navigation
    assert 'href="/app/profile?lang={{ page_language|default(\'am\') }}" class="drawer-item' not in navigation
    assert 'class="nav-search-icon"' in navigation
    assert 'class="nav-link-icon"' in navigation
    assert 'class="language-icon"' in navigation
    assert 'class="nav-cart-icon"' in navigation
    assert 'data-tooltip="{{ profile_text.get(\'Menu\', \'Menu\') }}"' in navigation


@pytest.mark.asyncio
async def test_update_web_profile_persists_language_and_notification_settings():
    from bot.web_app.router import WebProfileUpdate, update_web_user_profile

    user = SimpleNamespace(
        id=42,
        first_name="Aster",
        last_name=None,
        username=None,
        telegram_id=42,
        phone_number=None,
        email=None,
        language="am",
        preferred_language=None,
        role="customer",
        status="active",
        city=None,
        created_at=None,
        password_hash=None,
    )
    service = Mock()
    service.get_user = AsyncMock(return_value=user)

    async def update_user(_user_id, update, *, partial):
        assert partial is False
        user.language = update.language
        return user

    service.update_user = AsyncMock(side_effect=update_user)
    with patch("bot.web_app.router.UserService", return_value=service):
        db = Mock()
        db.execute = AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=None)),
                Mock(scalar_one_or_none=Mock(return_value=None)),
                Mock(scalar_one_or_none=Mock(return_value=None)),
                Mock(scalar_one_or_none=Mock(return_value=None)),
            ]
        )
        db.add = Mock()
        db.commit = AsyncMock()

        profile = await update_web_user_profile(
            WebProfileUpdate(
                language="om",
                notification_settings={"email_notifications": False},
            ),
            current_user={"id": 42},
            db=db,
        )

    saved_preferences = db.add.call_args.args[0]
    assert user.language == "om"
    assert user.preferred_language == "om"
    assert saved_preferences.language == "om"
    assert saved_preferences.email_notifications is False
    assert profile["language"] == "om"


@pytest.mark.asyncio
async def test_profile_rejects_contact_changes_without_a_verification_flow():
    from fastapi import HTTPException

    from bot.web_app.router import WebProfileUpdate, update_web_user_profile

    user = SimpleNamespace(phone_number="+251911111111", email="user@example.com")
    service = Mock()
    service.get_user = AsyncMock(return_value=user)
    db = Mock()
    db.rollback = AsyncMock()

    with patch("bot.web_app.router.UserService", return_value=service):
        with pytest.raises(HTTPException) as exc:
            await update_web_user_profile(
                WebProfileUpdate(phone_number="0912222222"),
                current_user={"id": 42},
                db=db,
            )

    assert exc.value.status_code == 409
    assert user.phone_number == "+251911111111"
    db.rollback.assert_awaited_once()


def test_product_upload_normalizes_valid_images_and_rejects_non_images():
    from io import BytesIO

    from fastapi import HTTPException
    from PIL import Image

    from bot.web_app.router import _normalize_uploaded_product_image

    source = BytesIO()
    Image.new("RGB", (32, 24), color=(30, 120, 80)).save(source, format="PNG")

    normalized = _normalize_uploaded_product_image(source.getvalue())
    with Image.open(BytesIO(normalized)) as image:
        assert image.format == "WEBP"
        assert image.size == (32, 24)

    with pytest.raises(HTTPException) as exc:
        _normalize_uploaded_product_image(b"not an image")
    assert exc.value.status_code == 415


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_profile_image_normalization_accepts_safe_formats(image_format):
    from io import BytesIO

    from PIL import Image

    from bot.web_app.router import _normalize_uploaded_profile_image

    source = BytesIO()
    Image.new("RGB", (48, 32), color=(40, 100, 160)).save(source, format=image_format)

    normalized = _normalize_uploaded_profile_image(source.getvalue())

    with Image.open(BytesIO(normalized)) as image:
        assert image.format == "WEBP"
        assert image.size == (48, 32)


def test_profile_image_normalization_rejects_unsupported_and_invalid_image_data():
    from io import BytesIO

    from fastapi import HTTPException
    from PIL import Image

    from bot.web_app.router import _normalize_uploaded_profile_image

    gif = BytesIO()
    Image.new("RGB", (8, 8), color=(20, 40, 60)).save(gif, format="GIF")
    for image_data in (gif.getvalue(), b"not an image"):
        with pytest.raises(HTTPException) as exc:
            _normalize_uploaded_profile_image(image_data)
        assert exc.value.status_code == 415


@pytest.mark.asyncio
@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
async def test_authenticated_profile_image_upload_saves_private_normalized_file(
    image_format,
    tmp_path,
    monkeypatch,
):
    from io import BytesIO
    from types import SimpleNamespace

    from PIL import Image
    from starlette.datastructures import Headers
    from starlette.datastructures import UploadFile as StarletteUploadFile

    import bot.web_app.router as router

    source = BytesIO()
    Image.new("RGB", (40, 28), color=(80, 120, 160)).save(source, format=image_format)
    upload = StarletteUploadFile(
        filename=f"avatar.{image_format.lower()}",
        file=BytesIO(source.getvalue()),
        headers=Headers({"content-type": f"image/{image_format.lower()}"}),
    )
    monkeypatch.setattr(router, "_PROFILE_IMAGE_DIRECTORY", tmp_path / "private")
    user = SimpleNamespace(id=42, profile_picture="legacy-telegram-file-id")
    result = Mock()
    result.scalar_one_or_none.return_value = user
    db = Mock()
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    response = await router.upload_web_user_profile_photo(
        image=upload,
        current_user={"id": 42},
        db=db,
    )

    assert response == {
        "uploaded": True,
        "has_custom_profile_picture": True,
        "cleanup_pending": False,
    }
    assert db.execute.await_args.args[0].compile().params["id_1"] == 42
    assert user.profile_picture.startswith("local-profile-image:")
    image_path = router._profile_image_path(user.profile_picture)
    assert image_path is not None and image_path.is_file()
    with Image.open(image_path) as saved_image:
        assert saved_image.format == "WEBP"
        assert saved_image.size == (40, 28)
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_profile_image_upload_removes_only_previous_managed_image(tmp_path, monkeypatch):
    from io import BytesIO
    from types import SimpleNamespace

    from PIL import Image
    from starlette.datastructures import Headers
    from starlette.datastructures import UploadFile as StarletteUploadFile

    import bot.web_app.router as router

    image_directory = tmp_path / "private"
    image_directory.mkdir()
    old_filename = "c" * 32 + ".webp"
    old_path = image_directory / old_filename
    old_path.write_bytes(b"old private image")
    source = BytesIO()
    Image.new("RGB", (20, 20), color=(60, 90, 120)).save(source, format="PNG")
    upload = StarletteUploadFile(
        filename="avatar.png",
        file=BytesIO(source.getvalue()),
        headers=Headers({"content-type": "image/png"}),
    )
    monkeypatch.setattr(router, "_PROFILE_IMAGE_DIRECTORY", image_directory)
    user = SimpleNamespace(
        id=42,
        profile_picture=f"local-profile-image:{old_filename}",
    )
    result = Mock()
    result.scalar_one_or_none.return_value = user
    db = Mock()
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    await router.upload_web_user_profile_photo(
        image=upload,
        current_user={"id": 42},
        db=db,
    )

    assert not old_path.exists()
    assert router._profile_image_path(user.profile_picture) is not None
    assert router._profile_image_path(user.profile_picture).is_file()


@pytest.mark.asyncio
async def test_profile_image_removal_clears_own_reference_and_deletes_private_file(
    tmp_path,
    monkeypatch,
):
    from types import SimpleNamespace

    import bot.web_app.router as router

    image_directory = tmp_path / "private"
    image_directory.mkdir()
    filename = "a" * 32 + ".webp"
    image_path = image_directory / filename
    image_path.write_bytes(b"private image")
    pointer = f"local-profile-image:{filename}"
    monkeypatch.setattr(router, "_PROFILE_IMAGE_DIRECTORY", image_directory)
    user = SimpleNamespace(id=42, profile_picture=pointer)
    result = Mock()
    result.scalar_one_or_none.return_value = user
    db = Mock()
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    response = await router.remove_web_user_profile_photo(
        current_user={"id": 42},
        db=db,
    )

    assert response == {
        "removed": True,
        "has_custom_profile_picture": False,
        "cleanup_pending": False,
    }
    assert user.profile_picture is None
    assert not image_path.exists()
    assert db.execute.await_args.args[0].compile().params["id_1"] == 42
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_profile_photo_route_serves_only_private_managed_image_without_telegram(
    tmp_path,
    monkeypatch,
):
    from types import SimpleNamespace

    import bot.web_app.router as router
    from core.config import settings

    image_directory = tmp_path / "private"
    image_directory.mkdir()
    filename = "b" * 32 + ".webp"
    image_bytes = b"normalized profile image"
    (image_directory / filename).write_bytes(image_bytes)
    monkeypatch.setattr(router, "_PROFILE_IMAGE_DIRECTORY", image_directory)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "")
    service = Mock()
    service.get_user = AsyncMock(
        return_value=SimpleNamespace(profile_picture=f"local-profile-image:{filename}")
    )
    with patch("bot.web_app.router.UserService", return_value=service):
        response = await router.get_user_profile_photo(
            current_user={"id": 42},
            db=Mock(),
        )

    assert response.body == image_bytes
    assert response.media_type == "image/webp"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_profile_image_upload_rejects_oversized_file_before_image_decode(tmp_path, monkeypatch):
    from io import BytesIO

    from fastapi import HTTPException
    from starlette.datastructures import Headers
    from starlette.datastructures import UploadFile as StarletteUploadFile

    import bot.web_app.router as router
    from core.constants import MAX_IMAGE_SIZE_BYTES

    upload = StarletteUploadFile(
        filename="too-large.png",
        file=BytesIO(b"x" * (MAX_IMAGE_SIZE_BYTES + 1)),
        headers=Headers({"content-type": "image/png"}),
    )
    monkeypatch.setattr(router, "_PROFILE_IMAGE_DIRECTORY", tmp_path / "private")
    db = Mock()

    with pytest.raises(HTTPException) as exc:
        await router.upload_web_user_profile_photo(
            image=upload,
            current_user={"id": 42},
            db=db,
        )

    assert exc.value.status_code == 413
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_profile_image_upload_endpoint_requires_authentication():
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from httpx import ASGITransport, AsyncClient

    from bot.web_app.router import web_app_router
    from core.dependencies import get_db_session
    from core.exceptions import AuthenticationError

    app = FastAPI()
    app.include_router(web_app_router)
    app.add_exception_handler(
        AuthenticationError,
        lambda _request, exc: JSONResponse(status_code=401, content={"detail": str(exc)}),
    )

    async def override_database():
        db = Mock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        yield db

    app.dependency_overrides[get_db_session] = override_database
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/app/api/user/profile/photo",
            files={"image": ("avatar.png", b"not an image", "image/png")},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_vendor_product_upload_creates_pending_product_with_saved_image(
    tmp_path,
    monkeypatch,
):
    from io import BytesIO
    from types import SimpleNamespace

    from PIL import Image
    from starlette.datastructures import Headers
    from starlette.datastructures import UploadFile as StarletteUploadFile

    import bot.web_app.router as router
    from apps.products.schemas import ProductResponse
    from core.constants import ProductStatus

    source = BytesIO()
    Image.new("RGB", (24, 24), color=(80, 90, 100)).save(source, format="PNG")
    upload = StarletteUploadFile(
        filename="product.png",
        file=BytesIO(source.getvalue()),
        headers=Headers({"content-type": "image/png"}),
    )
    monkeypatch.setattr(router, "__file__", str(tmp_path / "router.py"))
    product = SimpleNamespace(
        id=14,
        vendor_id=9,
        category_id=None,
        name="Pending table",
        price=25,
        status=ProductStatus.PENDING,
    )
    service = SimpleNamespace(create_product=AsyncMock(return_value=product))
    db = AsyncMock()
    monkeypatch.setattr(router, "ProductService", lambda _db: service)
    monkeypatch.setattr(ProductResponse, "model_validate", classmethod(lambda cls, value: value))

    response = await router.web_vendor_create_product(
        payload='{"name":"Pending table","sku":"TABLE-14","price":25,"stock_quantity":2}',
        images=[upload],
        current_user={"id": 6, "vendor_id": 9},
        db=db,
    )

    service.create_product.assert_awaited_once()
    db.commit.assert_awaited_once()
    vendor_id, product_data = service.create_product.await_args.args
    assert vendor_id == 9
    assert product_data.status == ProductStatus.PENDING
    assert product_data.images[0].startswith("/app/static/uploads/")
    assert response.status == ProductStatus.PENDING
    assert response.id == 14
    saved_file = tmp_path / "static" / "uploads" / product_data.images[0].rsplit("/", 1)[-1]
    assert saved_file.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("function_name", "approved", "reason"),
    [
        ("web_admin_approve_product", True, None),
        ("web_admin_reject_product", False, "Missing product details"),
    ],
)
async def test_admin_product_review_routes_delegate_to_product_service(
    function_name,
    approved,
    reason,
    monkeypatch,
):
    from types import SimpleNamespace

    import bot.web_app.router as router
    from core.constants import ProductStatus

    product = SimpleNamespace(
        id=31,
        vendor_id=9,
        name="Review item",
        name_am=None,
        sku="REVIEW-31",
        price=25,
        compare_price=None,
        stock_quantity=4,
        category_id=None,
        status=ProductStatus.ACTIVE if approved else ProductStatus.REJECTED,
        description=None,
        images=["/app/static/uploads/item.webp"],
    )
    service = SimpleNamespace(review_product=AsyncMock(return_value=product))
    monkeypatch.setattr(router, "ProductService", lambda _db: service)

    if approved:
        response = await router.web_admin_approve_product(
            31,
            current_user={"id": 1, "role": "admin"},
            db=Mock(),
        )
    else:
        response = await router.web_admin_reject_product(
            31,
            router.WebProductRejection(reason=reason),
            current_user={"id": 1, "role": "admin"},
            db=Mock(),
        )

    service.review_product.assert_awaited_once()
    assert service.review_product.await_args.args == (31,)
    assert service.review_product.await_args.kwargs["approved"] is approved
    if reason:
        assert service.review_product.await_args.kwargs["reason"] == reason
    assert response["status"] == product.status.value
    assert response["images"] == product.images


@pytest.mark.asyncio
async def test_web_categories_returns_nested_tree_with_active_product_counts():
    from types import SimpleNamespace

    from bot.web_app.router import get_categories

    root = SimpleNamespace(
        id=1,
        name="Home",
        name_am="ቤት",
        slug="home",
        parent_id=None,
        description=None,
        description_am=None,
        icon_url=None,
        image_url=None,
        is_featured=True,
        display_order=1,
    )
    child = SimpleNamespace(
        id=2,
        name="Kitchen",
        name_am="ወጥ ቤት",
        slug="kitchen",
        parent_id=1,
        description=None,
        description_am=None,
        icon_url=None,
        image_url="/images/kitchen.png",
        is_featured=False,
        display_order=2,
    )
    query_result = Mock()
    query_result.all.return_value = [(root, 2), (child, 3)]
    db = Mock()
    db.execute = AsyncMock(return_value=query_result)

    categories = await get_categories(db)

    assert len(categories) == 1
    assert categories[0]["id"] == 1
    assert categories[0]["product_count"] == 5
    assert categories[0]["direct_product_count"] == 2
    assert categories[0]["children"][0]["id"] == 2
    assert categories[0]["children"][0]["product_count"] == 3


@pytest.mark.asyncio
async def test_web_products_filter_category_includes_active_descendants():
    from decimal import Decimal
    from types import SimpleNamespace

    from bot.web_app.router import get_products

    categories_result = Mock()
    categories_result.all.return_value = [
        SimpleNamespace(id=1, parent_id=None),
        SimpleNamespace(id=2, parent_id=1),
        SimpleNamespace(id=3, parent_id=2),
    ]
    count_result = Mock()
    count_result.scalar.return_value = 1
    product_result = Mock()
    product_result.scalars.return_value.all.return_value = [
        SimpleNamespace(
            id=17,
            name="Kettle",
            name_am="የውሃ ማፍያ",
            slug="kettle",
            description="",
            price=Decimal("125.00"),
            compare_price=None,
            stock_quantity=4,
            images=[],
            status="active",
            is_featured=False,
            category_id=3,
            category_type="",
        )
    ]
    db = Mock()
    db.execute = AsyncMock(side_effect=[categories_result, count_result, product_result])

    response = await get_products(page=1, page_size=20, category_id=1, db=db)
    payload = json.loads(response.body)
    count_query = db.execute.await_args_list[1].args[0]
    bound_values = count_query.compile().params.values()

    assert payload["total"] == 1
    assert payload["items"][0]["category_id"] == 3
    assert [1, 2, 3] in bound_values
    assert "active" in bound_values


def test_bearer_user_parser_handles_valid_invalid_and_missing_tokens():
    from bot.web_app.router import _user_from_bearer

    request = Mock()
    request.headers = {}
    assert _user_from_bearer(request, Mock()) is None

    request.headers = {"Authorization": "Bearer token"}
    with patch("core.security.verify_token", return_value={"sub": "17"}):
        assert _user_from_bearer(request, Mock()) == 17

    with patch("core.security.verify_token", return_value=None):
        assert _user_from_bearer(request, Mock()) is None

    with patch("core.security.verify_token", return_value={"sub": "not-number"}):
        assert _user_from_bearer(request, Mock()) is None


def test_web_auth_response_contains_token_and_user_summary():
    from bot.web_app.router import _web_auth_response

    user = Mock(
        id=3,
        role="customer",
        token_version=0,
        first_name="Test",
        last_name="User",
        phone_number="0912345678",
        email=None,
    )
    with patch("core.security.create_access_token", return_value="jwt-token") as create_token:
        response = _web_auth_response(user)

    create_token.assert_called_once_with(
        {"sub": "3", "role": "customer", "token_version": 0}
    )
    assert response["access_token"] == "jwt-token"
    assert response["user"]["full_name"] == "Test User"
    assert response["user"]["email"] == ""


@pytest.mark.asyncio
async def test_tg_auth_does_not_authenticate_as_first_database_user_in_development(monkeypatch):
    from fastapi import HTTPException

    from bot.web_app.router import tg_auth
    from core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    request = Mock()
    request.json = AsyncMock(return_value={})
    db = Mock()

    with pytest.raises(HTTPException) as exc:
        await tg_auth(request, db)

    assert exc.value.status_code == 401
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_checkout_requires_authentication_in_development(monkeypatch):
    from fastapi import HTTPException

    from bot.web_app.router import CartItemIn, CheckoutRequest, api_checkout
    from core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    request = Mock(headers={})
    body = CheckoutRequest(
        items=[CartItemIn(id=1, name="Phone", price=10, qty=1)],
        full_name="Test User",
        phone="0912345678",
        city="Addis Ababa",
        address="Main street",
        payment_method="cod",
    )
    db = Mock()
    db.get = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await api_checkout(request, body, db)

    assert exc.value.status_code == 401
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_my_orders_requires_telegram_authentication_in_development(monkeypatch):
    from fastapi import HTTPException

    from bot.web_app.router import MyOrdersRequest, api_my_orders
    from core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    db = Mock()

    with pytest.raises(HTTPException) as exc:
        await api_my_orders(MyOrdersRequest(), db)

    assert exc.value.status_code == 401
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_my_orders_accepts_authenticated_web_account(monkeypatch):
    from types import SimpleNamespace

    import bot.web_app.router as router

    monkeypatch.setattr(router.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(router, "_user_from_bearer", lambda _authorization, _db: 42)

    user_result = Mock()
    user_result.scalar_one_or_none.return_value = SimpleNamespace(id=42)
    orders_result = Mock()
    orders_result.scalars.return_value.all.return_value = []
    db = Mock()
    db.execute = AsyncMock(side_effect=[user_result, orders_result])

    response = await router.api_my_orders(
        router.MyOrdersRequest(),
        db,
        authorization="Bearer valid-token",
    )

    assert response == {"orders": [], "total": 0}
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_configured_telegram_admin_is_authorized_even_without_admin_database_role(monkeypatch):
    from core.config import settings
    from core.dependencies import get_current_admin

    monkeypatch.setattr(settings, "ADMIN_IDS", "42,99")
    current_user = {"id": 7, "telegram_id": 42, "role": "customer"}

    assert await get_current_admin(current_user) == current_user


@pytest.mark.asyncio
async def test_non_admin_user_is_rejected_from_admin_dependency(monkeypatch):
    from core.config import settings
    from core.dependencies import get_current_admin
    from core.exceptions import PermissionError

    monkeypatch.setattr(settings, "ADMIN_IDS", "42,99")

    with pytest.raises(PermissionError) as exc:
        await get_current_admin({"id": 8, "telegram_id": 100, "role": "customer"})

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_web_login_normalizes_international_phone_and_throttles(monkeypatch):
    from types import SimpleNamespace

    import bot.web_app.router as router
    import core.dependencies

    rate_limit = AsyncMock()
    monkeypatch.setattr(core.dependencies, "check_rate_limit", rate_limit)
    user = SimpleNamespace(
        id=17,
        first_name="Test",
        last_name="Customer",
        phone_number="0912345678",
        email=None,
        password_hash="stored-hash",
        status="active",
        role="customer",
        token_version=0,
    )
    result = Mock()
    result.scalar_one_or_none.return_value = user
    db = Mock()
    db.execute = AsyncMock(return_value=result)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    with patch("core.security.verify_password", return_value=True):
        response = await router.api_web_login(
            router.WebLoginRequest(phone="+251 91 234 5678", password="test-password"),
            request,
            db,
        )

    assert response["token_type"] == "bearer"
    assert response["user"]["phone"] == "0912345678"
    rate_limit.assert_awaited_once_with(
        request,
        key_prefix="web_login",
        limit=10,
        window=300,
    )
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_web_login_rejects_invalid_phone_before_database_lookup(monkeypatch):
    from fastapi import HTTPException

    import bot.web_app.router as router
    import core.dependencies

    monkeypatch.setattr(core.dependencies, "check_rate_limit", AsyncMock())
    db = Mock()
    db.execute = AsyncMock()
    request = Mock()

    with pytest.raises(HTTPException) as exc:
        await router.api_web_login(
            router.WebLoginRequest(phone="12345", password="test-password"),
            request,
            db,
        )

    assert exc.value.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_web_login_uses_same_unauthorized_response_for_inactive_accounts(monkeypatch):
    from types import SimpleNamespace

    from fastapi import HTTPException

    import bot.web_app.router as router
    import core.dependencies

    monkeypatch.setattr(core.dependencies, "check_rate_limit", AsyncMock())
    user = SimpleNamespace(password_hash="stored-hash", status="suspended")
    result = Mock()
    result.scalar_one_or_none.return_value = user
    db = Mock()
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc:
        await router.api_web_login(
            router.WebLoginRequest(phone="0912345678", password="test-password"),
            Mock(),
            db,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "ስልክ ቁጥሩ ወይም የይለፍ ቃሉ ስህተት ነው"


@pytest.mark.asyncio
async def test_web_login_stops_rate_limited_attempt_before_database_lookup(monkeypatch):
    import bot.web_app.router as router
    import core.dependencies
    from core.exceptions import RateLimitError

    rate_limit = AsyncMock(side_effect=RateLimitError(retry_after=300))
    monkeypatch.setattr(core.dependencies, "check_rate_limit", rate_limit)
    db = Mock()
    db.execute = AsyncMock()

    with pytest.raises(RateLimitError):
        await router.api_web_login(
            router.WebLoginRequest(phone="0912345678", password="test-password"),
            Mock(),
            db,
        )

    db.execute.assert_not_awaited()


def test_wishlist_model_maps_existing_unique_constraint():
    from apps.users.models import Wishlist

    unique_constraints = [
        constraint
        for constraint in Wishlist.__table__.constraints
        if constraint.name == "unique_user_product_wishlist"
    ]

    assert len(unique_constraints) == 1
    assert [column.name for column in unique_constraints[0].columns] == [
        "user_id",
        "product_id",
    ]


@pytest.mark.asyncio
async def test_list_web_wishlist_scopes_by_owner_and_returns_current_product_data():
    from decimal import Decimal
    from types import SimpleNamespace

    from bot.web_app.router import list_web_user_wishlist
    from core.constants import ProductStatus

    product = SimpleNamespace(
        id=17,
        name="Current name",
        name_am="የአሁኑ ስም",
        price=Decimal("125.50"),
        images=["/current.webp"],
        is_deleted=False,
        deleted_at=None,
        status=ProductStatus.ACTIVE,
        stock_quantity=3,
    )
    saved = SimpleNamespace(product_id=17, created_at=None)
    result = Mock()
    result.all.return_value = [(saved, product)]
    db = Mock()
    db.execute = AsyncMock(return_value=result)

    response = await list_web_user_wishlist(current_user={"id": 42}, db=db)

    statement = db.execute.await_args.args[0]
    assert "wishlists.user_id" in str(statement.whereclause)
    assert 42 in statement.compile().params.values()
    assert response["items"] == [
        {
            "id": 17,
            "name": "Current name",
            "name_am": "የአሁኑ ስም",
            "price": "125.50",
            "image": "/current.webp",
            "available": True,
            "availability_reason": None,
            "status": "active",
            "created_at": None,
        }
    ]


@pytest.mark.asyncio
async def test_add_web_wishlist_is_idempotent_and_checks_product_availability():
    from types import SimpleNamespace

    from fastapi import HTTPException

    from bot.web_app.router import add_web_user_wishlist_item
    from core.constants import ProductStatus

    def result_with_scalar(value):
        result = Mock()
        result.scalar_one_or_none.return_value = value
        return result

    product = SimpleNamespace(
        id=17,
        is_deleted=False,
        deleted_at=None,
        status=ProductStatus.ACTIVE,
        stock_quantity=3,
    )
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            result_with_scalar(42),
            result_with_scalar(None),
            result_with_scalar(product),
        ]
    )
    db.commit = AsyncMock()

    response = await add_web_user_wishlist_item(
        17,
        current_user={"id": 42},
        db=db,
    )

    assert response == {"added": True}
    entry = db.add.call_args.args[0]
    assert (entry.user_id, entry.product_id) == (42, 17)
    assert 42 in db.execute.await_args_list[1].args[0].compile().params.values()
    db.commit.assert_awaited_once()

    out_of_stock = SimpleNamespace(
        id=18,
        is_deleted=False,
        deleted_at=None,
        status=ProductStatus.OUT_OF_STOCK,
        stock_quantity=0,
    )
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            result_with_scalar(42),
            result_with_scalar(None),
            result_with_scalar(out_of_stock),
        ]
    )
    db.rollback = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await add_web_user_wishlist_item(18, current_user={"id": 42}, db=db)

    assert exc.value.status_code == 409
    db.add.assert_not_called()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_existing_wishlist_product_does_not_create_a_duplicate():
    from types import SimpleNamespace

    from bot.web_app.router import add_web_user_wishlist_item

    lock_result = Mock()
    lock_result.scalar_one_or_none.return_value = 42
    existing_result = Mock()
    existing_result.scalar_one_or_none.return_value = SimpleNamespace(
        user_id=42,
        product_id=17,
    )
    db = Mock()
    db.execute = AsyncMock(side_effect=[lock_result, existing_result])

    response = await add_web_user_wishlist_item(
        17,
        current_user={"id": 42},
        db=db,
    )

    assert response == {"added": False}
    assert db.execute.await_count == 2
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_remove_web_wishlist_product_scopes_delete_to_authenticated_user():
    from fastapi import Response

    from bot.web_app.router import remove_web_user_wishlist_item

    result = Mock()
    result.scalar_one_or_none.return_value = None
    db = Mock()
    owner_result = Mock()
    owner_result.scalar_one_or_none.return_value = 42
    db.execute = AsyncMock(side_effect=[owner_result, result])
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    response = await remove_web_user_wishlist_item(
        17,
        current_user={"id": 42},
        db=db,
    )

    statement = db.execute.await_args.args[0]
    query_params = statement.compile().params.values()
    assert 42 in query_params
    assert 17 in query_params
    assert isinstance(response, Response)
    assert response.status_code == 204
    db.delete.assert_not_called()
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_web_wishlist_deduplicates_ids_and_skips_missing_or_unavailable_products():
    from decimal import Decimal
    from types import SimpleNamespace

    from bot.web_app.router import WebWishlistSync, sync_web_user_wishlist
    from core.constants import ProductStatus

    def scalar_result(value):
        result = Mock()
        result.scalar_one_or_none.return_value = value
        return result

    def scalars_result(values):
        result = Mock()
        result.scalars.return_value.all.return_value = values
        return result

    available = SimpleNamespace(
        id=6,
        name="Current name",
        name_am=None,
        price=Decimal("25.00"),
        images=[],
        is_deleted=False,
        deleted_at=None,
        status=ProductStatus.ACTIVE,
        stock_quantity=2,
    )
    out_of_stock = SimpleNamespace(
        id=9,
        is_deleted=False,
        deleted_at=None,
        status=ProductStatus.OUT_OF_STOCK,
        stock_quantity=0,
    )
    saved = SimpleNamespace(product_id=6, created_at=None)
    final = Mock()
    final.all.return_value = [(saved, available)]
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            scalar_result(42),
            scalars_result([5]),
            scalars_result([available, out_of_stock]),
            final,
        ]
    )
    db.commit = AsyncMock()

    response = await sync_web_user_wishlist(
        WebWishlistSync(product_ids=[5, 5, 6, 9, 10]),
        current_user={"id": 42},
        db=db,
    )

    assert response["skipped"] == [
        {"product_id": 9, "reason": "out_of_stock"},
        {"product_id": 10, "reason": "not_found"},
    ]
    assert [item["id"] for item in response["items"]] == [6]
    assert db.add.call_count == 1
    imported = db.add.call_args.args[0]
    assert (imported.user_id, imported.product_id) == (42, 6)
    assert db.commit.await_count == 1


def test_wishlist_sync_schema_rejects_non_positive_and_non_integer_ids():
    from bot.web_app.router import WebWishlistSync

    assert WebWishlistSync(product_ids=[7, 7]).product_ids == [7]
    with pytest.raises(ValidationError):
        WebWishlistSync(product_ids=[0])
    with pytest.raises(ValidationError):
        WebWishlistSync(product_ids=[True])
