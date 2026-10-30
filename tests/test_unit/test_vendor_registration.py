from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from apps.users.schemas import VendorApplicationCreate
from apps.users.services import VendorService
from bot.handlers.vendor_registration import (
    VENDOR_CONFIRM_STATE,
    _step_keyboard,
    application_choice_callback,
    application_navigation_callback,
    handle_text,
)


def _valid_application_data() -> dict[str, str]:
    return {
        "business_name": "Wolloyewa Furniture",
        "business_license": "ABC12345",
        "tin_number": "1234567890",
        "license_document_file_id": "telegram-file-id",
        "license_document_type": "photo",
        "business_category": "Furniture",
        "region": "Amhara",
        "city": "Bahir Dar",
        "subcity": "Kebele 01",
        "specific_location": "Near the central market",
        "business_address": "Amhara, Bahir Dar, Kebele 01, Near the central market",
        "business_phone": "0912345678",
        "bank_name": "Commercial Bank",
        "bank_account_name": "Wolloyewa Furniture",
        "bank_account_number": "00123456789",
        "maps_link": "https://maps.google.com/?q=11.59,37.39",
    }


@pytest.mark.unit
def test_vendor_application_validates_required_data_and_normalizes_values():
    data = _valid_application_data()
    data["business_license"] = "abc12345"
    data["business_phone"] = "+251 912 345 678"
    data["bank_account_number"] = "0012-345 6789"

    application = VendorApplicationCreate.model_validate(data)

    assert application.business_license == "ABC12345"
    assert application.business_phone == "0912345678"
    assert application.bank_account_number == "00123456789"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tin_number", "12345"),
        ("business_phone", "123456"),
        ("bank_account_number", "1234"),
        ("license_document_type", "archive"),
        ("maps_link", "not-a-url"),
    ],
)
def test_vendor_application_rejects_invalid_fields(field: str, value: str):
    data = _valid_application_data()
    data[field] = value

    with pytest.raises(ValidationError):
        VendorApplicationCreate.model_validate(data)


@pytest.mark.unit
def test_vendor_application_inline_choices_include_navigation_controls():
    category_keyboard = _step_keyboard(4)
    category_callbacks = [
        button.callback_data
        for row in category_keyboard.inline_keyboard
        for button in row
    ]
    assert "vendor_choice_category_electronics" in category_callbacks
    assert "vendor_application_back" in category_callbacks
    assert "vendor_application_cancel" in category_callbacks

    bank_keyboard = _step_keyboard(10)
    bank_callbacks = [
        button.callback_data
        for row in bank_keyboard.inline_keyboard
        for button in row
    ]
    assert "vendor_choice_bank_cbe" in bank_callbacks
    assert "vendor_choice_bank_other" in bank_callbacks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vendor_application_text_flow_rejects_invalid_tin_without_advancing():
    message = SimpleNamespace(text="12345", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        update_id=1,
        callback_query=None,
    )
    context = SimpleNamespace(
        user_data={
            "vendor_application_step": 3,
            "vendor_application_draft": {},
        }
    )

    await handle_text(update, context)

    assert context.user_data["vendor_application_step"] == 3
    assert "vendor_application_draft" in context.user_data
    message.reply_text.assert_awaited_once()
    assert "10 digits" in message.reply_text.await_args.args[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vendor_application_step_one_advances_to_business_license():
    message = SimpleNamespace(text="ethiosadat furnitur", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        update_id=2,
        callback_query=None,
    )
    context = SimpleNamespace(
        user_data={
            "vendor_application_step": 0,
            "vendor_application_draft": {},
        }
    )

    next_state = await handle_text(update, context)

    assert next_state == 1
    assert context.user_data["vendor_application_step"] == 1
    assert context.user_data["vendor_application_draft"]["business_name"] == "ethiosadat furnitur"
    message.reply_text.assert_awaited_once()
    assert "Step 2/14" in message.reply_text.await_args.args[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vendor_category_inline_choice_saves_value_and_advances():
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(
        data="vendor_choice_category_electronics",
        answer=AsyncMock(),
        message=message,
    )
    update = SimpleNamespace(callback_query=query, effective_message=message)
    context = SimpleNamespace(
        user_data={
            "vendor_application_step": 4,
            "vendor_application_draft": {},
        }
    )

    next_state = await application_choice_callback(update, context)

    assert next_state == 5
    assert context.user_data["vendor_application_draft"]["business_category"] == "Electronics"
    assert context.user_data["vendor_application_step"] == 5
    assert "Step 6/14" in message.reply_text.await_args.args[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vendor_application_back_returns_to_previous_step():
    message = SimpleNamespace(
        edit_text=AsyncMock(),
        reply_text=AsyncMock(),
    )
    query = SimpleNamespace(
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        message=message,
    )
    update = SimpleNamespace(callback_query=query, effective_message=message)
    context = SimpleNamespace(
        user_data={
            "vendor_application_step": "confirm",
            "vendor_application_draft": _valid_application_data(),
        }
    )

    previous_state = await application_navigation_callback(update, context)

    assert previous_state == 13
    assert context.user_data["vendor_application_step"] == 13
    assert "Step 14/14" in message.reply_text.await_args.args[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vendor_business_license_uses_active_conversation_state():
    message = SimpleNamespace(text="314354", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        update_id=3,
        callback_query=None,
    )
    context = SimpleNamespace(
        user_data={
            "vendor_application_step": 0,
            "vendor_application_draft": {"business_name": "ethiosadat furnitur"},
        }
    )

    next_state = await handle_text(update, context, step_index=1)

    assert next_state == 2
    assert context.user_data["vendor_application_step"] == 2
    assert context.user_data["vendor_application_draft"]["business_license"] == "314354"
    message.reply_text.assert_awaited_once()
    assert "Step 3/14" in message.reply_text.await_args.args[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vendor_final_step_recovers_when_bank_account_number_is_missing():
    message = SimpleNamespace(text="0912345678", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        update_id=4,
        callback_query=None,
    )
    draft = _valid_application_data()
    draft.pop("bank_account_number")
    context = SimpleNamespace(
        user_data={
            "vendor_application_step": 13,
            "vendor_application_draft": draft,
        }
    )

    next_state = await handle_text(update, context, step_index=13)

    assert next_state == 12
    assert context.user_data["vendor_application_step"] == 12
    assert context.user_data["vendor_application_draft"]["business_phone"] == "0912345678"
    message.reply_text.assert_awaited_once()
    assert "Some application details are missing" in message.reply_text.await_args.args[0]
    assert "Step 13/14 · Bank account number" in message.reply_text.await_args.args[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vendor_final_step_confirms_complete_draft_and_masks_account_number():
    message = SimpleNamespace(text="0912345678", reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_message=message,
        update_id=5,
        callback_query=None,
    )
    context = SimpleNamespace(
        user_data={
            "vendor_application_step": 13,
            "vendor_application_draft": _valid_application_data(),
        }
    )

    next_state = await handle_text(update, context, step_index=13)

    assert next_state == VENDOR_CONFIRM_STATE
    assert context.user_data["vendor_application_step"] == "confirm"
    message.reply_text.assert_awaited_once()
    confirmation = message.reply_text.await_args.args[0]
    assert "••••6789" in confirmation
    assert "0912345678" in confirmation


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vendor_role_is_granted_only_after_admin_approval():
    service = VendorService(AsyncMock())
    service.user_repo = AsyncMock()
    service.vendor_repo = AsyncMock()

    customer = SimpleNamespace(
        id=7,
        role="customer",
        status="active",
        is_deleted=False,
    )
    pending_vendor = SimpleNamespace(
        id=12,
        user_id=7,
        is_approved=False,
        rejected_at=None,
        **_valid_application_data(),
    )
    service.user_repo.get_by_id.return_value = customer
    service.vendor_repo.get_by_user_id.return_value = None
    service.vendor_repo.get_by_license.return_value = None
    service.vendor_repo.get_by_tin.return_value = None
    service.vendor_repo.create.return_value = pending_vendor

    await service.create_vendor(7, VendorApplicationCreate.model_validate(_valid_application_data()))

    service.user_repo.update.assert_awaited_once_with(7, {"phone_number": "0912345678"})

    service.vendor_repo.get_by_id.return_value = pending_vendor
    approved_vendor = SimpleNamespace(id=12, user_id=7, is_approved=True)
    service.vendor_repo.update.return_value = approved_vendor

    result = await service.approve_vendor(12, admin_id=99)

    assert result is approved_vendor
    assert service.user_repo.update.await_args_list[-1].args == (7, {"role": "vendor"})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_incomplete_legacy_application_cannot_be_approved():
    from core.exceptions import ValidationError as ServiceValidationError

    service = VendorService(AsyncMock())
    service.vendor_repo = AsyncMock()
    incomplete_vendor = SimpleNamespace(
        id=12,
        is_approved=False,
        business_name="Legacy store",
    )
    service.vendor_repo.get_by_id.return_value = incomplete_vendor

    with pytest.raises(ServiceValidationError, match="application is incomplete"):
        await service.approve_vendor(12, admin_id=99)

    service.vendor_repo.update.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pending_legacy_vendor_role_cannot_access_vendor_permissions():
    from core.dependencies import get_current_vendor
    from core.exceptions import PermissionError

    current_user = {"id": 7, "role": "vendor"}
    pending_vendor = SimpleNamespace(id=12, is_approved=False)
    repository = AsyncMock()
    repository.get_by_user_id.return_value = pending_vendor

    with pytest.raises(PermissionError, match="not been approved"):
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "apps.users.repository.VendorRepository",
                lambda db: repository,
            )
            await get_current_vendor(current_user=current_user, db=AsyncMock())
