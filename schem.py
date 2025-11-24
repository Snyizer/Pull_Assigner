from sqlalchemy import create_engine, Column, String, Boolean, ForeignKey, Enum
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

# Создаем базовый класс для моделей
Base = declarative_base()


# Enum для статусов Pull Request
class PRStatus(enum.Enum):
    OPEN = "OPEN"
    MERGED = "MERGED"


class User(Base):
    __tablename__ = 'user'

    user_id = Column(String, primary_key=True)
    username = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Связи
    team_memberships = relationship("TeamMember", back_populates="user")
    authored_pull_requests = relationship("PullRequest", back_populates="author", foreign_keys="PullRequest.author_id")
    assigned_review_requests = relationship("PullRequestReviewer", back_populates="reviewer")


class Team(Base):
    __tablename__ = 'team'

    team_name = Column(String, primary_key=True)
    members = relationship("TeamMember", back_populates="team")


class TeamMember(Base):
    __tablename__ = 'teammember'

    user_id = Column(String, ForeignKey('user.user_id'), primary_key=True)
    team_name = Column(String, ForeignKey('team.team_name'), primary_key=True)
    username = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    user = relationship("User", back_populates="team_memberships")
    team = relationship("Team", back_populates="members")


class PullRequest(Base):
    __tablename__ = 'pullrequest'

    pull_request_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pull_request_name = Column(String, nullable=False)
    author_id = Column(String, ForeignKey('user.user_id'), nullable=False)
    status = Column(Enum(PRStatus), nullable=False, default=PRStatus.OPEN)

    # Связи
    author = relationship("User", back_populates="authored_pull_requests", foreign_keys=[author_id])
    reviewers = relationship("PullRequestReviewer", back_populates="pull_request")


class PullRequestShort(Base):
    __tablename__ = 'pullrequestshort'

    pull_request_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pull_request_name = Column(String, nullable=False)
    author_id = Column(String, ForeignKey('user.user_id'), nullable=False)
    status = Column(Enum(PRStatus), nullable=False, default=PRStatus.OPEN)

    # Связь с автором
    author = relationship("User", foreign_keys=[author_id])


class PullRequestReviewer(Base):
    __tablename__ = 'pullrequestreviewer'

    pull_request_id = Column(String, ForeignKey('pullrequest.pull_request_id'), primary_key=True)
    user_id = Column(String, ForeignKey('user.user_id'), primary_key=True)

    # Связи
    pull_request = relationship("PullRequest", back_populates="reviewers")
    reviewer = relationship("User", back_populates="assigned_review_requests")

