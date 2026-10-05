"""Focused tests for Telegram Mini App router primitives and page routes."""

import hashlib
import hmac
import json
import time
import urllib.parse
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("function_name", "template_name"),
    [
        ("index_page", "index.html"),
        ("login_page", "login.html"),
        ("register_page", "register.html"),
        ("categories_page", "categories.html"),
        ("dashboard_page", "dashboard.html"),
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
    assert response.context["request"] is request


@pytest.mark.asyncio
async def test_product_page_includes_product_id():
    from bot.web_app.router import product_page

    request = Mock()
    response = await product_page(request, 17)

    assert response.template.name == "product.html"
    assert response.context["product_id"] == 17


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
        first_name="Test",
        last_name="User",
        phone_number="0912345678",
        email=None,
    )
    with patch("core.security.create_access_token", return_value="jwt-token") as create_token:
        response = _web_auth_response(user)

    create_token.assert_called_once_with({"sub": "3", "role": "customer"})
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
