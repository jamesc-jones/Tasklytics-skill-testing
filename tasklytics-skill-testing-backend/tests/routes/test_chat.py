import pytest

from app.models import Task


class TestChatEndpointSuccess:
    def test_authenticated_user_gets_structured_chat_response(
        self, client, auth_headers, mock_call_claude, db_session, test_user
    ):
        db_session.add(
            Task(
                title="Finish quarterly report",
                description="Compile Q3 numbers for leadership",
                completed=False,
                priority="high",
                user_id=test_user.id,
            )
        )
        db_session.commit()

        response = client.post(
            "/chat",
            json={"message": "What should I focus on today?"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["response"] == "Here's what to focus on."
        assert body["priority_tasks"] == ["Finish quarterly report"]
        assert body["insight"]
        mock_call_claude.assert_called_once()


class TestChatEndpointAuthentication:
    @pytest.mark.parametrize(
        "headers, expected_status",
        [
            pytest.param({}, 401, id="missing-credentials"),
            pytest.param(
                {"Authorization": "Bearer not-a-real-token"},
                401,
                id="invalid-token",
            ),
        ],
    )
    def test_rejects_request_without_valid_authentication(
        self, client, mock_call_claude, headers, expected_status
    ):
        response = client.post("/chat", json={"message": "hi"}, headers=headers)

        assert response.status_code == expected_status
        mock_call_claude.assert_not_called()


class TestChatEndpointPayloadValidation:
    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({}, id="missing-message-field"),
            pytest.param({"message": 12345}, id="wrong-type-for-message"),
        ],
    )
    def test_rejects_malformed_request_body(
        self, client, auth_headers, mock_call_claude, payload
    ):
        response = client.post("/chat", json=payload, headers=auth_headers)

        assert response.status_code == 422
        mock_call_claude.assert_not_called()
