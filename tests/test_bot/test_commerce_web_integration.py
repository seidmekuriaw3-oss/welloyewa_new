from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError as PydanticValidationError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "expected_home", "expected_subtitle"),
    [
        ("am", "መነሻ", "የኢትዮጵያ የመስመር ላይ ሱቅ"),
        ("en", "Home", "Ethiopian Online Store"),
        ("om", "Fuula jalqabaa", "Suuqii Itoophiyaa kan interneetii"),
    ],
)
async def test_storefront_shell_and_homepage_are_localized(
    language, expected_home, expected_subtitle
):
    from bot.web_app.router import index_page

    response = await index_page(SimpleNamespace(query_params={"lang": language}))

    assert response.context["page_language"] == language
    assert response.context["profile_text"]["Home"] == expected_home
    assert response.context["profile_text"]["Ethiopian Online Store"] == expected_subtitle
    assert f'aria-label="{expected_home}"'.encode() in response.body
    assert b'class="home-hero"' in response.body
    assert b'id="languageSelector"' in response.body
    assert b'href="#"' not in response.body
    assert b"pexels.com" not in response.body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "expected_review", "expected_product_title"),
    [
        ("am", "የደንበኞች ግምገማ", "ምርት"),
        ("en", "Customer reviews", "Product"),
        ("om", "Gamaaggama maamiltootaa", "Meeshaa"),
    ],
)
async def test_product_and_tracking_pages_receive_supported_localization(
    language, expected_review, expected_product_title
):
    from bot.web_app.router import order_tracking_page, product_page

    request = SimpleNamespace(query_params={"lang": language})
    product_response = await product_page(request, 12)
    tracking_response = await order_tracking_page(request)

    assert product_response.context["page_language"] == language
    assert product_response.context["commerce_text"]["review_section"] == expected_review
    assert product_response.context["commerce_text"]["product_page_title"] == expected_product_title
    assert tracking_response.context["page_language"] == language
    assert tracking_response.template.name == "track_order.html"
    assert product_response.context["commerce_text"]["product_add_to_cart"]
    assert b"productReviewForm" in product_response.body
    assert b"orderTrackingForm" in tracking_response.body
    assert b"/api/v1/orders/track/" in tracking_response.body


def test_product_review_comment_is_limited_by_api_schema():
    from apps.products.schemas import ReviewCreate

    with pytest.raises(PydanticValidationError):
        ReviewCreate(rating=5, comment="x" * 2001)


@pytest.mark.asyncio
async def test_telegram_product_review_callback_preserves_product_id():
    from bot.handlers.feedback import WAITING_RATING, start_feedback

    query = Mock(data="review_42")
    query.answer = AsyncMock()
    query.message = Mock(text="Product")
    query.message.edit_text = AsyncMock()
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={"user": {"language": "en"}})

    state = await start_feedback(update, context)

    assert state == WAITING_RATING
    assert context.user_data["product_review_id"] == 42
    assert "Choose a rating" in query.message.edit_text.await_args.args[0]


@pytest.mark.asyncio
async def test_telegram_product_review_uses_review_service_not_support_ticket(monkeypatch):
    from bot.handlers import feedback

    user = SimpleNamespace(id=9)
    service = SimpleNamespace(create_review=AsyncMock())
    transaction = object()

    @asynccontextmanager
    async def fake_transaction_session():
        yield transaction

    monkeypatch.setattr(feedback, "transaction_session", fake_transaction_session)
    monkeypatch.setattr(
        feedback,
        "UserService",
        lambda db: SimpleNamespace(
            get_user_by_telegram=AsyncMock(return_value=user)
        ),
    )
    monkeypatch.setattr(feedback, "ReviewService", lambda db: service)
    monkeypatch.setattr(
        feedback,
        "TicketService",
        Mock(side_effect=AssertionError("Product reviews must not create support tickets")),
    )

    message = SimpleNamespace(text="  Good quality.  ", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        effective_user=SimpleNamespace(id=123),
        callback_query=None,
        update_id=None,
    )
    context = SimpleNamespace(
        user_data={
            "user": {"language": "en"},
            "product_review_id": 42,
            "feedback_rating": 5,
        }
    )

    state = await feedback.message_handler(update, context)

    assert state == feedback.ConversationHandler.END
    service.create_review.assert_awaited_once()
    assert service.create_review.await_args.kwargs["user_id"] == user.id
    assert service.create_review.await_args.kwargs["product_id"] == 42
    review_data = service.create_review.await_args.kwargs["data"]
    assert review_data.rating == 5
    assert review_data.comment == "Good quality."
    assert context.user_data == {"user": {"language": "en"}}
    assert "moderation" in message.reply_text.await_args.args[0]
