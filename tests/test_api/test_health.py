# ============================
# WOLLOYEWA STORE BOT - HEALTH API TESTS
# ============================
"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.api
class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    async def test_detailed_health(self, client: AsyncClient):
        """Test detailed health check endpoint."""
        response = await client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
    
    async def test_readiness_probe(self, client: AsyncClient):
        """Test Kubernetes readiness probe."""
        response = await client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)
    
    async def test_liveness_probe(self, client: AsyncClient):
        """Test Kubernetes liveness probe."""
        response = await client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert "alive" in data
        assert data["alive"] is True
    
    async def test_metrics_endpoint(self, client: AsyncClient):
        """Test metrics endpoint."""
        response = await client.get("/health/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "environment" in data
    
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "environment" in data


__all__ = ["TestHealthEndpoints"]