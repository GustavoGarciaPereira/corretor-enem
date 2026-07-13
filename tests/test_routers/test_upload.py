"""Tests for upload and competence routes (basic smoke tests)."""


def test_upload_page_redirects_without_auth(client):
    """GET /upload without login should not crash."""
    response = client.get("/upload")
    assert response.status_code in (200, 302)
    assert "Login" in response.text or "login" in response.url.path


def test_competence_levels_endpoint(client):
    """GET /competences/{id}/levels should return JSON."""
    response = client.get("/competences/1/levels")
    # With our test setup, tables are created on-the-fly
    assert response.status_code in (200, 302, 404)
    if response.status_code == 200:
        data = response.json()
        assert "levels" in data


def test_upload_file_invalid_extension(client):
    """POST /upload/file with .txt should not crash."""
    response = client.post(
        "/upload/file",
        files={"file": ("teste.txt", b"conteudo", "text/plain")},
        data={"template_id": 1},
    )
    assert response.status_code in (200, 302)
