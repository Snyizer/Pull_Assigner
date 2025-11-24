from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from schem import User, Team, TeamMember, PullRequest, PullRequestReviewer, PRStatus
from datetime import datetime

def create_team_with_members(
        db: Session,
        team_data: dict[str, any]
) -> dict[str, any]:
    """
    Создать команду с участниками (создаёт/обновляет пользователей)

    tags: [Teams]
    summary: Создать команду с участниками (создаёт/обновляет пользователей)

    Args:
        db: SQLAlchemy сессия
        team_data: {
            "team_name": "payments",
            "members": [
                {"user_id": "u1", "username": "Alice", "is_active": true},
                {"user_id": "u2", "username": "Bob", "is_active": true}
            ]
        }

    Returns:
        dict с результатом: {"success": true, "team_name": str, "members_count": int}
    """

    team_name = team_data["team_name"]
    members_data = team_data["members"]

    try:
        # 1. Проверяем, существует ли команда
        existing_team = db.query(Team).filter(Team.team_name == team_name).first()
        if existing_team:
            return {
                "success": False,
                "error": {
                    "code": "TEAM_EXISTS",
                    "message": f"Team '{team_name}' already exists"
                }
            }

        # 2. Создаём команду
        team = Team(team_name=team_name)
        db.add(team)
        db.flush()  # фиксируем team_name в БД

        # 3. Обрабатываем каждого участника
        created_members = []
        for member_data in members_data:
            user_id = member_data["user_id"]
            username = member_data["username"]
            is_active = member_data["is_active"]

            # 4. Создаём/обновляем пользователя
            user = User(
                user_id=user_id,
                username=username,
                is_active=is_active
            )
            db.merge(user)  # upsert пользователя

            # 5. Создаём связь TeamMember
            team_member = TeamMember(
                user_id=user_id,
                username=username,  # дублируем для быстрых запросов
                team_name=team_name,
                is_active=is_active
            )
            db.add(team_member)
            created_members.append({
                "user_id": user_id,
                "username": username,
                "team_name": team_name,
                "is_active": is_active
            })

        # 6. Коммитим все изменения
        db.commit()

        return {
            "success": True,
            "team": {
                "team_name": team_name,
                "members": created_members
            }
        }

    except IntegrityError as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTEGRITY_ERROR",
                "message": f"Data integrity error: {str(e)}"
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": f"Server error: {str(e)}"
            }
        }


def get_team_with_members(
        db: Session,
        team_name: str
) -> dict[str, any]:
    """
    Получить команду с участниками

    tags: [Teams]
    summary: Получить команду с участниками

    Args:
        db: SQLAlchemy сессия
        team_name: Название команды

    Returns:
        dict с результатом: команда с участниками или ошибка
    """

    try:
        # 1. Ищем команду
        team = db.query(Team).filter(Team.team_name == team_name).first()

        if not team:
            return {
                "success": False,
                "error": {
                    "code": "TEAM_NOT_FOUND",
                    "message": f"Team '{team_name}' not found"
                }
            }

        # 2. Получаем всех участников команды
        team_members = db.query(TeamMember).filter(
            TeamMember.team_name == team_name,
            TeamMember.is_active == True
        ).all()

        # 3. Формируем список участников
        members_list = []
        for member in team_members:
            members_list.append({
                "user_id": member.user_id,
                "username": member.username,
                "is_active": member.is_active
            })

        # 4. Возвращаем результат
        return {
            "success": True,
            "team": {
                "team_name": team_name,
                "members": members_list
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": f"Server error: {str(e)}"
            }
        }


def set_user_active_flag(
        db: Session,
        user_data: dict[str, any]
) -> dict[str, any]:
    """
    Установить флаг активности пользователя

    tags: [Users]
    summary: Установить флаг активности пользователя

    Args:
        db: SQLAlchemy сессия
        user_data: {
            "user_id": "u2",
            "is_active": false
        }

    Returns:
        dict с результатом: обновлённый пользователь или ошибка
    """

    user_id = user_data["user_id"]
    is_active = user_data["is_active"]

    try:
        # 1. Находим пользователя
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return {
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": f"User '{user_id}' not found"
                }
            }

        # 2. Обновляем флаг активности пользователя
        user.is_active = is_active

        # 3. Также обновляем флаг активности во всех членствах пользователя в командах
        team_memberships = db.query(TeamMember).filter(TeamMember.user_id == user_id).all()

        for membership in team_memberships:
            membership.is_active = is_active

        # 4. Получаем информацию о команде пользователя (первая активная команда)
        user_team = db.query(TeamMember).filter(
            TeamMember.user_id == user_id,
            TeamMember.is_active == True
        ).first()

        team_name = user_team.team_name if user_team else None

        # 5. Коммитим изменения
        db.commit()

        # 6. Формируем ответ
        return {
            "success": True,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "team_name": team_name,
                "is_active": user.is_active
            }
        }

    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": f"Server error: {str(e)}"
            }
        }


def create_pull_request_with_reviewers(
        db: Session,
        pr_data: dict[str, any]
) -> dict[str, any]:
    """
    Создать PR и автоматически назначить до 2 ревьюверов из команды автора

    tags: [PullRequests]
    summary: Создать PR и автоматически назначить до 2 ревьюверов из команды автора

    Args:
        db: SQLAlchemy сессия
        pr_data: {
            "pull_request_id": "pr-1001",
            "pull_request_name": "Add search",
            "author_id": "u1"
        }

    Returns:
        Dict с результатом: созданный PR с назначенными ревьюверами или ошибка
    """

    pull_request_id = pr_data["pull_request_id"]
    pull_request_name = pr_data["pull_request_name"]
    author_id = pr_data["author_id"]

    try:
        # 1. Проверяем, существует ли уже PR с таким ID
        existing_pr = db.query(PullRequest).filter(
            PullRequest.pull_request_id == pull_request_id
        ).first()

        if existing_pr:
            return {
                "success": False,
                "error": {
                    "code": "PR_EXISTS",
                    "message": f"PR with id '{pull_request_id}' already exists"
                }
            }

        # 2. Проверяем существование и активность автора
        author = db.query(User).filter(
            User.user_id == author_id,
            User.is_active == True
        ).first()

        if not author:
            return {
                "success": False,
                "error": {
                    "code": "AUTHOR_NOT_FOUND",
                    "message": f"Author '{author_id}' not found or inactive"
                }
            }

        # 3. Находим активную команду автора
        author_team_member = db.query(TeamMember).filter(
            TeamMember.user_id == author_id,
            TeamMember.is_active == True
        ).first()

        if not author_team_member:
            return {
                "success": False,
                "error": {
                    "code": "TEAM_NOT_FOUND",
                    "message": f"Author '{author_id}' is not in any active team"
                }
            }

        team_name = author_team_member.team_name

        # 4. Ищем до 2 случайных активных ревьюверов из той же команды (исключая автора)
        potential_reviewers = db.query(TeamMember).filter(
            TeamMember.team_name == team_name,
            TeamMember.user_id != author_id,
            TeamMember.is_active == True
        ).limit(2).all()

        # 5. Создаём PullRequest
        new_pr = PullRequest(
            pull_request_id=pull_request_id,
            pull_request_name=pull_request_name,
            author_id=author_id,
            status=PRStatus.OPEN
        )
        db.add(new_pr)
        db.flush()

        # 6. Назначаем ревьюверов (сколько есть доступных, от 0 до 2)
        assigned_reviewer_ids = []
        for reviewer in potential_reviewers:
            pr_reviewer = PullRequestReviewer(
                pull_request_id=pull_request_id,
                user_id=reviewer.user_id
            )
            db.add(pr_reviewer)
            assigned_reviewer_ids.append(reviewer.user_id)

        # 7. Коммитим все изменения
        db.commit()

        # 8. Формируем ответ
        return {
            "success": True,
            "pr": {
                "pull_request_id": pull_request_id,
                "pull_request_name": pull_request_name,
                "author_id": author_id,
                "status": "OPEN",
                "assigned_reviewers": assigned_reviewer_ids
            }
        }

    except IntegrityError as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "INTEGRITY_ERROR",
                "message": f"Data integrity error: {str(e)}"
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": f"Server error: {str(e)}"
            }
        }


def merge_pull_request(
        db: Session,
        pr_data: dict[str, any]
) -> dict[str, any]:
    """
    Пометить PR как MERGED (идемпотентная операция)

    tags: [PullRequests]
    summary: Пометить PR как MERGED (идемпотентная операция)

    Args:
        db: SQLAlchemy сессия
        pr_data: {
            "pull_request_id": "pr-1001"
        }

    Returns:
        Dict с результатом: обновленный PR или ошибка
    """

    pull_request_id = pr_data["pull_request_id"]

    try:
        # 1. Находим PR
        pr = db.query(PullRequest).filter(
            PullRequest.pull_request_id == pull_request_id
        ).first()

        if not pr:
            return {
                "success": False,
                "error": {
                    "code": "PR_NOT_FOUND",
                    "message": f"Pull request '{pull_request_id}' not found"
                }
            }

        # 2. Получаем список ревьюверов
        reviewers = db.query(PullRequestReviewer).filter(
            PullRequestReviewer.pull_request_id == pull_request_id
        ).all()

        reviewer_ids = [reviewer.user_id for reviewer in reviewers]

        # 3. Если PR уже в статусе MERGED, просто возвращаем данные (идемпотентность)
        if pr.status == PRStatus.MERGED:
            return {
                "success": True,
                "pr": {
                    "pull_request_id": pr.pull_request_id,
                    "pull_request_name": pr.pull_request_name,
                    "author_id": pr.author_id,
                    "status": "MERGED",
                    "assigned_reviewers": reviewer_ids,
                    "mergedAt": datetime.now().isoformat() + "Z"
                }
            }

        # 4. Обновляем статус на MERGED
        pr.status = PRStatus.MERGED

        # 5. Коммитим изменения
        db.commit()

        # 6. Формируем ответ
        return {
            "success": True,
            "pr": {
                "pull_request_id": pr.pull_request_id,
                "pull_request_name": pr.pull_request_name,
                "author_id": pr.author_id,
                "status": "MERGED",
                "assigned_reviewers": reviewer_ids,
                "mergedAt": datetime.now().isoformat() + "Z"
            }
        }

    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": f"Server error: {str(e)}"
            }
        }


def get_user_review_pull_requests(
        db: Session,
        user_id: str
) -> dict[str, any]:
    """
    Получить PR'ы, где пользователь назначен ревьювером

    tags: [Users]
    summary: Получить PR'ы, где пользователь назначен ревьювером

    Args:
        db: SQLAlchemy сессия
        user_id: ID пользователя

    Returns:
        Dict с результатом: список PR'ов пользователя или ошибка
    """

    try:
        # 1. Проверяем существование пользователя
        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            return {
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": f"User '{user_id}' not found"
                }
            }

        # 2. Находим все PR, где пользователь назначен ревьювером
        review_assignments = db.query(PullRequestReviewer).filter(
            PullRequestReviewer.user_id == user_id
        ).all()

        # 3. Получаем информацию о каждом PR
        pull_requests_list = []
        for assignment in review_assignments:
            pr = db.query(PullRequest).filter(
                PullRequest.pull_request_id == assignment.pull_request_id
            ).first()

            if pr:
                pull_requests_list.append({
                    "pull_request_id": pr.pull_request_id,
                    "pull_request_name": pr.pull_request_name,
                    "author_id": pr.author_id,
                    "status": pr.status.value  # Convert Enum to string
                })

        # 4. Формируем ответ
        return {
            "success": True,
            "user_id": user_id,
            "pull_requests": pull_requests_list
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": f"Server error: {str(e)}"
            }
        }


def reassign_pull_request_reviewer(
        db: Session,
        reassign_data: dict[str, any]
) -> dict[str, any]:
    """
    Переназначить конкретного ревьювера на другого из его команды

    tags: [PullRequests]
    summary: Переназначить конкретного ревьювера на другого из его команды

    Args:
        db: SQLAlchemy сессия
        reassign_data: {
            "pull_request_id": "pr-1001",
            "old_user_id": "u2"
        }

    Returns:
        Dict с результатом: обновленный PR и user_id нового ревьювера или ошибка
    """

    pull_request_id = reassign_data["pull_request_id"]
    old_user_id = reassign_data["old_user_id"]

    try:
        # 1. Находим PR и проверяем его статус
        pr = db.query(PullRequest).filter(
            PullRequest.pull_request_id == pull_request_id
        ).first()

        if not pr:
            return {
                "success": False,
                "error": {
                    "code": "PR_NOT_FOUND",
                    "message": f"Pull request '{pull_request_id}' not found"
                }
            }

        # 2. Проверяем, что PR не в статусе MERGED
        if pr.status == PRStatus.MERGED:
            return {
                "success": False,
                "error": {
                    "code": "PR_MERGED",
                    "message": "Cannot reassign on merged PR"
                }
            }

        # 3. Проверяем, что старый ревьювер действительно назначен на этот PR
        old_reviewer_assignment = db.query(PullRequestReviewer).filter(
            PullRequestReviewer.pull_request_id == pull_request_id,
            PullRequestReviewer.user_id == old_user_id
        ).first()

        if not old_reviewer_assignment:
            return {
                "success": False,
                "error": {
                    "code": "NOT_ASSIGNED",
                    "message": "Reviewer is not assigned to this PR"
                }
            }

        # 4. Находим команду старого ревьювера
        old_reviewer_team = db.query(TeamMember).filter(
            TeamMember.user_id == old_user_id,
            TeamMember.is_active == True
        ).first()

        if not old_reviewer_team:
            return {
                "success": False,
                "error": {
                    "code": "USER_NOT_IN_TEAM",
                    "message": f"User '{old_user_id}' is not in any active team"
                }
            }

        team_name = old_reviewer_team.team_name

        # 5. Ищем кандидата на замену из той же команды
        # Исключаем автора PR и текущих ревьюверов (включая старого)
        current_reviewers = db.query(PullRequestReviewer).filter(
            PullRequestReviewer.pull_request_id == pull_request_id
        ).all()
        current_reviewer_ids = [r.user_id for r in current_reviewers]

        # Ищем активных пользователей в команде, исключая автора и текущих ревьюверов
        candidate = db.query(TeamMember).filter(
            TeamMember.team_name == team_name,
            TeamMember.user_id != pr.author_id,
            TeamMember.user_id.not_in(current_reviewer_ids),
            TeamMember.is_active == True
        ).first()

        if not candidate:
            return {
                "success": False,
                "error": {
                    "code": "NO_CANDIDATE",
                    "message": "No active replacement candidate in team"
                }
            }

        # 6. Заменяем ревьювера
        old_reviewer_assignment.user_id = candidate.user_id

        # 7. Получаем обновленный список ревьюверов
        updated_reviewers = db.query(PullRequestReviewer).filter(
            PullRequestReviewer.pull_request_id == pull_request_id
        ).all()
        updated_reviewer_ids = [reviewer.user_id for reviewer in updated_reviewers]

        # 8. Коммитим изменения
        db.commit()

        # 9. Формируем ответ
        return {
            "success": True,
            "pr": {
                "pull_request_id": pr.pull_request_id,
                "pull_request_name": pr.pull_request_name,
                "author_id": pr.author_id,
                "status": pr.status.value,
                "assigned_reviewers": updated_reviewer_ids
            },
            "replaced_by": candidate.user_id
        }

    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": f"Server error: {str(e)}"
            }
        }