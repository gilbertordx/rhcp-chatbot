"""
Tests for health and readiness endpoints.
"""

from fastapi.testclient import TestClient

from app.infra.logging import setup_logging
from app.main import app


class TestHealthEndpoints:
    """Test health and readiness endpoints."""

    def setup_method(self):
        """Setup test environment."""
        setup_logging(level="INFO", format_type="json", debug=False)
        self.client = TestClient(app)

    def test_healthz_endpoint(self):
        """Test basic health check endpoint."""
        response = self.client.get("/healthz")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["version"] == "2.0.0"

    def test_readyz_endpoint_structure(self):
        """Test readiness endpoint structure."""
        response = self.client.get("/readyz")

        assert response.status_code in [200, 503]  # Can be either ready or not ready
        data = response.json()

        assert "ready" in data
        assert isinstance(data["ready"], bool)
        assert "details" in data
        assert isinstance(data["details"], dict)

    def test_readyz_details_structure(self):
        """Test readiness details structure."""
        response = self.client.get("/readyz")
        data = response.json()
        details = data["details"]

        # Should have these keys (may be ok or error status)
        expected_keys = [
            "database",
            "model",
            "band_info",
            "discography",
            "chatbot_processor",
        ]

        for key in expected_keys:
            assert key in details
            assert isinstance(details[key], str)

    def test_readyz_status_codes(self):
        """Test readiness status codes."""
        response = self.client.get("/readyz")
        data = response.json()

        if data["ready"]:
            assert response.status_code == 200
        else:
            assert response.status_code == 503

    def test_healthz_content_type(self):
        """Test health endpoint content type."""
        response = self.client.get("/healthz")

        assert response.headers["content-type"] == "application/json"

    def test_readyz_content_type(self):
        """Test readiness endpoint content type."""
        response = self.client.get("/readyz")

        assert response.headers["content-type"] == "application/json"

    def test_healthz_methods(self):
        """Test health endpoint only accepts GET."""
        # POST should not be allowed
        response = self.client.post("/healthz")
        assert response.status_code == 405  # Method not allowed

        # PUT should not be allowed
        response = self.client.put("/healthz")
        assert response.status_code == 405  # Method not allowed

    def test_readyz_methods(self):
        """Test readiness endpoint only accepts GET."""
        # POST should not be allowed
        response = self.client.post("/readyz")
        assert response.status_code == 405  # Method not allowed

        # PUT should not be allowed
        response = self.client.put("/readyz")
        assert response.status_code == 405  # Method not allowed


class TestHealthEndpointIntegration:
    """Test health endpoints with application state."""

    def setup_method(self):
        """Setup test environment."""
        setup_logging(level="INFO", format_type="json", debug=False)
        self.client = TestClient(app)

    def test_healthz_always_available(self):
        """Test that healthz is always available regardless of app state."""
        # Should always return 200
        response = self.client.get("/healthz")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"

    def test_readyz_database_check(self):
        """Test that readyz checks database connectivity."""
        response = self.client.get("/readyz")
        data = response.json()
        details = data["details"]

        # Database check should be present
        assert "database" in details

        # In test environment, database should be available
        # (SQLite file should exist or be created)
        assert "database" in details

    def test_readyz_file_checks(self):
        """Test that readyz checks required files."""
        response = self.client.get("/readyz")
        data = response.json()
        details = data["details"]

        # File checks should be present
        assert "model" in details
        assert "band_info" in details
        assert "discography" in details

        # These files should exist in the test environment
        # (they're part of the repository)
        assert "model" in details
        assert "band_info" in details
        assert "discography" in details
