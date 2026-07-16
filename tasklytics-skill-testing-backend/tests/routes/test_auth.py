from app.auth.auth_utils import create_access_token, create_refresh_token


class TestRegister:
    def test_register_creates_user(self, client):
        resp = client.post("/auth/register", json={
            "email": "newuser@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["user"]["email"] == "newuser@example.com"

    def test_register_rejects_duplicate_email(self, client, test_user):
        resp = client.post("/auth/register", json={
            "email": test_user.email,
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
        })
        assert resp.status_code == 400

    def test_register_rejects_mismatched_passwords(self, client):
        resp = client.post("/auth/register", json={
            "email": "mismatch@example.com",
            "password": "TestPassword123!",
            "confirm_password": "DifferentPassword!",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_returns_access_and_refresh_tokens(self, client, test_user):
        resp = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_login_rejects_wrong_password(self, client, test_user):
        resp = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401


class TestRefreshTokenFlow:
    def test_refresh_token_issues_new_working_access_token(self, client, test_user):
        login_resp = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!",
        })
        refresh_token = login_resp.json()["refresh_token"]

        refresh_resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_resp.status_code == 200
        new_access_token = refresh_resp.json()["access_token"]

        protected_resp = client.get(
            "/tasks/", headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert protected_resp.status_code == 200

    def test_access_token_rejected_at_refresh_endpoint(self, client, test_user):
        access_token = create_access_token({
            "sub": str(test_user.id), "email": test_user.email, "role": test_user.role
        })
        resp = client.post("/auth/refresh", json={"refresh_token": access_token})
        assert resp.status_code == 401

    def test_refresh_token_rejected_at_protected_route(self, client, test_user):
        refresh_token = create_refresh_token({
            "sub": str(test_user.id), "email": test_user.email, "role": test_user.role
        })
        resp = client.get(
            "/tasks/", headers={"Authorization": f"Bearer {refresh_token}"}
        )
        assert resp.status_code == 401

    def test_malformed_refresh_token_rejected(self, client):
        resp = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
        assert resp.status_code == 401
