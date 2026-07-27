"""Tests for healthcheck_worker — quick ping and proxy health tracking.

Tests the internal ``_quick_ping()`` helper directly with mocked aiohttp sessions,
and the worker's DB-query-and-update logic via an in-memory SQLite DB with mocked
``_quick_ping``, letting the loop run exactly one cycle.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.db_models import Proxy

# ---------------------------------------------------------------------------
#  _quick_ping unit tests
# ---------------------------------------------------------------------------


def _make_mock_response(status: int = 200) -> MagicMock:
    """Return an async-context-manager mock suitable for ``session.get()``.

    ``ClientSession.get()`` in aiohttp is **not** a coroutine — it returns a
    ``ClientResponse`` synchronously.  The response object itself is an async
    context manager, so we set up ``__aenter__`` / ``__aexit__`` on the mock.
    """
    resp = MagicMock()
    resp.status = status
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    return resp


@pytest.mark.unit
@pytest.mark.asyncio
async def test_quick_ping_success():
    """_quick_ping returns (True, latency_ms) on a 200 response."""
    from app.healthcheck_worker import _quick_ping

    sem = asyncio.Semaphore(10)
    sess = MagicMock()
    sess.get.return_value = _make_mock_response(200)

    success, latency = await _quick_ping("http://1.2.3.4:8080", sem, sess)

    assert success is True
    assert isinstance(latency, int)
    assert latency >= 0
    sess.get.assert_called_once()
    _, kw = sess.get.call_args
    assert kw["proxy"] == "http://1.2.3.4:8080"
    assert kw["ssl"] is False
    assert kw["allow_redirects"] is False
    # url is passed positionally
    args, _ = sess.get.call_args
    assert args[0] == "http://httpbin.org/ip"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_quick_ping_non_200():
    """_quick_ping returns (False, latency_ms) on a non-200 response."""
    from app.healthcheck_worker import _quick_ping

    sem = asyncio.Semaphore(10)
    sess = MagicMock()
    sess.get.return_value = _make_mock_response(404)

    success, latency = await _quick_ping("http://1.2.3.4:8080", sem, sess)

    assert success is False
    assert isinstance(latency, int)
    assert latency >= 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_quick_ping_failure():
    """_quick_ping returns (False, None) when the HTTP call raises."""
    from app.healthcheck_worker import _quick_ping

    sem = asyncio.Semaphore(10)
    sess = MagicMock()
    sess.get.side_effect = OSError("connection refused")

    success, latency = await _quick_ping("http://1.2.3.4:8080", sem, sess)

    assert success is False
    assert latency is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_quick_ping_socks5_normalization():
    """socks5:// URLs get the scheme replaced with http:// for the proxy kwarg."""
    from app.healthcheck_worker import _quick_ping

    sem = asyncio.Semaphore(10)
    sess = MagicMock()
    sess.get.return_value = _make_mock_response(200)

    await _quick_ping("socks5://10.0.0.1:1080", sem, sess)

    _, kw = sess.get.call_args
    assert kw["proxy"] == "http://10.0.0.1:1080"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_quick_ping_socks4_normalization():
    """socks4:// URLs get the scheme replaced with http:// for the proxy kwarg."""
    from app.healthcheck_worker import _quick_ping

    sem = asyncio.Semaphore(10)
    sess = MagicMock()
    sess.get.return_value = _make_mock_response(200)

    await _quick_ping("socks4://10.0.0.2:1080", sem, sess)

    _, kw = sess.get.call_args
    assert kw["proxy"] == "http://10.0.0.2:1080"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_quick_ping_http_unchanged():
    """http:// URLs are passed through verbatim."""
    from app.healthcheck_worker import _quick_ping

    sem = asyncio.Semaphore(10)
    sess = MagicMock()
    sess.get.return_value = _make_mock_response(200)

    await _quick_ping("http://9.9.9.9:3128", sem, sess)

    _, kw = sess.get.call_args
    assert kw["proxy"] == "http://9.9.9.9:3128"


# ---------------------------------------------------------------------------
#  Worker integration tests  (in-memory SQLite + monkeypatched _quick_ping)
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.unit


async def _setup_inmemory_db():
    """Create and return a (engine, sessionmaker) for an empty in-memory DB."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    return engine, SessionLocal


async def _run_one_cycle(monkeypatch, SessionLocal) -> None:
    """Run *healthcheck_worker* for exactly one loop iteration.

    Patches:
    * ``AsyncSessionLocal`` → our test session maker
    * ``asyncio.sleep``   → raise CancelledError after the startup delay
    * ``aiohttp.TCPConnector`` / ``aiohttp.ClientTimeout`` → pass-through mocks
    * ``aiohttp.ClientSession`` → async context manager mock
    """
    from app.healthcheck_worker import healthcheck_worker

    # ---- DB ----
    monkeypatch.setattr(
        "app.healthcheck_worker.AsyncSessionLocal", SessionLocal
    )

    # ---- aiohttp setup (never actually used because _quick_ping is mocked) ----
    monkeypatch.setattr("aiohttp.TCPConnector", MagicMock)
    monkeypatch.setattr("aiohttp.ClientTimeout", MagicMock)

    async def _aenter(outer_self):
        return outer_self

    mock_cs = MagicMock()
    mock_cs.__aenter__ = _aenter
    mock_cs.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "aiohttp.ClientSession", MagicMock(return_value=mock_cs)
    )

    # ---- Make the loop stop after the startup sleep ----
    sleep_call: list[int] = [0]

    async def _sleep_once(seconds: float) -> None:
        sleep_call[0] += 1
        if sleep_call[0] >= 2:  # 1st = startup, 2nd = end-of-cycle → break
            raise asyncio.CancelledError()

    monkeypatch.setattr("app.healthcheck_worker.asyncio.sleep", _sleep_once)

    # ---- Run ----
    await healthcheck_worker()


@pytest.mark.asyncio
async def test_healthcheck_worker_marks_dead(monkeypatch):
    """A proxy with validation_failures >= MAX_FAILURES_BEFORE_DEAD is marked dead."""
    from app.healthcheck_worker import MAX_FAILURES_BEFORE_DEAD

    engine, SessionLocal = await _setup_inmemory_db()
    try:
        async with SessionLocal() as session:
            session.add(
                Proxy(
                    url="http://1.2.3.4:80",
                    protocol="http",
                    ip="1.2.3.4",
                    port=80,
                    is_working=True,
                    validation_status="validated",
                    validation_failures=MAX_FAILURES_BEFORE_DEAD - 1,
                )
            )
            await session.commit()

        mock_ping = AsyncMock(return_value=(False, None))
        monkeypatch.setattr(
            "app.healthcheck_worker._quick_ping", mock_ping
        )

        await _run_one_cycle(monkeypatch, SessionLocal)

        async with SessionLocal() as session:
            proxy = (await session.execute(select(Proxy))).scalars().one()
            assert proxy.is_working is False
            assert (
                proxy.validation_failures == MAX_FAILURES_BEFORE_DEAD
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_healthcheck_worker_updates_latency(monkeypatch):
    """A healthy ping updates latency_ms, resets failures, and sets last_validated."""
    engine, SessionLocal = await _setup_inmemory_db()
    try:
        async with SessionLocal() as session:
            session.add(
                Proxy(
                    url="http://1.2.3.4:80",
                    protocol="http",
                    ip="1.2.3.4",
                    port=80,
                    is_working=True,
                    validation_status="validated",
                    validation_failures=1,
                    latency_ms=999,
                )
            )
            await session.commit()

        mock_ping = AsyncMock(return_value=(True, 100))
        monkeypatch.setattr(
            "app.healthcheck_worker._quick_ping", mock_ping
        )

        await _run_one_cycle(monkeypatch, SessionLocal)

        async with SessionLocal() as session:
            proxy = (await session.execute(select(Proxy))).scalars().one()
            assert proxy.latency_ms == 100
            assert proxy.validation_failures == 0
            assert proxy.last_validated is not None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_healthcheck_worker_skips_recently_validated(monkeypatch):
    """A proxy checked within STALE_CUTOFF_MINUTES is not pinged."""
    engine, SessionLocal = await _setup_inmemory_db()
    try:
        recent = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        async with SessionLocal() as session:
            session.add(
                Proxy(
                    url="http://1.2.3.4:80",
                    protocol="http",
                    ip="1.2.3.4",
                    port=80,
                    is_working=True,
                    validation_status="validated",
                    validation_failures=0,
                    last_validated=recent,
                )
            )
            await session.commit()

        mock_ping = AsyncMock()
        monkeypatch.setattr(
            "app.healthcheck_worker._quick_ping", mock_ping
        )

        await _run_one_cycle(monkeypatch, SessionLocal)

        assert mock_ping.call_count == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_healthcheck_worker_skips_max_failures(monkeypatch):
    """A proxy at MAX_FAILURES_BEFORE_DEAD is excluded from the query."""
    from app.healthcheck_worker import MAX_FAILURES_BEFORE_DEAD

    engine, SessionLocal = await _setup_inmemory_db()
    try:
        async with SessionLocal() as session:
            session.add(
                Proxy(
                    url="http://1.2.3.4:80",
                    protocol="http",
                    ip="1.2.3.4",
                    port=80,
                    is_working=True,
                    validation_status="validated",
                    validation_failures=MAX_FAILURES_BEFORE_DEAD,
                )
            )
            await session.commit()

        mock_ping = AsyncMock()
        monkeypatch.setattr(
            "app.healthcheck_worker._quick_ping", mock_ping
        )

        await _run_one_cycle(monkeypatch, SessionLocal)

        assert mock_ping.call_count == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_healthcheck_worker_skips_non_validated(monkeypatch):
    """A proxy with validation_status != 'validated' is not pinged."""
    engine, SessionLocal = await _setup_inmemory_db()
    try:
        async with SessionLocal() as session:
            session.add(
                Proxy(
                    url="http://1.2.3.4:80",
                    protocol="http",
                    ip="1.2.3.4",
                    port=80,
                    is_working=True,
                    validation_status="pending",
                    validation_failures=0,
                )
            )
            await session.commit()

        mock_ping = AsyncMock()
        monkeypatch.setattr(
            "app.healthcheck_worker._quick_ping", mock_ping
        )

        await _run_one_cycle(monkeypatch, SessionLocal)

        assert mock_ping.call_count == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_healthcheck_worker_updates_multiple_proxies(monkeypatch):
    """Multiple proxies are all pinged and updated correctly."""
    engine, SessionLocal = await _setup_inmemory_db()
    try:
        async with SessionLocal() as session:
            for i in range(3):
                session.add(
                    Proxy(
                        url=f"http://1.1.1.{i}:80",
                        protocol="http",
                        ip=f"1.1.1.{i}",
                        port=80,
                        is_working=True,
                        validation_status="validated",
                        validation_failures=0,
                    )
                )
            await session.commit()

        # First proxy alive, second dead, third alive
        side_effects = [
            (True, 50),
            (False, None),
            (True, 150),
        ]
        mock_ping = AsyncMock(side_effect=side_effects)
        monkeypatch.setattr(
            "app.healthcheck_worker._quick_ping", mock_ping
        )

        await _run_one_cycle(monkeypatch, SessionLocal)

        async with SessionLocal() as session:
            proxies = (await session.execute(select(Proxy).order_by(Proxy.id))).scalars().all()
            # Proxy 0 — alive
            assert proxies[0].latency_ms == 50
            assert proxies[0].validation_failures == 0
            assert proxies[0].is_working is True
            # Proxy 1 — dead (first failure, needs 2 total)
            assert proxies[1].latency_ms is None
            assert proxies[1].validation_failures == 1
            assert proxies[1].is_working is True
            # Proxy 2 — alive
            assert proxies[2].latency_ms == 150
            assert proxies[2].validation_failures == 0
            assert proxies[2].is_working is True
    finally:
        await engine.dispose()
