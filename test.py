# test.py
from database import SessionLocal, init_db
from interaction import (
    create_team_with_members,
    create_pull_request_with_reviewers,
    merge_pull_request,
    get_user_review_pull_requests
)

# Инициализируем базу данных (создаем таблицы)
init_db()

db = SessionLocal()

print("=== Тест 1: Создание команды и нескольких PR ===")
team_data_1 = {
    "team_name": "payments",
    "members": [
        {"user_id": "u1", "username": "Alice", "is_active": True},
        {"user_id": "u2", "username": "Bob", "is_active": True},
        {"user_id": "u3", "username": "Charlie", "is_active": True},
        {"user_id": "u4", "username": "David", "is_active": True}
    ]
}
result_1 = create_team_with_members(db, team_data_1)
print("Результат создания команды:", result_1)

# Создаем несколько PR от разных авторов
pr_data_1 = {
    "pull_request_id": "pr-1001",
    "pull_request_name": "Add search",
    "author_id": "u1"
}
result_2 = create_pull_request_with_reviewers(db, pr_data_1)
print("Результат создания PR-1001:", result_2)

pr_data_2 = {
    "pull_request_id": "pr-1002",
    "pull_request_name": "Fix bug",
    "author_id": "u2"
}
result_3 = create_pull_request_with_reviewers(db, pr_data_2)
print("Результат создания PR-1002:", result_3)

pr_data_3 = {
    "pull_request_id": "pr-1003",
    "pull_request_name": "Refactor code",
    "author_id": "u3"
}
result_4 = create_pull_request_with_reviewers(db, pr_data_3)
print("Результат создания PR-1003:", result_4)

print("\n=== Тест 2: Получение PR для ревьювера u2 ===")
result_5 = get_user_review_pull_requests(db, "u2")
print("PR для ревьювера u2:", result_5)

print("\n=== Тест 3: Получение PR для ревьювера u3 ===")
result_6 = get_user_review_pull_requests(db, "u3")
print("PR для ревьювера u3:", result_6)

print("\n=== Тест 4: Получение PR для ревьювера u4 ===")
result_7 = get_user_review_pull_requests(db, "u4")
print("PR для ревьювера u4:", result_7)

print("\n=== Тест 5: Мерж одного PR и проверка статуса ===")
merge_data_1 = {
    "pull_request_id": "pr-1001"
}
result_8 = merge_pull_request(db, merge_data_1)
print("Результат мержа PR-1001:", result_8)

# Проверяем, что статус обновился в списке ревьюверов
result_9 = get_user_review_pull_requests(db, "u2")
print("PR для ревьювера u2 после мержа:", result_9)

print("\n=== Тест 6: Получение PR для несуществующего пользователя ===")
result_10 = get_user_review_pull_requests(db, "u999")
print("Результат для несуществующего пользователя:", result_10)

print("\n=== Тест 7: Получение PR для пользователя без назначенных ревью ===")
result_11 = get_user_review_pull_requests(db, "u1")
print("PR для автора u1 (обычно не назначается себе ревью):", result_11)

# Закрытие сессии
db.close()