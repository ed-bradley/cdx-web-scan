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
    CDX_WEB_SCAN_LOG_FILE = environ.get("CDX_WEB_SCAN_LOG_FILE")
    APP_SERVER_OS = environ.get("APP_SERVER_OS")

    # Intake API (AWS API Gateway + Lambda)
    INTAKE_API_URL = environ.get("INTAKE_API_URL")
    INTAKE_API_TOKEN = environ.get("INTAKE_API_TOKEN")

class ProdConfig(Config):
    """Production System Configuration"""

    FLASK_ENV = "production"
    DEBUG = False
    TESTING = False
    LOG_LINES_TO_SHOW = "164"
    CDX_WEB_SCAN_DB_FOLDER = environ.get("CDX_WEB_SCAN_DB_FOLDER")
    CDX_WEB_SCAN_DB_FILE_NAME = environ.get("CDX_WEB_SCAN_DB_FILE_NAME")
    CDX_WEB_SCAN_FOLDER = environ.get("CDX_WEB_SCAN_FOLDER")


class DevConfig(Config):
    """Development System Configuration"""

    FLASK_ENV = "development"
    DEBUG = True
    TESTING = True
    CDX_WEB_SCAN_FOLDER = environ.get("CDX_WEB_SCAN_FOLDER")
    LOG_LINES_TO_SHOW = "164"
    CDX_WEB_SCAN_DB_FOLDER = environ.get("CDX_WEB_SCAN_DB_FOLDER")
    CDX_WEB_SCAN_DB_FILE_NAME = environ.get("CDX_WEB_SCAN_DB_FILE_NAME")
    CDX_WEB_SCAN_LOG_FILE = environ.get("CDX_WEB_SCAN_LOG_FILE")
    