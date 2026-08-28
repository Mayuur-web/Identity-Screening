"""Tests for the verification history DELETE endpoint."""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestDeleteEndpoint:
    """Tests for DELETE /api/history/{document_id}."""

    def test_delete_returns_404_for_nonexistent_record(self):
        """Deleting a non-existent record should return 404."""
        with patch(
            "app.api.routes.history.delete_verification_record"
        ) as mock_delete:
            mock_delete.return_value = {
                "success": False,
                "message": "No record found for DOC-NONEXISTENT",
                "deleted": 0,
            }

            response = client.delete("/api/history/DOC-NONEXISTENT")
            assert response.status_code == 404
            data = response.json()
            assert "No record found" in data["detail"]

    def test_delete_success(self):
        """Deleting an existing record should return 200 with success."""
        with patch(
            "app.api.routes.history.delete_verification_record"
        ) as mock_delete:
            mock_delete.return_value = {
                "success": True,
                "message": "Record DOC-TEST123 deleted",
                "deleted": 1,
            }

            response = client.delete("/api/history/DOC-TEST123")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["deleted"] == 1

    def test_delete_supabase_error_returns_500(self):
        """Supabase connection failure should return 500."""
        with patch(
            "app.api.routes.history.delete_verification_record"
        ) as mock_delete:
            mock_delete.return_value = {
                "success": False,
                "message": "Supabase unavailable",
                "deleted": 0,
            }

            response = client.delete("/api/history/DOC-FAIL")
            assert response.status_code == 500

    def test_delete_endpoint_exists(self):
        """Verify DELETE endpoint is registered."""
        routes = [r.path for r in app.routes]
        assert "/api/history/{document_id}" in routes

    def test_get_history_still_works(self):
        """Verify GET /api/history is not broken."""
        response = client.get("/api/history?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "records" in data
