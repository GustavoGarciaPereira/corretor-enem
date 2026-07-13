"""Tests for auth routes using TestClient."""


def test_register_page(client):
    """GET /register should return 200."""
    response = client.get("/register")
    assert response.status_code == 200


def test_register_user(client):
    """POST /register should create user and redirect to login."""
    response = client.post(
        "/register",
        data={"username": "novo", "email": "novo@email.com", "password": "senha123"},
    )
    # TestClient follows redirects, so we check the final destination
    assert response.status_code == 200
    assert "Login" in response.text or "login" in response.url.path


def test_register_duplicate(client):
    """Registering the same username twice should show error."""
    client.post("/register", data={"username": "dup", "email": "dup1@email.com", "password": "123"})
    response = client.post(
        "/register",
        data={"username": "dup", "email": "dup2@email.com", "password": "123"},
    )
    assert response.status_code == 200
    assert "já cadastrado" in response.text


def test_login_page(client):
    """GET /login should return 200."""
    response = client.get("/login")
    assert response.status_code == 200


def test_login_success(client):
    """POST /login with valid credentials should succeed and set session."""
    client.post("/register", data={"username": "user1", "email": "u1@email.com", "password": "abc"})
    response = client.post(
        "/login",
        data={"username": "user1", "password": "abc"},
    )
    # TestClient follows redirect → should land on dashboard
    assert response.status_code == 200
    assert "Dashboard" in response.text or "Minhas Redações" in response.text


def test_login_invalid(client):
    """POST /login with wrong password should stay on login page."""
    client.post("/register", data={"username": "user2", "email": "u2@email.com", "password": "abc"})
    response = client.post(
        "/login",
        data={"username": "user2", "password": "wrong"},
    )
    assert response.status_code == 200
    assert "inválidos" in response.text


def test_dashboard_requires_auth(client):
    """GET /dashboard without login should redirect to login."""
    response = client.get("/dashboard")
    # TestClient follows redirect → should land on login page
    assert response.status_code == 200
    assert "Login" in response.text or "login" in response.url.path


def test_upload_requires_auth(client):
    """GET /upload without login should redirect to login."""
    response = client.get("/upload")
    assert response.status_code == 200
    assert "Login" in response.text or "login" in response.url.path


def test_logout(auth_client):
    """GET /logout should clear session and redirect to login."""
    response = auth_client.get("/logout")
    # Follows redirect to login page
    assert response.status_code == 200
    assert "Login" in response.text or "login" in response.url.path
