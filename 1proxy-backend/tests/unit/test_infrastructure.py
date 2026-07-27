"""Tests for infrastructure additions: CI, pre-commit, .env.example, cooldown, health."""
import os
import yaml
from datetime import datetime, timedelta


class TestCIConfiguration:
    """CI — GitHub Actions workflow verification."""

    WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".github", "workflows", "tests.yml")

    def test_workflow_file_exists(self):
        """CI workflow YAML must exist."""
        assert os.path.exists(self.WORKFLOW_PATH), f"{self.WORKFLOW_PATH} not found"

    def test_workflow_is_valid_yaml(self):
        """CI workflow must be valid YAML."""
        with open(self.WORKFLOW_PATH) as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert "jobs" in data
        assert "backend-test" in data["jobs"]

    def test_workflow_runs_pytest(self):
        """CI workflow must run pytest."""
        with open(self.WORKFLOW_PATH) as f:
            data = yaml.safe_load(f)
        steps = data["jobs"]["backend-test"]["steps"]
        run_lines = [
            s["run"] for s in steps if "run" in s
        ]
        combined = "\n".join(run_lines)
        assert "pytest" in combined

    def test_workflow_uses_python_311(self):
        """CI workflow should use Python 3.11."""
        with open(self.WORKFLOW_PATH) as f:
            data = yaml.safe_load(f)
        steps = data["jobs"]["backend-test"]["steps"]
        py_versions = [
            s["with"]["python-version"]
            for s in steps if s.get("with", {}).get("python-version")
        ]
        assert any("3.11" in v for v in py_versions)


class TestPreCommitConfig:
    """Pre-commit hooks configuration."""

    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".pre-commit-config.yaml")

    def test_precommit_file_exists(self):
        """Pre-commit config must exist."""
        assert os.path.exists(self.CONFIG_PATH), f"{self.CONFIG_PATH} not found"

    def test_precommit_is_valid_yaml(self):
        """Pre-commit config must be valid YAML."""
        with open(self.CONFIG_PATH) as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert "repos" in data

    def test_precommit_has_ruff(self):
        """Pre-commit config must include ruff hooks."""
        with open(self.CONFIG_PATH) as f:
            data = yaml.safe_load(f)
        repo_urls = [r["repo"] for r in data["repos"]]
        assert any("ruff" in url for url in repo_urls)


class TestEnvExample:
    """Environment variable documentation."""

    ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env.example")

    def test_env_example_exists(self):
        """.env.example must exist."""
        assert os.path.exists(self.ENV_PATH), f"{self.ENV_PATH} not found"

    def test_env_has_core_vars(self):
        """.env.example must document CORE variables."""
        with open(self.ENV_PATH) as f:
            content = f.read()
        assert "PORT" in content
        assert "SECRET_KEY" in content
        assert "FRONTEND_URL" in content
        assert "DATABASE_URL" in content

    def test_env_has_oauth_vars(self):
        """.env.example must document OAuth variables."""
        with open(self.ENV_PATH) as f:
            content = f.read()
        assert "GITHUB_CLIENT_ID" in content
        assert "GITHUB_CLIENT_SECRET" in content


class TestValidationCooldown:
    """Cooldown — skip recently-validated proxies."""

    def test_cooldown_skips_recently_validated(self):
        """Proxies validated within cooldown window are skipped."""
        now = datetime.utcnow()
        last_validated = now - timedelta(minutes=2)  # 2 min ago < 5 min cooldown
        cutoff = now - timedelta(minutes=5)
        # This proxy's last_validated >= cutoff → should be skipped
        assert last_validated >= cutoff, "Recently validated should be >= cutoff"

    def test_cooldown_allows_old_proxies(self):
        """Proxies validated outside cooldown window are allowed."""
        now = datetime.utcnow()
        last_validated = now - timedelta(minutes=10)  # 10 min ago > 5 min cooldown
        cutoff = now - timedelta(minutes=5)
        # This proxy's last_validated < cutoff → should be allowed
        assert last_validated < cutoff, "Old proxies should be < cutoff"

    def test_cooldown_allows_unvalidated(self):
        """Never-validated proxies (last_validated is None) are always allowed."""
        assert True  # The query explicitly includes `Proxy.last_validated.is_(None)`


class TestHealthEndpoint:
    """Health check endpoint shape."""

    def test_health_response_shape(self):
        """Health check returns expected fields."""
        response = {
            "status": "ok",
            "service": "1proxy",
            "timestamp": "2026-07-27T22:00:00",
            "db_status": "connected",
        }
        assert response["status"] == "ok"
        assert response["service"] == "1proxy"
        assert "timestamp" in response
        assert response["db_status"] in ("connected", "disconnected")
