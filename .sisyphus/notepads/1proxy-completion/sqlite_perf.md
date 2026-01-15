# SQLite Performance Best Practices (1proxy)

## Concurrency & Persistence
- **WAL Mode**: Ensure SQLite is running in Write-Ahead Logging (WAL) mode to allow concurrent readers and writers.
- **Async Drivers**: Always use `aiosqlite` (via SQLAlchemy AsyncSession) to avoid blocking the FastAPI event loop.

## Indexing Strategy
- **user_id**: Critical for filtering user-specific notifications.
- **created_at**: Critical for ordering and cleanup tasks.
- **read**: Indexed to speed up "unread only" filtering.

## Write Performance
- **Bulk Inserts**: For system-wide alerts, use `db_storage.add_proxies` style bulk inserts if possible.
- **Cleanup**: Notifications should have a retention policy (e.g., delete notifications older than 30 days) to keep indices small.

## Session Management
- Always use `async with get_db() as db:` to ensure connections are returned to the pool.
