"""Integration tests for the /api/alert-rules endpoints."""

import pytest
from unittest.mock import AsyncMock, patch


RULE = {
    "name": "High humidity",
    "sensor_id": None,
    "metric": "humidity",
    "operator": ">",
    "threshold": 70.0,
    "channel": "email",
    "channel_target": "alert@example.com",
    "cooldown_minutes": 30,
}


@pytest.mark.asyncio
class TestAlertRulesCRUD:
    async def test_list_empty(self, client):
        resp = await client.get("/api/alert-rules")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_rule(self, client):
        resp = await client.post("/api/alert-rules", json=RULE)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "High humidity"
        assert data["metric"] == "humidity"
        assert data["operator"] == ">"
        assert data["threshold"] == 70.0
        assert data["is_active"] is True
        assert data["last_triggered_at"] is None

    async def test_list_after_create(self, client):
        await client.post("/api/alert-rules", json=RULE)
        await client.post("/api/alert-rules", json={**RULE, "name": "Low battery", "metric": "battery", "operator": "<", "threshold": 20})
        resp = await client.get("/api/alert-rules")
        assert len(resp.json()) == 2

    async def test_get_rule(self, client):
        created = (await client.post("/api/alert-rules", json=RULE)).json()
        resp = await client.get(f"/api/alert-rules/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    async def test_get_nonexistent(self, client):
        resp = await client.get("/api/alert-rules/999")
        assert resp.status_code == 404

    async def test_patch_rule(self, client):
        created = (await client.post("/api/alert-rules", json=RULE)).json()
        resp = await client.patch(f"/api/alert-rules/{created['id']}", json={"threshold": 80.0})
        assert resp.status_code == 200
        assert resp.json()["threshold"] == 80.0

    async def test_disable_rule(self, client):
        created = (await client.post("/api/alert-rules", json=RULE)).json()
        resp = await client.patch(f"/api/alert-rules/{created['id']}", json={"is_active": False})
        assert resp.json()["is_active"] is False

    async def test_delete_rule(self, client):
        created = (await client.post("/api/alert-rules", json=RULE)).json()
        resp = await client.delete(f"/api/alert-rules/{created['id']}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/alert-rules/{created['id']}")
        assert resp.status_code == 404

    async def test_delete_nonexistent(self, client):
        resp = await client.delete("/api/alert-rules/999")
        assert resp.status_code == 404

    async def test_test_rule_success(self, client):
        created = (await client.post("/api/alert-rules", json=RULE)).json()

        mock_notifier = AsyncMock()
        mock_notifier.send = AsyncMock()

        with patch("app.api.alert_rules.NOTIFIERS", {"email": mock_notifier}):
            resp = await client.post(f"/api/alert-rules/{created['id']}/test")

        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"
        mock_notifier.send.assert_called_once()

    async def test_test_rule_notifier_failure(self, client):
        created = (await client.post("/api/alert-rules", json=RULE)).json()

        mock_notifier = AsyncMock()
        mock_notifier.send = AsyncMock(side_effect=RuntimeError("Connection refused"))

        with patch("app.api.alert_rules.NOTIFIERS", {"email": mock_notifier}):
            resp = await client.post(f"/api/alert-rules/{created['id']}/test")

        assert resp.status_code == 502
        assert "Connection refused" in resp.json()["detail"]

    async def test_test_nonexistent_rule(self, client):
        resp = await client.post("/api/alert-rules/999/test")
        assert resp.status_code == 404

    async def test_logs_empty(self, client):
        resp = await client.get("/api/alert-rules/logs")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_all_valid_metrics_accepted(self, client):
        for metric in ("temperature", "humidity", "battery"):
            rule = {**RULE, "metric": metric}
            resp = await client.post("/api/alert-rules", json=rule)
            assert resp.status_code == 201, f"metric={metric} rejected"

    async def test_all_valid_operators_accepted(self, client):
        for op in (">", "<", ">=", "<=", "==", "!="):
            rule = {**RULE, "operator": op}
            resp = await client.post("/api/alert-rules", json=rule)
            assert resp.status_code == 201, f"operator={op} rejected"

    async def test_all_valid_channels_accepted(self, client):
        for channel in ("email", "telegram", "line"):
            rule = {**RULE, "channel": channel}
            resp = await client.post("/api/alert-rules", json=rule)
            assert resp.status_code == 201, f"channel={channel} rejected"

    async def test_invalid_metric_rejected(self, client):
        rule = {**RULE, "metric": "pressure"}
        resp = await client.post("/api/alert-rules", json=rule)
        assert resp.status_code == 422

    async def test_invalid_operator_rejected(self, client):
        rule = {**RULE, "operator": "between"}
        resp = await client.post("/api/alert-rules", json=rule)
        assert resp.status_code == 422

    async def test_invalid_channel_rejected(self, client):
        rule = {**RULE, "channel": "sms"}
        resp = await client.post("/api/alert-rules", json=rule)
        assert resp.status_code == 422
