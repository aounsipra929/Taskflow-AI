import os

# Settings must exist before the app is imported.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ["FIRST_ADMIN_EMAIL"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    with Session() as session:
        yield session


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: (yield db_session)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(client, email="user@example.com", password="Passw0rdX"):
    client.post("/api/v1/auth/register", json={"email": email, "full_name": "Test User", "password": password})
    r = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def user_headers(client):
    return register_and_login(client)


@pytest.fixture()
def admin_headers(client, db_session):
    db_session.add(User(email="admin@example.com", full_name="Admin", hashed_password=hash_password("Admin12345"), role="admin"))
    db_session.commit()
    r = client.post("/api/v1/auth/login", data={"username": "admin@example.com", "password": "Admin12345"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
