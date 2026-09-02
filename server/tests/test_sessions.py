def test_health_and_dashboard_login(client, login):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.headers["x-frame-options"] == "DENY"
    login(client)
    assert client.get("/api/session").json()["authenticated"] is True
    assert client.get("/api/status").status_code == 200


def test_dashboard_session_can_be_revoked(client, login):
    login(client)
    response = client.delete("/api/session")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False
    assert client.get("/api/status").status_code == 401


def test_wrong_dashboard_key_is_rejected(client):
    response = client.post("/api/session", json={"key": "wrong-key-value"})
    assert response.status_code == 401
    assert client.cookies.get("robot_session") is None


def test_dashboard_serves_es_module_entrypoint(client):
    dashboard = client.get("/")

    assert dashboard.status_code == 200
    assert 'type="module" src="/assets/app.js"' in dashboard.text
    assert client.get("/assets/app.js").text.strip() == 'import "./js/main.js";'
    assert client.get("/assets/js/main.js").status_code == 200
