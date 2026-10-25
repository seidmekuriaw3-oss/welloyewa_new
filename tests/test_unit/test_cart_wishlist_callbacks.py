from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.handlers.cart import cart_callback
from bot.handlers.wishlist import wishlist_callback


@pytest.mark.asyncio
async def test_add_to_cart_updates_cart_and_answers_once_with_confirmation():
    query = SimpleNamespace(data="add_to_cart_11", answer=AsyncMock())
    context = SimpleNamespace(user_data={"cart": [{"product_id": 11, "quantity": 1}]})

    await cart_callback(SimpleNamespace(callback_query=query), context)

    assert context.user_data["cart"] == [{"product_id": 11, "quantity": 2}]
    query.answer.assert_awaited_once_with("✅ ወደ ቅርጫት ተጨምሯል!")


@pytest.mark.asyncio
async def test_add_to_wishlist_updates_list_and_answers_once_with_confirmation():
    query = SimpleNamespace(data="add_to_wishlist_11", answer=AsyncMock())
    context = SimpleNamespace(user_data={"wishlist": []})

    await wishlist_callback(SimpleNamespace(callback_query=query), context)

    assert len(context.user_data["wishlist"]) == 1
    assert context.user_data["wishlist"][0]["product_id"] == 11
    query.answer.assert_awaited_once_with("⭐ ወደ ተመራጮች ተጨምሯል!")


@pytest.mark.asyncio
async def test_add_existing_wishlist_item_reports_it_without_duplicating():
    existing_item = {"product_id": 11, "added_at": "2026-10-23T00:00:00"}
    query = SimpleNamespace(data="add_to_wishlist_11", answer=AsyncMock())
    context = SimpleNamespace(user_data={"wishlist": [existing_item]})

    await wishlist_callback(SimpleNamespace(callback_query=query), context)

    assert context.user_data["wishlist"] == [existing_item]
    query.answer.assert_awaited_once_with("⭐ ይህ ምርት ቀድሞውኑ በተመራጮች ውስጥ አለ።")
