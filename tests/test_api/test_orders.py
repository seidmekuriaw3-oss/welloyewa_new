# ============================
# WOLLOYEWA STORE BOT - ORDERS API TESTS
# ============================
"""Tests for order management endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.api
class TestOrderEndpoints:
    """Tests for order endpoints."""

    async def test_create_order(
        self, client: AsyncClient, sample_user_data, sample_order_data, auth_token
    ):
        """Test creating an order."""
        # Register user
        await client.post("/api/v1/users/register", json=sample_user_data)

        # Create order
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.post("/api/v1/orders/", json=sample_order_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert "order_number" in data
        assert "status" in data
        assert "total" in data

    async def test_create_order_ignores_client_supplied_discount(
        self, client: AsyncClient, sample_user_data, sample_order_data, auth_token
    ):
        """Client input must not grant an unauthorized order discount."""
        await client.post("/api/v1/users/register", json=sample_user_data)
        order_data = {**sample_order_data, "discount": 100000, "shipping_fee": 0}
        headers = {"Authorization": f"******"}

        response = await client.post("/api/v1/orders/", json=order_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["discount"] == 0
        expected_shipping_fee = 0 if data["subtotal"] >= 1000 else 50
        assert data["shipping_fee"] == expected_shipping_fee
        assert data["total"] == pytest.approx(
            data["subtotal"] + data["shipping_fee"] + data["tax"]
        )

    async def test_create_order_with_invalid_product(
        self, client: AsyncClient, sample_user_data, auth_token
    ):
        """Test creating order with invalid product."""
        await client.post("/api/v1/users/register", json=sample_user_data)

        invalid_order = {
            "items": [{"product_id": 99999, "quantity": 1}],
            "payment_method": "chapa",
            "shipping_address": "123 Test St",
            "shipping_city": "Addis Ababa",
            "shipping_phone": "0912345678",
        }
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.post("/api/v1/orders/", json=invalid_order, headers=headers)

        assert response.status_code == 404

    async def test_get_my_orders(
        self, client: AsyncClient, sample_user_data, sample_order_data, auth_token
    ):
        """Test getting user's orders."""
        # Register user
        await client.post("/api/v1/users/register", json=sample_user_data)

        # Create an order
        headers = {"Authorization": f"Bearer {auth_token}"}
        await client.post("/api/v1/orders/", json=sample_order_data, headers=headers)

        # Get orders
        response = await client.get("/api/v1/orders/", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_get_order_by_id(
        self, client: AsyncClient, sample_user_data, sample_order_data, auth_token
    ):
        """Test getting order by ID."""
        # Register user
        await client.post("/api/v1/users/register", json=sample_user_data)

        # Create order
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_response = await client.post(
            "/api/v1/orders/", json=sample_order_data, headers=headers
        )
        order_id = create_response.json()["id"]

        # Get order
        response = await client.get(f"/api/v1/orders/{order_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == order_id

    async def test_cancel_order(
        self, client: AsyncClient, sample_user_data, sample_order_data, auth_token
    ):
        """Test cancelling an order."""
        # Register user
        await client.post("/api/v1/users/register", json=sample_user_data)

        # Create order
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_response = await client.post(
            "/api/v1/orders/", json=sample_order_data, headers=headers
        )
        order_id = create_response.json()["id"]

        # Cancel order
        response = await client.put(
            f"/api/v1/orders/{order_id}/cancel?reason=Changed mind", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"


class TestOrderTrackingEndpoints:
    """Tests for order tracking endpoints."""

    async def test_track_order(
        self, client: AsyncClient, sample_user_data, sample_order_data, auth_token
    ):
        """Test tracking an order."""
        # Register user
        await client.post("/api/v1/users/register", json=sample_user_data)

        # Create order
        headers = {"Authorization": f"Bearer {auth_token}"}
        create_response = await client.post(
            "/api/v1/orders/", json=sample_order_data, headers=headers
        )
        order_number = create_response.json()["order_number"]

        # Track order (public endpoint - no auth)
        response = await client.get(f"/api/v1/orders/track/{order_number}?email=test@example.com")

        assert response.status_code == 200
        data = response.json()
        assert "order_number" in data
        assert "status" in data

    async def test_track_order_without_contact(self, client: AsyncClient):
        """Test tracking order without contact info."""
        response = await client.get("/api/v1/orders/track/ORD12345")

        assert response.status_code == 400

    async def test_track_order_rejects_unmatched_contact(
        self, client: AsyncClient, sample_user_data, sample_order_data, auth_token
    ):
        """Order number alone must not reveal order tracking details."""
        await client.post("/api/v1/users/register", json=sample_user_data)
        headers = {"Authorization": f"******"}
        create_response = await client.post(
            "/api/v1/orders/", json=sample_order_data, headers=headers
        )
        order_number = create_response.json()["order_number"]

        response = await client.get(
            f"/api/v1/orders/track/{order_number}?email=attacker@example.com"
        )

        assert response.status_code == 404


class TestVendorOrderEndpoints:
    """Tests for vendor order endpoints."""

    async def test_pending_vendor_cannot_access_orders(
        self, client: AsyncClient, sample_user_data, sample_vendor_application_data, auth_token
    ):
        """A submitted but unapproved application must not grant vendor access."""
        # Register as vendor
        await client.post("/api/v1/users/register", json=sample_user_data)
        vendor_data = sample_vendor_application_data
        headers = {"Authorization": f"Bearer {auth_token}"}
        await client.post("/api/v1/users/vendor/register", json=vendor_data, headers=headers)

        # Get vendor orders
        response = await client.get("/api/v1/orders/vendor/orders", headers=headers)

        assert response.status_code == 403

    async def test_update_order_status_vendor(
        self,
        client: AsyncClient,
        sample_user_data,
        sample_order_data,
        sample_vendor_application_data,
        auth_token,
    ):
        """A pending vendor cannot access the order status workflow."""
        # Register as vendor
        await client.post("/api/v1/users/register", json=sample_user_data)
        vendor_data = sample_vendor_application_data
        headers = {"Authorization": f"Bearer {auth_token}"}
        await client.post("/api/v1/users/vendor/register", json=vendor_data, headers=headers)

        response = await client.get("/api/v1/orders/vendor/orders", headers=headers)
        assert response.status_code == 403


class TestAdminOrderEndpoints:
    """Tests for admin order endpoints."""

    async def test_admin_get_all_orders(self, client: AsyncClient, admin_token):
        """Test admin getting all orders."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get("/api/v1/orders/admin/orders", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_admin_update_order_status(
        self, client: AsyncClient, sample_user_data, sample_order_data, admin_token
    ):
        """Test admin updating order status."""
        # Create order as user
        await client.post("/api/v1/users/register", json=sample_user_data)
        user_headers = {"Authorization": f"Bearer {admin_token}"}
        create_response = await client.post(
            "/api/v1/orders/", json=sample_order_data, headers=user_headers
        )
        order_id = create_response.json()["id"]

        # Admin update status
        headers = {"Authorization": f"Bearer {admin_token}"}
        status_data = {"status": "shipped"}
        response = await client.put(
            f"/api/v1/orders/admin/orders/{order_id}/status", json=status_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shipped"


__all__ = [
    "TestAdminOrderEndpoints",
    "TestOrderEndpoints",
    "TestOrderTrackingEndpoints",
    "TestVendorOrderEndpoints",
]
