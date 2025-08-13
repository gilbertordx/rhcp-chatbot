import os
import tempfile
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.infra.logging import setup_logging


class TestModelReadiness:
    """Test model file readiness checks in /readyz endpoint."""
    
    def setup_method(self):
        """Setup test environment."""
        setup_logging(level="INFO", format_type="json", debug=False)
        self.client = TestClient(app)
    
    def test_readyz_with_model_file_present(self, tmp_path):
        """Test /readyz returns ready:true when model file is present."""
        # Create a fake model file
        model_file = tmp_path / "model.bin"
        model_file.write_bytes(b"fake model data")
        
        # Mock the model path to point to our fake file
        with patch.dict(os.environ, {"RHCP_MODEL_PATH": str(model_file)}):
            # Need to reload the app to pick up new env vars
            from importlib import reload
            import app.config
            reload(app.config)
            
            response = self.client.get("/readyz")
            
            # Should return 503 because other dependencies aren't initialized
            # but model_file should show as ready
            assert response.status_code == 503
            data = response.json()
            assert data["ready"] is False
            assert "model_file" in data["details"]
            assert "ready:" in data["details"]["model_file"]
            assert "bytes" in data["details"]["model_file"]
    
    def test_readyz_with_model_file_missing(self):
        """Test /readyz returns ready:false when model file is missing."""
        # Mock the model path to point to non-existent file
        with patch.dict(os.environ, {"RHCP_MODEL_PATH": "/nonexistent/model.bin"}):
            # Need to reload the app to pick up new env vars
            from importlib import reload
            import app.config
            reload(app.config)
            
            response = self.client.get("/readyz")
            
            assert response.status_code == 503
            data = response.json()
            assert data["ready"] is False
            assert "model_file" in data["details"]
            assert "not found" in data["details"]["model_file"]
    
    def test_readyz_with_model_file_empty(self, tmp_path):
        """Test /readyz returns ready:false when model file is empty."""
        # Create an empty model file
        model_file = tmp_path / "empty_model.bin"
        model_file.write_bytes(b"")
        
        # Mock the model path to point to our empty file
        with patch.dict(os.environ, {"RHCP_MODEL_PATH": str(model_file)}):
            # Need to reload the app to pick up new env vars
            from importlib import reload
            import app.config
            reload(app.config)
            
            response = self.client.get("/readyz")
            
            assert response.status_code == 503
            data = response.json()
            assert data["ready"] is False
            assert "model_file" in data["details"]
            assert "empty file" in data["details"]["model_file"]
    
    def test_readyz_with_model_file_not_readable(self, tmp_path):
        """Test /readyz returns ready:false when model file is not readable."""
        # Create a model file
        model_file = tmp_path / "unreadable_model.bin"
        model_file.write_bytes(b"fake model data")
        
        # Make it unreadable
        os.chmod(model_file, 0o000)
        
        try:
            # Mock the model path to point to our unreadable file
            with patch.dict(os.environ, {"RHCP_MODEL_PATH": str(model_file)}):
                # Need to reload the app to pick up new env vars
                from importlib import reload
                import app.config
                reload(app.config)
                
                response = self.client.get("/readyz")
                
                assert response.status_code == 503
                data = response.json()
                assert data["ready"] is False
                assert "model_file" in data["details"]
                assert "not readable" in data["details"]["model_file"]
        finally:
            # Restore permissions for cleanup
            os.chmod(model_file, 0o644)
    
    def test_readyz_with_custom_model_path(self, tmp_path):
        """Test /readyz works with custom RHCP_MODEL_PATH."""
        # Create a model file in a custom location
        custom_model_dir = tmp_path / "custom_models"
        custom_model_dir.mkdir()
        model_file = custom_model_dir / "rhcp_model.joblib"
        model_file.write_bytes(b"custom model data")
        
        # Mock the model path to point to our custom file
        with patch.dict(os.environ, {"RHCP_MODEL_PATH": str(model_file)}):
            # Need to reload the app to pick up new env vars
            from importlib import reload
            import app.config
            reload(app.config)
            
            response = self.client.get("/readyz")
            
            # Should return 503 because other dependencies aren't initialized
            # but model_file should show as ready
            assert response.status_code == 503
            data = response.json()
            assert data["ready"] is False
            assert "model_file" in data["details"]
            assert "ready:" in data["details"]["model_file"]
            assert "bytes" in data["details"]["model_file"]
            assert "custom_models/rhcp_model.joblib" in data["details"]["model_file"]
    
    def test_readyz_default_model_path(self):
        """Test /readyz uses default model path when RHCP_MODEL_PATH not set."""
        # Clear RHCP_MODEL_PATH to use default
        with patch.dict(os.environ, {}, clear=True):
            # Need to reload the app to pick up new env vars
            from importlib import reload
            import app.config
            reload(app.config)
            
            response = self.client.get("/readyz")
            
            assert response.status_code == 503
            data = response.json()
            assert "model_file" in data["details"]
            # Should show default path
            assert "data/model.bin" in data["details"]["model_file"] 