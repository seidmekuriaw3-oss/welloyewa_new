from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from telegram import ReplyKeyboardRemove
from telegram.error import BadRequest

from apps.products.repository import ProductRepository
from apps.users.repository import UserRepository
from apps.users.schemas import UserUpdate
from bot.handlers import catalog, checkout, feedback, location, profile, start
from bot.handlers.search import WAITING_QUERY, filter_callback, search_query_handler
from bot.localization import tr


@pytest.mark.asyncio
async def test_get_product_by_id_eagerly_loads_vendor():
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))
    )
    repository = ProductRepository(db)

    await repository.get_by_id(11)

    statement = db.execute.await_args.args[0]
    assert any(
        getattr(path_item, "key", None) == "vendor"
        for path_item in statement._with_options[0].path
    )


@pytest.mark.asyncio
async def test_search_callback_continues_after_expired_callback_ack():
    query = SimpleNamespace(
        id="expired-query",
        data="search_filter",
        answer=AsyncMock(
            side_effect=BadRequest(
                "Query is too old and response timeout expired or query id is invalid"
            )
        ),
        message=SimpleNamespace(edit_text=AsyncMock()),
    )
    update = SimpleNamespace(callback_query=query)

    await filter_callback(update, SimpleNamespace())

    query.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_repository_loads_addresses_eagerly_for_telegram_lookup():
    db = SimpleNamespace()
    selected = []

    async def fake_execute(stmt):
        selected.append(stmt)
        return SimpleNamespace(scalar_one_or_none=lambda: None)

    db.execute = AsyncMock(side_effect=fake_execute)
    repository = UserRepository(db)

    await repository.get_by_telegram(12345)

    assert selected
    assert any(
        getattr(path_item, "key", None) == "addresses"
        for option in selected[0]._with_options
        for path_item in option.path
    )


@pytest.mark.asyncio
async def test_search_callback_propagates_unexpected_acknowledgement_error():
    query = SimpleNamespace(
        id="query",
        data="search_filter",
        answer=AsyncMock(side_effect=BadRequest("message cannot be edited")),
        message=SimpleNamespace(edit_text=AsyncMock()),
    )

    with pytest.raises(BadRequest, match="message cannot be edited"):
        await filter_callback(
            SimpleNamespace(callback_query=query),
            SimpleNamespace(),
        )

    query.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback_data", "expected_filter", "expected_value"),
    [
        ("filter_in_stock", "in_stock_only", True),
        ("filter_on_sale", "on_sale_only", True),
        ("filter_price_500_2000", "min_price", 500),
        ("filter_rating_4_5", "min_rating", 4.5),
        ("filter_category_electronics", "category", "electronics"),
    ],
)
async def test_search_filter_callbacks_apply_filters(
    callback_data, expected_filter, expected_value, monkeypatch
):
    from bot.handlers.search import FILTER_RESULTS

    monkeypatch.setattr("bot.handlers.search.perform_search", AsyncMock())
    query = SimpleNamespace(
        id="filter-query",
        data=callback_data,
        answer=AsyncMock(),
        message=SimpleNamespace(edit_text=AsyncMock()),
    )
    context = SimpleNamespace(
        user_data={"search_query": "phone", "search_filters": {}, "search_page": 3}
    )

    state = await filter_callback(SimpleNamespace(callback_query=query), context)

    assert state == FILTER_RESULTS
    assert context.user_data["search_filters"][expected_filter] == expected_value
    assert context.user_data["search_page"] == 1


@pytest.mark.asyncio
async def test_search_sort_callback_maps_price_ascending_to_supported_sort(monkeypatch):
    from bot.handlers.search import FILTER_RESULTS

    monkeypatch.setattr("bot.handlers.search.perform_search", AsyncMock())
    query = SimpleNamespace(
        id="sort-query",
        data="sort_price_asc",
        answer=AsyncMock(),
        message=SimpleNamespace(edit_text=AsyncMock()),
    )
    context = SimpleNamespace(user_data={"search_filters": {}, "search_page": 2})

    state = await filter_callback(SimpleNamespace(callback_query=query), context)

    assert state == FILTER_RESULTS
    assert context.user_data["search_filters"]["sort_by"] == "price"
    assert context.user_data["search_filters"]["sort_desc"] is False
    assert context.user_data["search_page"] == 1


@pytest.mark.asyncio
async def test_profile_email_input_is_not_reprocessed_as_product_search():
    message = SimpleNamespace(
        text="not-an-email",
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(update_id=17, effective_message=message, callback_query=None)
    context = SimpleNamespace(
        user_data={"updating_field": "email", "language": "en"}
    )

    await profile.profile_text_handler(update, context)
    await catalog.text_message_handler(update, context)

    message.reply_text.assert_awaited_once()
    assert "valid email address" in message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_profile_update_keeps_field_active_after_database_failure(monkeypatch):
    from sqlalchemy.exc import OperationalError

    @asynccontextmanager
    async def broken_transaction():
        raise OperationalError("update user", {}, RuntimeError("database unavailable"))
        yield

    monkeypatch.setattr(profile, "transaction_session", broken_transaction)
    monkeypatch.setattr("bot.middlewares.auth.auth_middleware.invalidate", Mock())
    message = SimpleNamespace(
        text="customer@gmail.com",
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(
        update_id=170,
        effective_message=message,
        effective_user=SimpleNamespace(id=42),
        callback_query=None,
    )
    context = SimpleNamespace(
        user_data={"updating_field": "email", "language": "en"}
    )

    await profile.profile_text_handler(update, context)

    assert context.user_data["updating_field"] == "email"
    assert "could not save your email" in message.reply_text.await_args.args[0].lower()


@pytest.mark.asyncio
async def test_catalog_text_router_sends_profile_edits_to_profile_handler(monkeypatch):
    message = SimpleNamespace(text="customer@example.com", reply_text=AsyncMock())
    update = SimpleNamespace(
        update_id=171,
        effective_message=message,
        callback_query=None,
    )
    context = SimpleNamespace(user_data={"updating_field": "email"})
    profile_input = AsyncMock()
    monkeypatch.setattr(profile, "profile_text_handler", profile_input)

    await catalog.text_message_handler(update, context)

    profile_input.assert_awaited_once_with(update, context)
    message.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_query_input_is_not_reprocessed_by_catalog_fallback():
    message = SimpleNamespace(text="x", reply_text=AsyncMock())
    update = SimpleNamespace(update_id=18, effective_message=message, callback_query=None)
    context = SimpleNamespace(user_data={"language": "en"})

    state = await search_query_handler(update, context)
    await catalog.text_message_handler(update, context)

    assert state == WAITING_QUERY
    message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["0918498153", "seidmekuriaw@gmail.com"])
async def test_contact_details_are_not_searched_as_product_queries(text):
    message = SimpleNamespace(text=text, reply_text=AsyncMock())
    update = SimpleNamespace(update_id=19, effective_message=message, callback_query=None)
    context = SimpleNamespace(user_data={"language": "en"})

    await catalog.text_message_handler(update, context)

    message.reply_text.assert_awaited_once_with(
        "📞 To update your phone number or email, use /profile."
    )


@pytest.mark.asyncio
async def test_checkout_accepts_shared_location_as_new_address(monkeypatch):
    db = SimpleNamespace(add=Mock())
    monkeypatch.setattr(checkout, "reverse_geocode", AsyncMock(return_value="Addis Ababa"))

    message = SimpleNamespace(
        location=SimpleNamespace(latitude=9.03, longitude=38.74),
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=42),
        message=message,
        callback_query=None,
    )
    context = SimpleNamespace(
        user_data={
            "checkout_in_progress": True,
            "checkout_conversation_active": True,
        }
    )

    result = await checkout.new_address_handler(update, context)

    assert result == checkout.SELECT_RECIPIENT_NAME
    assert context.user_data["checkout_pending_address"] == {
        "address_line1": "Shared location",
        "city": "Addis Ababa",
        "latitude": 9.03,
        "longitude": 38.74,
    }
    db.add.assert_not_called()
    message.reply_text.assert_awaited_once()
    assert message.reply_text.await_args.args[0] == tr(
        context, "checkout_recipient_name_prompt"
    )


@pytest.mark.asyncio
async def test_checkout_collects_recipient_name_and_phone_before_payment(monkeypatch):
    db = SimpleNamespace(add=Mock())

    async def flush_new_address():
        db.add.call_args.args[0].id = 99

    db.flush = AsyncMock(side_effect=flush_new_address)
    service = AsyncMock()
    service.get_user_by_telegram.return_value = SimpleNamespace(id=8)

    @asynccontextmanager
    async def transaction_session():
        yield db

    monkeypatch.setattr(checkout, "transaction_session", transaction_session)
    monkeypatch.setattr(checkout, "UserService", lambda _db: service)

    context = SimpleNamespace(
        user_data={
            "checkout_in_progress": True,
            "checkout_conversation_active": True,
            "checkout_pending_address": {
                "address_line1": "Shared location",
                "city": "Addis Ababa",
                "latitude": 9.03,
                "longitude": 38.74,
            },
        }
    )
    name_message = SimpleNamespace(text="Test Recipient", reply_text=AsyncMock())
    name_update = SimpleNamespace(
        effective_message=name_message,
        message=name_message,
        effective_user=SimpleNamespace(id=42),
        callback_query=None,
    )

    name_state = await checkout.recipient_name_handler(name_update, context)

    assert name_state == checkout.SELECT_RECIPIENT_PHONE
    assert context.user_data["checkout_recipient_name"] == "Test Recipient"

    phone_message = SimpleNamespace(
        contact=SimpleNamespace(phone_number="+251912345678"),
        reply_text=AsyncMock(),
    )
    phone_update = SimpleNamespace(
        effective_message=phone_message,
        message=phone_message,
        effective_user=SimpleNamespace(id=42),
        callback_query=None,
    )

    async def show_methods(update, _context):
        await update.effective_message.reply_text("payment methods")
        return checkout.SELECT_PAYMENT

    monkeypatch.setattr(checkout, "show_payment_methods", show_methods)
    phone_state = await checkout.recipient_phone_handler(phone_update, context)

    assert phone_state == checkout.SELECT_PAYMENT
    assert context.user_data["checkout_address_id"] == 99
    assert context.user_data["checkout_recipient_phone"] == "0912345678"
    saved_address = db.add.call_args.args[0]
    assert saved_address.recipient_name == "Test Recipient"
    assert saved_address.recipient_phone == "0912345678"
    assert saved_address.latitude == 9.03
    assert phone_message.reply_text.await_count == 2


@pytest.mark.asyncio
async def test_checkout_order_uses_confirmed_recipient_and_map_address(monkeypatch):
    address = SimpleNamespace(
        user_id=8,
        address_line1="Bole",
        city="Addis Ababa",
        latitude=9.03,
        longitude=38.74,
        recipient_phone="old-number",
    )
    db = SimpleNamespace(get=AsyncMock(return_value=address))
    user = SimpleNamespace(id=8, full_name="Account Name")
    order = SimpleNamespace(id=17, order_number="ORD-17")
    order_service = SimpleNamespace(
        product_service=SimpleNamespace(
            get_product=AsyncMock(return_value=SimpleNamespace(price=100))
        ),
        create_order=AsyncMock(return_value=order),
    )
    user_service = AsyncMock()
    user_service.get_user_by_telegram.return_value = user

    @asynccontextmanager
    async def transaction_session():
        yield db

    monkeypatch.setattr(checkout, "transaction_session", transaction_session)
    monkeypatch.setattr(checkout, "UserService", lambda _db: user_service)
    monkeypatch.setattr(checkout, "OrderService", lambda _db: order_service)
    monkeypatch.setattr(
        checkout,
        "get_user_cart",
        AsyncMock(return_value=[{"product_id": 5, "quantity": 2}]),
    )
    monkeypatch.setattr(
        checkout, "_process_order_payment", AsyncMock(return_value=checkout.CONFIRM_ORDER)
    )

    context = SimpleNamespace(
        user_data={
            "checkout_address_id": 99,
            "checkout_payment_method": "cash_on_delivery",
            "checkout_recipient_name": "Delivery Recipient",
            "checkout_recipient_phone": "0912345678",
        }
    )
    query = SimpleNamespace(message=SimpleNamespace(edit_text=AsyncMock()))
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42),
    )

    result = await checkout._create_and_process_order(update, context)

    assert result == checkout.CONFIRM_ORDER
    order_data = order_service.create_order.await_args.args[1]
    assert order_data.shipping_phone == "0912345678"
    assert order_data.customer_notes == "Delivery recipient: Delivery Recipient"
    assert "Google Maps: https://maps.google.com/?q=9.03000,38.74000" in (
        order_data.shipping_address
    )


@pytest.mark.asyncio
async def test_checkout_resumes_legacy_payment_step_to_collect_delivery_details():
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(
        data="pay_cod",
        answer=AsyncMock(),
        message=message,
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_message=message,
    )
    context = SimpleNamespace(user_data={"checkout_address_id": 7})

    state = await checkout.payment_callback(update, context)

    assert state == checkout.SELECT_RECIPIENT_NAME
    assert context.user_data["checkout_payment_method"] == "cash_on_delivery"
    assert context.user_data["checkout_resume_confirmation"] is True
    message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_location_handler_ignores_checkout_location():
    message = SimpleNamespace(
        location=SimpleNamespace(latitude=9.03, longitude=38.74),
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(
        message=message,
        effective_user=SimpleNamespace(id=42),
    )
    context = SimpleNamespace(
        user_data={
            "checkout_in_progress": True,
            "checkout_conversation_active": True,
        }
    )

    await location.location_message_handler(update, context)

    message.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_location_handler_recovers_stale_checkout_with_restart_message():
    message = SimpleNamespace(
        location=SimpleNamespace(latitude=9.03, longitude=38.74),
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(user_data={"checkout_in_progress": True})

    await location.location_message_handler(update, context)

    assert "checkout_in_progress" not in context.user_data
    assert message.reply_text.await_args.args[0] == tr(
        context, "checkout_session_expired"
    )


@pytest.mark.asyncio
async def test_phone_profile_update_commits_and_refreshes_cached_user(monkeypatch):
    user = SimpleNamespace(id=8)
    updated_user = SimpleNamespace(phone_number="0918498153")
    service = AsyncMock()
    service.get_user_by_telegram.return_value = user
    service.update_user.return_value = updated_user
    transaction_events = []

    @asynccontextmanager
    async def transaction_session():
        transaction_events.append("begin")
        yield object()
        transaction_events.append("commit")

    monkeypatch.setattr(profile, "transaction_session", transaction_session)
    monkeypatch.setattr(profile, "UserService", lambda _db: service)
    monkeypatch.setattr("bot.middlewares.auth.auth_middleware.invalidate", Mock())

    message = SimpleNamespace(text="0918498153", reply_text=AsyncMock())
    update = SimpleNamespace(
        update_id=20,
        effective_message=message,
        effective_user=SimpleNamespace(id=42),
        callback_query=None,
    )
    context = SimpleNamespace(
        user_data={
            "updating_field": "phone",
            "user": {"phone_number": None},
            "language": "en",
        }
    )

    await profile.profile_text_handler(update, context)

    assert transaction_events == ["begin", "commit"]
    service.update_user.assert_awaited_once()
    assert service.update_user.await_args.args[1] == UserUpdate(phone_number="0918498153")
    assert context.user_data["user"]["phone_number"] == "0918498153"
    assert "Phone number saved" in message.reply_text.await_args.args[0]


@pytest.mark.asyncio
async def test_location_update_uses_supported_fields_and_commits(monkeypatch):
    user = SimpleNamespace(id=8)
    service = AsyncMock()
    service.get_user_by_telegram.return_value = user
    transaction_events = []

    @asynccontextmanager
    async def transaction_session():
        transaction_events.append("begin")
        yield object()
        transaction_events.append("commit")

    monkeypatch.setattr(location, "transaction_session", transaction_session)
    monkeypatch.setattr(location, "UserService", lambda _db: service)
    monkeypatch.setattr(location, "reverse_geocode", AsyncMock(return_value="Addis Ababa"))

    message = SimpleNamespace(
        location=SimpleNamespace(latitude=9.03, longitude=38.74),
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=42),
        message=message,
    )
    context = SimpleNamespace(user_data={"language": "en"})

    await location.location_message_handler(update, context)

    assert transaction_events == ["begin", "commit"]
    assert service.update_user.await_count == 2
    location_update = service.update_user.await_args_list[0].args[1]
    assert location_update.location_lat == 9.03
    assert location_update.location_lng == 38.74
    assert "location has been saved" in message.reply_text.await_args.args[0]
    assert isinstance(
        message.reply_text.await_args.kwargs["reply_markup"],
        ReplyKeyboardRemove,
    )


@pytest.mark.asyncio
async def test_feedback_ticket_uses_database_user_id_and_commits(monkeypatch):
    user_service = AsyncMock()
    user_service.get_user_by_telegram.return_value = SimpleNamespace(id=8)
    ticket_service = AsyncMock()
    transaction_events = []

    @asynccontextmanager
    async def transaction_session():
        transaction_events.append("begin")
        yield object()
        transaction_events.append("commit")

    monkeypatch.setattr(feedback, "transaction_session", transaction_session)
    monkeypatch.setattr(feedback, "UserService", lambda _db: user_service)
    monkeypatch.setattr(feedback, "TicketService", lambda _db: ticket_service)

    message = SimpleNamespace(text="Great service", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=42),
        callback_query=None,
    )
    context = SimpleNamespace(user_data={"feedback_rating": 5})

    await feedback.message_handler(update, context)

    assert transaction_events == ["begin", "commit"]
    assert ticket_service.create_ticket.await_args.kwargs["user_id"] == 8
    assert message.reply_text.await_count == 1


@pytest.mark.asyncio
async def test_main_menu_callback_replies_when_source_is_a_photo():
    message = SimpleNamespace(text=None, reply_text=AsyncMock())
    query = SimpleNamespace(
        data="menu_main",
        answer=AsyncMock(),
        message=message,
        edit_message_text=AsyncMock(),
    )
    update = SimpleNamespace(
        callback_query=query,
        effective_user=SimpleNamespace(id=42),
    )
    context = SimpleNamespace(user_data={"user": {"language": "am"}})

    await start.menu_callback(update, context)

    query.answer.assert_awaited_once()
    message.reply_text.assert_awaited_once()
    query.edit_message_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_feedback_entry_replies_when_source_is_a_photo():
    message = SimpleNamespace(text=None, reply_text=AsyncMock(), edit_text=AsyncMock())
    query = SimpleNamespace(answer=AsyncMock(), message=message)

    await feedback.start_feedback(
        SimpleNamespace(callback_query=query),
        SimpleNamespace(),
    )

    query.answer.assert_awaited_once()
    message.reply_text.assert_awaited_once()
    message.edit_text.assert_not_awaited()
