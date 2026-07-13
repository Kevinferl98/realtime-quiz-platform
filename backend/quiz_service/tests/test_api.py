import pytest
from app.exception import DatabaseError, QuizNotFoundError, QuizPermissionError

def test_list_public_quizzes(client, mock_service):
    mock_service.list_public_quizzes.return_value = ([{"quizId": "1", "title": "Quiz 1"}], 1)

    response = client.get("/quizzes/public")

    assert response.status_code == 200
    assert response.json() == {"page": 1, "pages": 1, "total": 1, "quizzes": [{"quizId": "1", "title": "Quiz 1"}]}
    mock_service.list_public_quizzes.assert_called_once()

def test_list_public_quizzes_error_500(client, mock_service):
    mock_service.list_public_quizzes.side_effect = DatabaseError()
    
    response = client.get("/quizzes/public")
    
    assert response.status_code == 500
    assert response.json()["detail"] == "A database error occurred."

def test_list_my_quizzes_success(client, mock_service):
    mock_service.list_personal_quizzes.return_value = [{"quizId": "2", "title": "My Quiz"}]

    response = client.get("/quizzes/mine")

    assert response.status_code == 200
    mock_service.list_personal_quizzes.assert_called_once_with("user_123")

def test_list_my_quizzes_db_error(client, mock_service):
    mock_service.list_personal_quizzes.side_effect = DatabaseError()

    response = client.get("/quizzes/mine")

    assert response.status_code == 500
    assert response.json()["detail"] == "A database error occurred."

def test_get_quiz_by_id_success(client, mock_service):
    mock_service.get_quiz_by_id.return_value = {
        "quizId": "abc-123",
        "title": "Test Quiz",
        "owner_id": "user_123",
        "questions": []
    }

    response = client.get("/quizzes/abc-123")

    assert response.status_code == 200
    assert response.json()["quizId"] == "abc-123"

def test_get_quiz_by_id_not_found(client, mock_service):
    mock_service.get_quiz_by_id.side_effect = QuizNotFoundError()
    
    response = client.get("/quizzes/missing")

    assert response.status_code == 404

def test_create_quiz_success(client, mock_service):
    mock_service.create_quiz.return_value = "new-uuid"
    quiz_data = {
        "title": "New Quiz",
        "questions": [{"id": "q1", "question_text": "Text", "options": ["A", "B"], "correct_option": "A"}]
    }

    response = client.post("/quizzes/", json=quiz_data)

    assert response.status_code == 201
    assert response.json()["quizId"] == "new-uuid"
    args, kwargs = mock_service.create_quiz.call_args
    assert kwargs["owner_id"] == "user_123"
    assert kwargs["quiz_data"].title == "New Quiz"

def test_create_quiz_db_error(client, mock_service):
    mock_service.create_quiz.side_effect = DatabaseError()

    response = client.post(
        "/quizzes/",
        json={"title": "Test", "questions": []},
        headers={"Authorization": "Bearer valid_token"}
    )

    assert response.status_code == 500

def test_delete_quiz_success(client, mock_service):
    mock_service.get_quiz_by_id.return_value = {
        "quizId": "abc-123",
        "title": "Test Quiz",
        "owner_id": "user_123",
        "questions": []
    }
    response = client.delete("/quizzes/abc-123")

    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.parametrize("exception, expected_status", [
    (QuizNotFoundError(), 404),
    (QuizPermissionError(), 403),
    (DatabaseError(), 500),
])
def test_delete_quiz_scenarios(client, mock_service, exception, expected_status):
    mock_service.delete_quiz.side_effect = exception

    response = client.delete("/quizzes/123")

    assert response.status_code == expected_status

def test_check_answer_correct(client, mock_service):
    mock_service.check_answer.return_value = True
    payload = {"question_id": "q1", "answer": "A"}

    response = client.post("/quizzes/123/answer", json=payload)

    assert response.status_code == 200
    assert response.json()["correct"] is True
    mock_service.check_answer.assert_called_once_with("123", "q1", "A")