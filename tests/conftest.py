import os
import sys
from pathlib import Path

import pytest


# Ensure the project root (repo folder) is importable when running pytest under uv.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _clear_import_cache(prefix: str) -> None:
    for name in list(sys.modules.keys()):
        if name == prefix or name.startswith(prefix + "."):
            del sys.modules[name]


def _clear_module(name: str) -> None:
    if name in sys.modules:
        del sys.modules[name]


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create a Flask app configured to use a temp folder for DB/logs.

    The application is defined as a global in cdx_web_scan/__init__.py and reads
    configuration from environment variables at import time.
    """

    data_dir = tmp_path_factory.mktemp("cdx_web_scan_data")

    os.environ["APP_MODE"] = "config.DevConfig"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["APP_SERVER_OS"] = "Linux"

    # Force temp persistence so tests never touch the developer's real data.
    os.environ["CDX_WEB_SCAN_FOLDER"] = str(data_dir)
    os.environ["CDX_WEB_SCAN_DB_FILE_NAME"] = "test.sqlite"
    os.environ["CDX_WEB_SCAN_LOG_FILE"] = str(Path(data_dir) / "test.log")

    _clear_import_cache("cdx_web_scan")
    # APP_MODE points at the top-level module "config", so ensure it reloads with our env.
    _clear_module("config")
    _clear_module("app")

    import cdx_web_scan  # noqa: E402

    return cdx_web_scan.app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    import cdx_web_scan  # noqa: E402

    with app.app_context():
        yield cdx_web_scan.db
        cdx_web_scan.db.session.remove()
