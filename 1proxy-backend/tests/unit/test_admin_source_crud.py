"""Tests for admin source CRUD operations (Phase 6 — fully DB-driven)."""
import pytest
import json
import os
from unittest.mock import AsyncMock, MagicMock
from app.db_storage import db_storage
from app.db_models import ProxySource


class TestAdminSources:
    """Admin source management via db_storage admin methods."""

    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        session.add = MagicMock()
        session.add_all = MagicMock()
        return session

    # ── get_admin_sources ──

    @pytest.mark.asyncio
    async def test_get_admin_sources_empty(self, mock_session):
        """Should return empty list when no admin sources exist."""

        async def fake_execute(stmt):
            ret = MagicMock()
            ret.scalar.return_value = 0
            ret.scalars.return_value.all.return_value = []
            return ret

        mock_session.execute.side_effect = fake_execute

        sources, total = await db_storage.get_admin_sources(mock_session)
        assert sources == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_admin_sources_paginated(self, mock_session):
        """Should respect limit/offset pagination."""

        async def fake_execute(stmt):
            ret = MagicMock()
            ret.scalar.return_value = 20
            ret.scalars.return_value.all.return_value = [
                ProxySource(id=i, url=f"https://source{i}.com", type="GITHUB_RAW")
                for i in range(5)
            ]
            return ret

        mock_session.execute.side_effect = fake_execute

        sources, total = await db_storage.get_admin_sources(mock_session, limit=5, offset=0)
        assert len(sources) == 5
        assert total == 20

    # ── create_admin_source ──

    @pytest.mark.asyncio
    async def test_create_admin_source(self, mock_session):
        """Should create an admin source with correct fields."""

        async def fake_execute(stmt):
            ret = MagicMock()
            ret.scalar_one_or_none.return_value = None
            return ret

        mock_session.execute.side_effect = fake_execute

        source = await db_storage.create_admin_source(
            session=mock_session,
            url="https://new-source.com/list.txt",
            source_type="GENERIC_TEXT",
            admin_user_id=1,
            name="Test Source",
            description="A test admin source",
            enabled=True,
        )

        assert source.url == "https://new-source.com/list.txt"
        assert source.type == "GENERIC_TEXT"
        assert source.is_admin_source is True
        assert source.enabled is True
        assert source.name == "Test Source"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_admin_source_defaults(self, mock_session):
        """Should create with sensible defaults when optional fields omitted."""

        async def fake_execute(stmt):
            ret = MagicMock()
            ret.scalar_one_or_none.return_value = None
            return ret

        mock_session.execute.side_effect = fake_execute

        source = await db_storage.create_admin_source(
            session=mock_session,
            url="https://github.com/user/repo/blob/main/proxies.txt",
            source_type="GITHUB_RAW",
            admin_user_id=1,
        )

        assert source.enabled is True
        assert source.name is not None  # auto-generated from URL
        assert source.description is None

    # ── update_admin_source ──

    @pytest.mark.asyncio
    async def test_update_admin_source(self, mock_session):
        """Should update specific fields on an admin source."""

        async def fake_execute(stmt):
            ret = MagicMock()
            ret.scalar_one_or_none.return_value = ProxySource(
                id=42,
                url="https://old-url.com",
                type="GENERIC_TEXT",
                name="Old Name",
                enabled=True,
                is_admin_source=True,
            )
            return ret

        mock_session.execute.side_effect = fake_execute

        result = await db_storage.update_admin_source(
            session=mock_session,
            source_id=42,
            name="New Name",
            enabled=False,
        )

        assert result is not None
        assert result.name == "New Name"
        assert result.enabled is False
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_admin_source_not_found(self, mock_session):
        """Should return None when source doesn't exist."""

        async def fake_execute(stmt):
            ret = MagicMock()
            ret.scalar_one_or_none.return_value = None
            return ret

        mock_session.execute.side_effect = fake_execute

        result = await db_storage.update_admin_source(
            session=mock_session,
            source_id=999,
            name="Ghost",
        )

        assert result is None

    # ── delete_admin_source ──

    @pytest.mark.asyncio
    async def test_delete_admin_source(self, mock_session):
        """Should delete an admin source."""

        async def fake_execute(stmt):
            ret = MagicMock()
            ret.scalar_one_or_none.return_value = ProxySource(
                id=42, url="https://delete-me.com", type="GENERIC_TEXT"
            )
            return ret

        mock_session.execute.side_effect = fake_execute

        deleted = await db_storage.delete_admin_source(mock_session, 42)

        assert deleted is True
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_admin_source_not_found(self, mock_session):
        """Should return False when source doesn't exist."""

        async def fake_execute(stmt):
            ret = MagicMock()
            ret.scalar_one_or_none.return_value = None
            return ret

        mock_session.execute.side_effect = fake_execute

        deleted = await db_storage.delete_admin_source(mock_session, 999)

        assert deleted is False

    # ── seed_admin_sources ──

    @pytest.mark.asyncio
    async def test_seed_admin_sources_from_json(self, mock_session):
        """Should seed admin sources from the JSON file."""

        async def fake_execute(stmt):
            ret = MagicMock()
            ret.scalar.return_value = 0
            ret.scalar_one_or_none.return_value = None  # no duplicate
            return ret

        mock_session.execute.side_effect = fake_execute

        await db_storage.seed_admin_sources(mock_session, admin_user_id=1)

        assert mock_session.add.called, "session.add should have been called"
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_seed_admin_sources_skips_if_exists(self, mock_session):
        """Should skip seeding if admin sources already exist in DB."""

        async def fake_execute(stmt):
            ret = MagicMock()
            ret.scalar.return_value = 5
            ret.scalar_one_or_none.return_value = MagicMock()  # truthy = exists
            return ret

        mock_session.execute.side_effect = fake_execute

        await db_storage.seed_admin_sources(mock_session, admin_user_id=1)

        mock_session.add.assert_not_called()
        mock_session.add_all.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_admin_sources_json_file_loads(self):
        """The admin_sources.json seed file should load and contain valid data."""
        json_path = os.path.join(
            os.path.dirname(__file__), "../../app/data/admin_sources.json"
        )
        with open(json_path) as f:
            sources = json.load(f)

        assert len(sources) >= 26
        for s in sources:
            assert "url" in s
            assert "type" in s
            assert s["url"]
            assert s.get("enabled", True)
