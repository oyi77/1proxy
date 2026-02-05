import pytest


@pytest.mark.unit
def test_app_import_smoke():
    # Importing the app should never crash at import time.
    from app.main import app

    assert app is not None
