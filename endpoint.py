from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

# Импортируем из database.py
from database import SessionLocal, init_db
from interaction import (
    create_team_with_members,
    get_team_with_members,
    set_user_active_flag,
    create_pull_request_with_reviewers,
    merge_pull_request,
    get_user_review_pull_requests, reassign_pull_request_reviewer
)
from schem import User, Team, PullRequest, PRStatus, PullRequestReviewer

app = FastAPI()


# Инициализация базы данных при запуске приложения
@app.on_event("startup")
def on_startup():
    init_db()


# Зависимость для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Модели Pydantic
class TeamMember(BaseModel):
    user_id: str
    username: str
    is_active: bool


class TeamCreate(BaseModel):
    team_name: str
    members: List[TeamMember]


class UserActive(BaseModel):
    user_id: str
    is_active: bool


class PRCreate(BaseModel):
    pull_request_id: str
    pull_request_name: str
    author_id: str


class PRMerge(BaseModel):
    pull_request_id: str


class PRReassign(BaseModel):
    pull_request_id: str
    old_user_id: str


# Эндпоинты
@app.post("/team/add", status_code=status.HTTP_201_CREATED)
def create_team(team: TeamCreate, db: Session = Depends(get_db)):
    """Создать команду с участниками"""
    result = create_team_with_members(db, team.dict())

    if not result["success"]:
        error = result["error"]
        if error["code"] == "TEAM_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error
        )

    return result


@app.get("/team/get")
def get_team(team_name: str, db: Session = Depends(get_db)):
    """Получить команду с участниками"""
    result = get_team_with_members(db, team_name)

    if not result["success"]:
        error = result["error"]
        if error["code"] == "TEAM_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error
        )

    return result


@app.post("/users/setIsActive")
def set_user_active(user_data: UserActive, db: Session = Depends(get_db)):
    """Установить флаг активности пользователя"""
    result = set_user_active_flag(db, user_data.dict())

    if not result["success"]:
        error = result["error"]
        if error["code"] == "USER_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error
        )

    return result


@app.post("/pullRequest/create", status_code=status.HTTP_201_CREATED)
def create_pull_request(pr_data: PRCreate, db: Session = Depends(get_db)):
    """Создать PR и автоматически назначить ревьюверов"""
    result = create_pull_request_with_reviewers(db, pr_data.dict())

    if not result["success"]:
        error = result["error"]
        if error["code"] == "PR_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error
            )
        elif error["code"] in ["AUTHOR_NOT_FOUND", "TEAM_NOT_FOUND"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error
        )

    return result


@app.post("/pullRequest/merge")
def merge_pull_request_endpoint(pr_data: PRMerge, db: Session = Depends(get_db)):
    """Пометить PR как MERGED"""
    result = merge_pull_request(db, pr_data.dict())

    if not result["success"]:
        error = result["error"]
        if error["code"] == "PR_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error
        )

    return result


@app.get("/users/getReview")
def get_user_review_prs(user_id: str, db: Session = Depends(get_db)):
    """Получить PR'ы, где пользователь назначен ревьювером"""
    result = get_user_review_pull_requests(db, user_id)

    if not result["success"]:
        error = result["error"]
        if error["code"] == "USER_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error
        )

    return result



@app.post("/pullRequest/reassign")
def reassign_pull_request_reviewer_endpoint(reassign_data: PRReassign, db: Session = Depends(get_db)):
    """Переназначить конкретного ревьювера на другого из его команды"""
    result = reassign_pull_request_reviewer(db, reassign_data.dict())

    if not result["success"]:
        error = result["error"]
        if error["code"] in ["PR_NOT_FOUND", "USER_NOT_IN_TEAM"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        elif error["code"] in ["PR_MERGED", "NOT_ASSIGNED", "NO_CANDIDATE"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error
        )

    return result


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Получить статистику сервиса"""
    try:
        # Базовая статистика
        total_users = db.query(User).count()
        total_teams = db.query(Team).count()
        total_prs = db.query(PullRequest).count()
        open_prs = db.query(PullRequest).filter(PullRequest.status == PRStatus.OPEN).count()
        merged_prs = db.query(PullRequest).filter(PullRequest.status == PRStatus.MERGED).count()

        # Статистика по назначениям
        user_assignments = db.query(
            PullRequestReviewer.user_id,
            func.count(PullRequestReviewer.pull_request_id).label('assignment_count')
        ).group_by(PullRequestReviewer.user_id).all()

        assignments_list = [
            {"user_id": user_id, "assignment_count": count}
            for user_id, count in user_assignments
        ]

        return {
            "success": True,
            "stats": {
                "total_users": total_users,
                "total_teams": total_teams,
                "total_prs": total_prs,
                "open_prs": open_prs,
                "merged_prs": merged_prs,
                "user_assignments": assignments_list
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": f"Error generating stats: {str(e)}"
            }
        }