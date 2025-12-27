# config.py
"""CDX Web Scan - Flask Application configuration."""

# Python imports
from os import environ, path

# Third-party imports
from dotenv import load_dotenv

# Local imports

# Load environment variables from .env file
basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, ".env"))


class Config:
    """Base config."""

    SECRET_KEY = environ.get("SECRET_KEY")

    # Default persistence location for local dev.
    # Docker sets CDX_WEB_SCAN_FOLDER=/data explicitly, so these defaults won't interfere.
    CDX_WEB_SCAN_FOLDER = (
        environ.get("CDX_WEB_SCAN_FOLDER")
        or environ.get("CDX_WEB_SCAN_HOST_DATA_DIR")
        or path.join(basedir, "cdx_data")
    )
    CDX_WEB_SCAN_DB_FOLDER = environ.get("CDX_WEB_SCAN_DB_FOLDER") or CDX_WEB_SCAN_FOLDER
    CDX_WEB_SCAN_DB_FILE_NAME = environ.get("CDX_WEB_SCAN_DB_FILE_NAME") or "cdx_web_scan.sqlite"
    CDX_WEB_SCAN_LOG_FILE = (
        environ.get("CDX_WEB_SCAN_LOG_FILE")
        or path.join(CDX_WEB_SCAN_FOLDER, "cdx_web_scan.log")
    )

    APP_SERVER_OS = environ.get("APP_SERVER_OS") or "Linux"

    # Intake API (AWS API Gateway + Lambda)
    INTAKE_API_URL = environ.get("INTAKE_API_URL")
    INTAKE_API_TOKEN = environ.get("INTAKE_API_TOKEN")

class ProdConfig(Config):
    """Production System Configuration"""

    FLASK_ENV = "production"
    DEBUG = False
    TESTING = False
    LOG_LINES_TO_SHOW = "164"
    


class DevConfig(Config):
    """Development System Configuration"""

    FLASK_ENV = "development"
    DEBUG = True
    TESTING = True
    LOG_LINES_TO_SHOW = "164"
    