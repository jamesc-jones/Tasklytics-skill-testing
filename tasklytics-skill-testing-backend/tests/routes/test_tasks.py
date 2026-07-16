import pytest

from app.auth.auth_utils import hash_password, create_access_token
from app.models import User


@pytest.fixture()
def other_user(db_session):
    """A second seeded user, distinct from `test_user`, for cross-user isolation checks."""
    user = User(
        email="other-user@example.com",
        hashed_password=hash_password("OtherPassword123!"),
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def other_auth_headers(other_user):
    token = create_access_token({
        "sub": str(other_user.id), "email": other_user.email, "role": other_user.role,
    })
    return {"Authorization": f"Bearer {token}"}


class TestTaskCreateAndList:
    def test_create_task_then_appears_in_list(self, client, auth_headers):
        create_resp = client.post(
            "/tasks/",
            json={"title": "Write tests", "description": "Cover the tasks routes", "priority": "high"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 200
        assert create_resp.json()["success"] is True

        list_resp = client.get("/tasks/", headers=auth_headers)
        assert list_resp.status_code == 200
        titles = [t["title"] for t in list_resp.json()["data"]]
        assert "Write tests" in titles

    def test_list_requires_authentication(self, client):
        resp = client.get("/tasks/")
        assert resp.status_code in (401, 403)


class TestTaskUpdateAndDelete:
    def test_update_task(self, client, auth_headers):
        created = client.post(
            "/tasks/",
            json={"title": "Original", "description": "desc", "priority": "low"},
            headers=auth_headers,
        ).json()["data"]

        update_resp = client.put(
            f"/tasks/{created['id']}",
            json={"title": "Updated", "description": "desc", "completed": True},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["title"] == "Updated"
        assert update_resp.json()["data"]["completed"] is True

    def test_delete_task(self, client, auth_headers):
        created = client.post(
            "/tasks/",
            json={"title": "Temporary", "description": "desc", "priority": "low"},
            headers=auth_headers,
        ).json()["data"]

        delete_resp = client.delete(f"/tasks/{created['id']}", headers=auth_headers)
        assert delete_resp.status_code == 200

        list_resp = client.get("/tasks/", headers=auth_headers)
        ids = [t["id"] for t in list_resp.json()["data"]]
        assert created["id"] not in ids

    def test_update_nonexistent_task_returns_404(self, client, auth_headers):
        resp = client.put(
            "/tasks/999999",
            json={"title": "x", "description": "x", "completed": False},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestCrossUserIsolation:
    """Validates the user_id filtering CLAUDE.md documents as enforced throughout tasks.py."""

    def test_user_cannot_see_another_users_tasks(self, client, auth_headers, other_auth_headers):
        client.post(
            "/tasks/",
            json={"title": "User A's private task", "description": "d", "priority": "high"},
            headers=auth_headers,
        )

        other_list_resp = client.get("/tasks/", headers=other_auth_headers)
        titles = [t["title"] for t in other_list_resp.json()["data"]]
        assert "User A's private task" not in titles

    def test_user_cannot_update_another_users_task(self, client, auth_headers, other_auth_headers):
        created = client.post(
            "/tasks/",
            json={"title": "User A's task", "description": "d", "priority": "high"},
            headers=auth_headers,
        ).json()["data"]

        resp = client.put(
            f"/tasks/{created['id']}",
            json={"title": "Hijacked", "description": "d", "completed": True},
            headers=other_auth_headers,
        )
        assert resp.status_code == 404

    def test_user_cannot_delete_another_users_task(self, client, auth_headers, other_auth_headers):
        created = client.post(
            "/tasks/",
            json={"title": "User A's task", "description": "d", "priority": "high"},
            headers=auth_headers,
        ).json()["data"]

        resp = client.delete(f"/tasks/{created['id']}", headers=other_auth_headers)
        assert resp.status_code == 404

        still_there = client.get("/tasks/", headers=auth_headers)
        ids = [t["id"] for t in still_there.json()["data"]]
        assert created["id"] in ids
