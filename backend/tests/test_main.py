import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.app.main import create_app
from backend.app.services.database import Base, get_session
from backend.app.models import Session, Message, Fold, User, AuditLog
from backend.app.services.auth import _hash_password
import uuid

pytestmark = pytest.mark.asyncio

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    import asyncio
    asyncio.run(engine.dispose())


@pytest.fixture(scope="session")
def test_session_maker(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def setup_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(test_session_maker):
    async with test_session_maker() as session:
        yield session


@pytest.fixture
async def override_get_session(test_session_maker):
    async def _override():
        async with test_session_maker() as session:
            yield session
    return _override


@pytest.fixture
def client(override_get_session):
    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client


@pytest.fixture
async def test_session(db_session):
    sess = Session(id=str(uuid.uuid4()), name="Test Session")
    db_session.add(sess)
    await db_session.commit()
    await db_session.refresh(sess)
    return sess


@pytest.fixture(scope="session")
async def test_user(test_session_maker):
    async with test_session_maker() as session:
        user = User(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            password_hash=_hash_password("password123"),
            roles=["operator"],
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


class TestHealth:
    async def test_health_check(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "orbit-observatory"}


class TestCompression:
    async def test_compress_fold_unfold_cycle(self, client, test_session, db_session):
        messages = [
            Message(session_id=test_session.id, ref=f"m{i:05d}", role="user" if i % 2 == 1 else "assistant", content=f"Message {i}", token_count=10)
            for i in range(1, 15)
        ]
        for msg in messages:
            db_session.add(msg)
        await db_session.commit()

        response = await client.post("/api/compress", json={
            "session_id": test_session.id,
            "start_ref": "m00001",
            "end_ref": "m00003",
            "summary": "First three messages"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["consumed_blocks"]
        fold_id = data["consumed_blocks"][0]

        response = await client.post("/api/decompress", json={
            "session_id": test_session.id,
            "ref": fold_id
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "First three messages" in data["content"]

    async def test_compress_dry_run(self, client, test_session, db_session):
        messages = [
            Message(session_id=test_session.id, ref=f"m{i:05d}", role="user" if i % 2 == 1 else "assistant", content=f"Message {i}", token_count=10)
            for i in range(1, 15)
        ]
        for msg in messages:
            db_session.add(msg)
        await db_session.commit()

        response = await client.post("/api/compress", json={
            "session_id": test_session.id,
            "start_ref": "m00001",
            "end_ref": "m00003",
            "summary": "First three messages",
            "dry_run": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["ranges"]) == 1
        assert data["ranges"][0]["estimated_tokens_saved"] > 0

    async def test_compress_protected_zone_excluded(self, client, test_session, db_session):
        messages = [
            Message(session_id=test_session.id, ref=f"m{i:05d}", role="user", content=f"Msg {i}", token_count=10)
            for i in range(1, 12)
        ]
        for msg in messages:
            db_session.add(msg)
        await db_session.commit()

        # Try to compress only the protected range (recent-10 + last user message)
        response = await client.post("/api/compress", json={
            "session_id": test_session.id,
            "start_ref": "m00002",
            "end_ref": "m00011",
            "summary": "Protected messages"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "protected" in data["error"].lower()

    async def test_search_context(self, client, test_session, db_session):
        messages = [
            Message(session_id=test_session.id, ref="m00001", role="user", content="Hello world", token_count=10),
            Message(session_id=test_session.id, ref="m00002", role="assistant", content="Goodbye world", token_count=15),
        ]
        for msg in messages:
            db_session.add(msg)
        await db_session.commit()

        response = await client.post("/api/search", json={
            "session_id": test_session.id,
            "query": "hello",
            "limit": 5
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 1
        assert "Hello world" in data["results"][0]["content"]

    async def test_acp_status(self, client, test_session, db_session):
        messages = [
            Message(session_id=test_session.id, ref="m00001", role="user", content="Hello", token_count=10),
            Message(session_id=test_session.id, ref="m00002", role="assistant", content="Hi", token_count=15),
            Message(session_id=test_session.id, ref="m00003", role="user", content="How are you?", token_count=12),
        ]
        for msg in messages:
            db_session.add(msg)
        await db_session.commit()

        response = await client.post("/api/acp_status", json={
            "session_id": test_session.id
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["compressible_spans"]) >= 1
        assert "protected_zones" in data

    async def test_acp_cache(self, client, test_session, db_session):
        fold = Fold(
            session_id=test_session.id,
            start_ref="m00001",
            end_ref="m00002",
            summary="Test fold",
            folded_refs=["m00001", "m00002"],
            token_count=25,
        )
        db_session.add(fold)
        await db_session.commit()

        response = await client.post("/api/acp_cache", json={
            "session_id": test_session.id
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["cache_entries"]) == 1


class TestAuth:
    async def test_login_success(self, client, test_user):
        response = await client.post("/api/login", json={
            "username": "testuser",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data.get("token_type") == "bearer"

    async def test_login_invalid_credentials(self, client, test_user):
        response = await client.post("/api/login", json={
            "username": "testuser",
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    async def test_me_endpoint(self, client, test_user):
        response = await client.post("/api/login", json={
            "username": "testuser",
            "password": "password123",
        })
        token = response.json()["access_token"]
        response = await client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["roles"] == ["operator"]

    async def test_refresh_token(self, client, test_user):
        login_resp = await client.post("/api/login", json={
            "username": "testuser",
            "password": "password123",
        })
        refresh_token = login_resp.json()["refresh_token"]
        response = await client.post("/api/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_unauthorized_without_token(self, client):
        response = await client.get("/api/me")
        assert response.status_code == 401