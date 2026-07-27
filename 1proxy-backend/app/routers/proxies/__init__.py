from ._router import router, limiter

# Sub-modules register routes on the shared router
from . import listing, rotation, manage, health  # noqa: F401

__all__ = ["router", "limiter"]
