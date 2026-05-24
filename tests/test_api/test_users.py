# ============================
# WOLLOYEWA STORE BOT - USERS API TESTS
# ============================
"""Tests for user management endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.api
class TestUserEndpoints:
    """Tests for user endpoints."""
    
    async def test_register_user(self, client: AsyncClient, sample_user_data):
        """Test user registration."""
        response = await client.post("/api/v1/users/register", json=sample_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["telegram_id"] == sample_user_data["telegram_id"]
        assert data["first_name"] == sample_user_data["first_name"]
        assert "id" in data
    
    async def test_register_duplicate_user(self, client: AsyncClient, sample_user_data):
        """Test registering duplicate user."""
        # First registration
        await client.post("/api/v1/users/register", json=sample_user_data)
        
        # Second registration (should fail)
        response = await client.post("/api/v1/users/register", json=sample_user_data)
        
        assert response.status_code == 409
    
    async def test_login_user(self, client: AsyncClient, sample_user_data):
        """Test user login."""
        # Register user first
        await client.post("/api/v1/users/register", json=sample_user_data)
        
        # Login
        login_data = {
            "telegram_id": sample_user_data["telegram_id"],
        }
        response = await client.post("/api/v1/users/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert "user" in data
    
    async def test_login_invalid_user(self, client: AsyncClient):
        """Test login with invalid user."""
        login_data = {"telegram_id": 999999999}
        response = await client.post("/api/v1/users/login", json=login_data)
        
        assert response.status_code == 401
    
    async def test_get_current_user_profile(self, client: AsyncClient, sample_user_data, auth_token):
        """Test getting current user profile."""
        # Register user
        await client.post("/api/v1/users/register", json=sample_user_data)
        
        # Get profile with token
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["telegram_id"] == sample_user_data["telegram_id"]
    
    async def test_update_current_user(self, client: AsyncClient, sample_user_data, auth_token):
        """Test updating current user profile."""
        # Register user
        await client.post("/api/v1/users/register", json=sample_user_data)
        
        # Update profile
        update_data = {"first_name": "UpdatedName"}
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.put("/api/v1/users/me", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "UpdatedName"
    
    async def test_change_password(self, client: AsyncClient, sample_user_data, auth_token):
        """Test changing user password."""
        # Register user
        await client.post("/api/v1/users/register", json=sample_user_data)
        
        # Change password
        password_data = {
            "current_password": "oldpassword",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        }
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.post("/api/v1/users/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestAdminUserEndpoints:
    """Tests for admin user endpoints."""
    
    async def test_get_all_users_admin(self, client: AsyncClient, sample_user_data, admin_token):
        """Test getting all users (admin only)."""
        # Register a user
        await client.post("/api/v1/users/register", json=sample_user_data)
        
        # Get users with admin token
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get("/api/v1/users/", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    async def test_get_user_by_id_admin(self, client: AsyncClient, sample_user_data, admin_token):
        """Test getting user by ID (admin only)."""
        # Register user
        register_response = await client.post("/api/v1/users/register", json=sample_user_data)
        user_id = register_response.json()["id"]
        
        # Get user with admin token
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
    
    async def test_update_user_by_id_admin(self, client: AsyncClient, sample_user_data, admin_token):
        """Test updating user by ID (admin only)."""
        # Register user
        register_response = await client.post("/api/v1/users/register", json=sample_user_data)
        user_id = register_response.json()["id"]
        
        # Update user with admin token
        update_data = {"status": "suspended"}
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.put(f"/api/v1/users/{user_id}", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "suspended"
    
    async def test_delete_user_admin(self, client: AsyncClient, sample_user_data, admin_token):
        """Test deleting user (admin only)."""
        # Register user
        register_response = await client.post("/api/v1/users/register", json=sample_user_data)
        user_id = register_response.json()["id"]
        
        # Delete user with admin token
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.delete(f"/api/v1/users/{user_id}", headers=headers)
        
        assert response.status_code == 200


class TestVendorEndpoints:
    """Tests for vendor endpoints."""
    
    async def test_register_vendor(self, client: AsyncClient, sample_user_data, auth_token):
        """Test vendor registration."""
        # Register as customer first
        await client.post("/api/v1/users/register", json=sample_user_data)
        
        # Register as vendor
        vendor_data = {
            "business_name": "Test Business",
            "business_license": "LIC123456",
            "tin_number": "1234567890",
            "business_address": "123 Test St",
            "business_phone": "0912345678",
        }
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await client.post("/api/v1/users/vendor/register", json=vendor_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["business_name"] == vendor_data["business_name"]
        assert "user_id" in data
    
    async def test_get_vendor_profile(self, client: AsyncClient, sample_user_data, auth_token):
        """Test getting vendor profile."""
        # Register as customer
        await client.post("/api/v1/users/register", json=sample_user_data)
        
        # Register as vendor
        vendor_data = {"business_name": "Test Business"}
        headers = {"Authorization": f"Bearer {auth_token}"}
        await client.post("/api/v1/users/vendor/register", json=vendor_data, headers=headers)
        
        # Get vendor profile
        response = await client.get("/api/v1/users/vendor/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["business_name"] == "Test Business"


__all__ = ["TestUserEndpoints", "TestAdminUserEndpoints", "TestVendorEndpoints"]