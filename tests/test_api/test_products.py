# ============================
# WOLLOYEWA STORE BOT - PRODUCTS API TESTS
# ============================
"""Tests for product management endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.api
class TestProductEndpoints:
    """Tests for product endpoints."""
    
    async def test_get_products(self, client: AsyncClient):
        """Test getting list of products."""
        response = await client.get("/api/v1/products/")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
    
    async def test_get_products_with_pagination(self, client: AsyncClient):
        """Test getting products with pagination."""
        response = await client.get("/api/v1/products/?page=1&page_size=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
    
    async def test_get_products_with_filters(self, client: AsyncClient):
        """Test getting products with filters."""
        response = await client.get("/api/v1/products/?category=electronics&min_price=100&max_price=5000")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    async def test_get_featured_products(self, client: AsyncClient):
        """Test getting featured products."""
        response = await client.get("/api/v1/products/featured?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_get_new_arrivals(self, client: AsyncClient):
        """Test getting new arrivals."""
        response = await client.get("/api/v1/products/new-arrivals?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_get_product_by_id(self, client: AsyncClient):
        """Test getting product by ID."""
        # First get a product ID from the list
        list_response = await client.get("/api/v1/products/")
        products = list_response.json().get("items", [])
        
        if products:
            product_id = products[0]["id"]
            response = await client.get(f"/api/v1/products/{product_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == product_id
        else:
            pytest.skip("No products found to test")
    
    async def test_get_product_not_found(self, client: AsyncClient):
        """Test getting non-existent product."""
        response = await client.get("/api/v1/products/99999")
        
        assert response.status_code == 404
    
    async def test_search_products(self, client: AsyncClient):
        """Test product search."""
        response = await client.get("/api/v1/products/?search=phone")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestProductReviewsEndpoints:
    """Tests for product review endpoints."""
    
    async def test_get_product_reviews(self, client: AsyncClient):
        """Test getting product reviews."""
        # First get a product ID
        list_response = await client.get("/api/v1/products/")
        products = list_response.json().get("items", [])
        
        if products:
            product_id = products[0]["id"]
            response = await client.get(f"/api/v1/products/{product_id}/reviews")
            
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
    
    async def test_get_product_review_summary(self, client: AsyncClient):
        """Test getting product review summary."""
        list_response = await client.get("/api/v1/products/")
        products = list_response.json().get("items", [])
        
        if products:
            product_id = products[0]["id"]
            response = await client.get(f"/api/v1/products/{product_id}/reviews/summary")
            
            assert response.status_code == 200
            data = response.json()
            assert "total_reviews" in data
            assert "average_rating" in data
    
    async def test_create_product_review(self, client: AsyncClient, sample_user_data, auth_token):
        """Test creating product review."""
        # Register user
        await client.post("/api/v1/users/register", json=sample_user_data)
        
        # Get a product ID
        list_response = await client.get("/api/v1/products/")
        products = list_response.json().get("items", [])
        
        if products:
            product_id = products[0]["id"]
            
            review_data = {
                "rating": 5,
                "title": "Great product!",
                "comment": "I really love this product.",
            }
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = await client.post(
                f"/api/v1/products/{product_id}/reviews",
                json=review_data,
                headers=headers
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["rating"] == 5


class TestCategoryEndpoints:
    """Tests for category endpoints."""
    
    async def test_get_categories(self, client: AsyncClient):
        """Test getting all categories."""
        response = await client.get("/api/v1/products/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    async def test_get_category_tree(self, client: AsyncClient):
        """Test getting category tree."""
        response = await client.get("/api/v1/products/categories/tree")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestVendorProductEndpoints:
    """Tests for vendor product management endpoints."""
    
    async def test_get_vendor_products(self, client: AsyncClient, sample_user_data, auth_token):
        """Test getting vendor's products."""
        # Register as vendor
        await client.post("/api/v1/users/register", json=sample_user_data)
        vendor_data = {"business_name": "Test Vendor"}
        headers = {"Authorization": f"Bearer {auth_token}"}
        await client.post("/api/v1/users/vendor/register", json=vendor_data, headers=headers)
        
        # Get vendor products
        response = await client.get("/api/v1/products/vendor/products", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    async def test_create_product(self, client: AsyncClient, sample_user_data, sample_product_data, auth_token):
        """Test creating a product (vendor only)."""
        # Register as vendor
        await client.post("/api/v1/users/register", json=sample_user_data)
        vendor_data = {"business_name": "Test Vendor"}
        headers = {"Authorization": f"Bearer {auth_token}"}
        await client.post("/api/v1/users/vendor/register", json=vendor_data, headers=headers)
        
        # Create product
        response = await client.post("/api/v1/products/", json=sample_product_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_product_data["name"]
        assert "id" in data


__all__ = ["TestProductEndpoints", "TestProductReviewsEndpoints", "TestCategoryEndpoints", "TestVendorProductEndpoints"]