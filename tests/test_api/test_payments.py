"""Tests for payment initiation and verification API behavior."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from infrastructure.payments.base import PaymentResponse, PaymentStatus


@pytest.mark.api
class TestPaymentEndpoints:
    async def test_payment_cannot_be_verified_by_another_customer(
        self, client: AsyncClient, sample_user_data, sample_order_data, auth_token
    ):
        from core.security import create_access_token
        from tests.conftest import make_telegram_init_data

        await client.post("/api/v1/users/register", json=sample_user_data)
        second_user_data = {
            **sample_user_data,
            "telegram_id": 223456789,
            "init_data": make_telegram_init_data(223456789),
            "phone_number": "0912345679",
        }
        second_user = await client.post("/api/v1/users/register", json=second_user_data)
        second_token = create_access_token(
            {"sub": str(second_user.json()["id"]), "role": "customer"}
        )
        headers = {"Authorization": f"Bearer {auth_token}"}
        created = await client.post("/api/v1/orders/", json=sample_order_data, headers=headers)

        with patch(
            "infrastructure.api.v1.endpoints.payments.process_payment", new_callable=AsyncMock
        ) as initiate:
            initiate.return_value = PaymentResponse(
                success=True,
                transaction_id="txn-private-order",
                status=PaymentStatus.PENDING,
            )
            await client.post(
                "/api/v1/payments/initiate",
                json={"order_id": created.json()["id"], "provider": "chapa"},
                headers=headers,
            )

        response = await client.get(
            "/api/v1/payments/verify/txn-private-order?method=chapa",
            headers={"Authorization": f"Bearer {second_token}"},
        )

        assert response.status_code == 404

    async def test_partial_refund_updates_only_after_provider_success(
        self,
        client: AsyncClient,
        db_session,
        sample_user_data,
        sample_order_data,
        auth_token,
        admin_token,
    ):
        from apps.orders.models import Order

        await client.post("/api/v1/users/register", json=sample_user_data)
        headers = {"Authorization": f"Bearer {auth_token}"}
        created = await client.post("/api/v1/orders/", json=sample_order_data, headers=headers)
        order = await db_session.get(Order, created.json()["id"])
        order.payment_status = "paid"
        order.payment_transaction_id = "txn-refund-order"
        await db_session.commit()

        provider = AsyncMock()
        provider.refund_payment.return_value = True
        with patch(
            "infrastructure.api.v1.endpoints.payments.get_payment_provider",
            new_callable=AsyncMock,
            return_value=provider,
        ):
            response = await client.post(
                "/api/v1/payments/refund",
                json={"order_id": order.id, "amount": "2.00", "reason": "Test refund"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )

        await db_session.refresh(order)
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["amount"] == 2.0
        assert order.refunded_amount == Decimal("2.00")
        assert order.payment_status == "paid"

    async def test_payment_transaction_is_saved_and_verified_against_order(
        self,
        client: AsyncClient,
        db_session,
        sample_user_data,
        sample_order_data,
        auth_token,
    ):
        from apps.orders.models import Order
        from infrastructure.payments.base import PaymentResponse, PaymentStatus, PaymentVerification

        await client.post("/api/v1/users/register", json=sample_user_data)
        headers = {"Authorization": f"Bearer {auth_token}"}
        created = await client.post("/api/v1/orders/", json=sample_order_data, headers=headers)
        order_id = created.json()["id"]

        with patch(
            "infrastructure.api.v1.endpoints.payments.process_payment", new_callable=AsyncMock
        ) as initiate:
            initiate.return_value = PaymentResponse(
                success=True,
                transaction_id="txn-order-1",
                status=PaymentStatus.PENDING,
                payment_url="https://payments.example/txn-order-1",
            )
            response = await client.post(
                "/api/v1/payments/initiate",
                json={"order_id": order_id, "provider": "chapa"},
                headers=headers,
            )

        assert response.status_code == 200
        assert (await db_session.get(Order, order_id)).payment_transaction_id == "txn-order-1"

        provider = AsyncMock()
        provider.verify_payment.return_value = PaymentVerification(
            verified=True,
            transaction_id="txn-order-1",
            status=PaymentStatus.COMPLETED,
            amount=Decimal(str(created.json()["total"])),
            currency="ETB",
        )
        with patch(
            "infrastructure.api.v1.endpoints.payments.get_payment_provider",
            new_callable=AsyncMock,
            return_value=provider,
        ):
            response = await client.get(
                "/api/v1/payments/verify/txn-order-1?method=chapa", headers=headers
            )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert (await db_session.get(Order, order_id)).payment_status == "paid"

    async def test_payment_amount_mismatch_does_not_mark_order_paid(
        self,
        client: AsyncClient,
        db_session,
        sample_user_data,
        sample_order_data,
        auth_token,
    ):
        from apps.orders.models import Order
        from infrastructure.payments.base import PaymentResponse, PaymentStatus, PaymentVerification

        await client.post("/api/v1/users/register", json=sample_user_data)
        headers = {"Authorization": f"Bearer {auth_token}"}
        created = await client.post("/api/v1/orders/", json=sample_order_data, headers=headers)
        order_id = created.json()["id"]

        with patch(
            "infrastructure.api.v1.endpoints.payments.process_payment", new_callable=AsyncMock
        ) as initiate:
            initiate.return_value = PaymentResponse(
                success=True,
                transaction_id="txn-order-2",
                status=PaymentStatus.PENDING,
            )
            await client.post(
                "/api/v1/payments/initiate",
                json={"order_id": order_id, "provider": "chapa"},
                headers=headers,
            )

        provider = AsyncMock()
        provider.verify_payment.return_value = PaymentVerification(
            verified=True,
            transaction_id="txn-order-2",
            status=PaymentStatus.COMPLETED,
            amount=Decimal("1.00"),
            currency="ETB",
        )
        with patch(
            "infrastructure.api.v1.endpoints.payments.get_payment_provider",
            new_callable=AsyncMock,
            return_value=provider,
        ):
            response = await client.get(
                "/api/v1/payments/verify/txn-order-2?method=chapa", headers=headers
            )

        assert response.status_code == 200
        assert response.json()["success"] is False
        assert (await db_session.get(Order, order_id)).payment_status == "pending"
