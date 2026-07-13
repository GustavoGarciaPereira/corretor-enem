"""End-to-end integration tests (basic smoke tests)."""


def test_dashboard_page(client):
    """GET /dashboard should not crash (may redirect to login)."""
    response = client.get("/dashboard")
    assert response.status_code in (200, 302)


def test_stats_page(client):
    """GET /stats should not crash."""
    response = client.get("/stats")
    assert response.status_code in (200, 302)


def test_competences_list(client):
    """GET /competences should not crash."""
    response = client.get("/competences")
    assert response.status_code in (200, 302)
