"""Shared worker heartbeat registry.

Workers update their heartbeat timestamp in this dict; the admin
endpoint reads it to report liveness.
"""

from datetime import datetime, timezone

worker_heartbeats: dict[str, dict] = {}
