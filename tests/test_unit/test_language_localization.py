import ast
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bot.localization import (
    _MESSAGES,
    SUPPORTED_LANGUAGES,
    get_language,
    get_web_login_translations,
    translate,
)


def test_translation_catalogs_have_matching_keys():
    keys = set(_MESSAGES["am"])
    assert set(_MESSAGES["en"]) == keys
    assert set(_MESSAGES["om"]) == keys


def test_handlers_only_reference_existing_translation_keys():
    handlers = Path(__file__).parents[2] / "bot" / "handlers"
    missing = []
    for source_path in handlers.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id not in {"tr", "translate"}:
                continue
            if len(node.args) < 2 or not isinstance(node.args[1], ast.Constant):
                continue
            key = node.args[1].value
            if isinstance(key, str) and any(key not in catalog for catalog in _MESSAGES.values()):
                missing.append(f"{source_path}:{node.lineno}: {key}")
    assert not missing, "\n".join(missing)


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "Your shopping cart"),
        ("om", "Gaatarii bittaa"),
    ],
)
def test_current_language_is_used_for_customer_screens(language, expected):
    context = SimpleNamespace(user_data={"user": {"language": language}})

    assert get_language(context) == language
    assert expected in translate(language, "cart_title")


def test_translation_formats_dynamic_values_in_selected_language():
    assert translate("en", "location_city_saved", city="London").startswith(
        "✅ *Your city, London,"
    )


def test_web_login_copy_uses_shared_amharic_and_english_catalogs():
    amharic = get_web_login_translations("am")
    english = get_web_login_translations("en")

    assert amharic["heading"] == "ወደ መለያዎ ይግቡ"
    assert english["heading"] == "Sign in to your account"
    assert "ስልክ ቁጥሩ" in amharic["credentials_error"]
    assert english["credentials_error"] == "The phone number or password is incorrect."


@pytest.mark.asyncio
async def test_empty_cart_command_uses_selected_language():
    from bot.handlers.cart import cart_command

    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message)
    context = SimpleNamespace(user_data={"language": "en"})

    await cart_command(update, context)

    sent_text = message.reply_text.await_args.args[0]
    assert "Your cart is empty" in sent_text
    assert "ምርቶችን ለመግዛት" not in sent_text


@pytest.mark.asyncio
async def test_checkout_payment_prompt_uses_selected_language(monkeypatch):
    from bot.handlers.checkout import SELECT_PAYMENT, show_payment_methods

    async def availability(_db):
        from apps.store_settings.checkout import CheckoutAvailability

        return CheckoutAvailability(
            store_open=True,
            maintenance_message=None,
            enabled_payment_methods=frozenset({"cod"}),
            configured_payment_gateways={"cod": True},
        )

    async def session():
        yield SimpleNamespace()

    monkeypatch.setattr("bot.handlers.checkout.get_checkout_availability", availability)
    monkeypatch.setattr("bot.handlers.checkout.get_db_session", session)
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(callback_query=None, message=message)
    context = SimpleNamespace(user_data={"language": "en"})

    state = await show_payment_methods(update, context)

    assert state == SELECT_PAYMENT
    sent_text = message.reply_text.await_args.args[0]
    assert "Choose a payment method" in sent_text
    keyboard = message.reply_text.await_args.kwargs["reply_markup"].inline_keyboard
    assert "Cash on delivery" in keyboard[0][0].text
    assert len(keyboard) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback_data", "expected_method"),
    [
        ("pay_chapa", "chapa"),
        ("pay_telebirr", "telebirr"),
        ("pay_cbe_birr", "cbe_birr"),
        ("pay_cod", "cash_on_delivery"),
    ],
)
async def test_checkout_payment_callback_preserves_payment_method(
    callback_data, expected_method, monkeypatch
):
    from bot.handlers import checkout

    monkeypatch.setattr(
        checkout,
        "show_order_confirmation",
        AsyncMock(return_value=checkout.CONFIRM_ORDER),
    )
    query = SimpleNamespace(data=callback_data, answer=AsyncMock())
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(
        user_data={
            "checkout_recipient_name": "Test Recipient",
            "checkout_recipient_phone": "0912345678",
        }
    )

    state = await checkout.payment_callback(update, context)

    assert state == checkout.CONFIRM_ORDER
    assert context.user_data["checkout_payment_method"] == expected_method


@pytest.mark.asyncio
async def test_telegram_coupon_step_validates_and_applies_server_result(monkeypatch):
    from decimal import Decimal

    from bot.handlers import checkout

    message = SimpleNamespace(text=" save10 ", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=42),
    )
    context = SimpleNamespace(user_data={})
    monkeypatch.setattr(
        checkout,
        "get_user_cart",
        AsyncMock(return_value=[{"product_id": 1, "quantity": 2}]),
    )
    validate = AsyncMock(
        return_value={"is_valid": True, "discount_amount": Decimal("12.50")}
    )
    monkeypatch.setattr(checkout, "_validate_checkout_coupon", validate)
    monkeypatch.setattr(
        checkout,
        "show_payment_methods",
        AsyncMock(return_value=checkout.SELECT_PAYMENT),
    )

    state = await checkout.coupon_message_handler(update, context)

    assert state == checkout.SELECT_PAYMENT
    assert context.user_data["checkout_coupon_code"] == "SAVE10"
    assert context.user_data["checkout_coupon_discount"] == Decimal("12.50")
    assert context.user_data["checkout_coupon_checked"] is True
    validate.assert_awaited_once()


@pytest.mark.asyncio
async def test_feedback_prompt_uses_selected_language():
    from bot.handlers.feedback import feedback_command

    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message)
    context = SimpleNamespace(user_data={"language": "en"})

    await feedback_command(update, context)

    assert "Thank you for your feedback" in message.reply_text.await_args_list[0].args[0]
    assert "Rate our service" in message.reply_text.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_location_prompt_uses_selected_language():
    from bot.handlers.location import location_command

    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(user_data={"language": "en"})

    await location_command(update, context)

    sent_text = message.reply_text.await_args.args[0]
    assert "Share your location" in sent_text
    assert "Enter a city" in message.reply_text.await_args.kwargs["reply_markup"].inline_keyboard[0][1].text


@pytest.mark.asyncio
async def test_profile_language_change_commits_and_updates_live_context(monkeypatch):
    from bot.handlers import profile

    user = SimpleNamespace(id=23)
    service = AsyncMock()
    service.get_user_by_telegram.return_value = user

    @asynccontextmanager
    async def transaction_session():
        yield object()

    monkeypatch.setattr(profile, "transaction_session", transaction_session)
    monkeypatch.setattr(profile, "UserService", lambda _db: service)
    monkeypatch.setattr(profile, "profile_command", AsyncMock())
    monkeypatch.setattr(
        "bot.middlewares.auth.auth_middleware.invalidate", Mock()
    )

    query = SimpleNamespace(
        data="lang_en",
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    context = SimpleNamespace(user_data={"user": {"language": "am"}})
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=101),
    )

    await profile.language_callback(update, context)

    service.update_user.assert_awaited_once()
    assert context.user_data["language"] == "en"
    assert context.user_data["user"]["language"] == "en"
    query.answer.assert_awaited_once()
    profile.profile_command.assert_awaited_once_with(update, context)


@pytest.mark.asyncio
async def test_onboarding_language_change_commits_and_updates_live_context(monkeypatch):
    from bot.handlers import start

    user = SimpleNamespace(id=17)
    service = AsyncMock()
    service.get_user_by_telegram.return_value = user

    @asynccontextmanager
    async def transaction_session():
        yield object()

    monkeypatch.setattr(start, "transaction_session", transaction_session)
    monkeypatch.setattr(start, "UserService", lambda _db: service)
    monkeypatch.setattr(
        "bot.middlewares.auth.auth_middleware.invalidate", Mock()
    )

    query = SimpleNamespace(
        data="onboard_lang_om",
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=102),
        effective_message=SimpleNamespace(reply_text=AsyncMock()),
    )
    context = SimpleNamespace(user_data={})

    await start.onboard_language_callback(update, context)

    service.update_user.assert_awaited_once()
    assert context.user_data["language"] == "om"
    assert context.user_data["user"]["language"] == "om"
    assert context.user_data["onboarding_lang"] == "om"
    query.answer.assert_awaited_once()


def test_supported_language_set_is_complete():
    assert SUPPORTED_LANGUAGES == {"am", "en", "om"}
