# /__init__.py

# Python Imports
import base64
import os
from datetime import datetime
import logging
import subprocess
import toml

# Third party imports
from flask import Flask, Response, jsonify, send_file, request, render_template
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from dotenv import load_dotenv

# Local imports

# Define the WSGI application object
app = Flask(__name__)

##################################
### Load Flask Run Mode
### Configuration based
### on environment
### (Production, Development)
##################################
load_dotenv("./.env", verbose=True)
app.config.from_object(os.environ["APP_MODE"])


##################################
### Logging Setup
##################################
logging.basicConfig(
    filename=app.config["CDX_WEB_SCAN_LOG_FILE"],
    level=logging.INFO,
    format="%(asctime)s %(levelname)s : %(message)s",
)

def log_message(message):
    """Helper function to prefix Log message with user name and source IP address"""
    source_ip = (
        request.headers.get("X-Forwarded-For", request.remote_addr)
        .split(",")[0]
        .strip()
    )
    return f"[IP: {source_ip}] {message}"



@app.route("/view-log")
def view_log():
    """Display the log viewer (in a new tab)."""
    app.logger.info(log_message("Processing /view-log route..."))
    return render_template("view_log.html")


@app.route("/get-log")
def get_log():
    """Get the last x lines of the application log file."""
    app.logger.debug(log_message("Processing /get-log route..."))
    log_file_path = app.config["CDX_WEB_SCAN_LOG_FILE"]
    lines_to_show = app.config["LOG_LINES_TO_SHOW"]
    if not os.path.exists(log_file_path):
        return jsonify({"error": "Log file not found"}), 404

    # use subprocess to call the system's tail command
    try:
        if app.config["APP_SERVER_OS"] == "Windows":
            result = subprocess.run(
                ["powershell", "Get-Content", log_file_path, "-Tail", lines_to_show],
                stdout=subprocess.PIPE,
            )
        else:
            result = subprocess.run(
                ["/usr/bin/tail", "-n", lines_to_show, log_file_path], stdout=subprocess.PIPE
            )
        log_content = result.stdout.decode("utf-8")
    except Exception as e:
        app.logger.error(log_message(f"Error reading log file: {e}"))
        return jsonify({"error": "Error reading log file"}), 500

    return Response(log_content, mimetype="text/plain")


##################################
### Database Setup
##################################
os.makedirs(app.config["CDX_WEB_SCAN_FOLDER"], exist_ok=True)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    app.config["CDX_WEB_SCAN_FOLDER"], app.config["CDX_WEB_SCAN_DB_FILE_NAME"]
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.logger.info(f"CDX Web Scan Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
print(f"CDX Web Scan Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

db = SQLAlchemy(app)

# Initialize schema (idempotent) so local persistence works out of the box.
with app.app_context():
    import cdx_web_scan.models  # noqa: F401

    db.create_all()


##################################
### Routing Blueprint Setup
##################################
from cdx_web_scan.error_pages.handlers import error_pages
from cdx_web_scan.web_scan.views import web_scan


app.register_blueprint(error_pages)
app.register_blueprint(web_scan)



##################################
### Context Processor
### Global template variables
##################################
def get_version():
    """Get the version of the application."""
    with open("pyproject.toml", "r") as f:
        pyproject_data = toml.load(f)
    return pyproject_data["project"]["version"]


@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""

    def get_asset_rev() -> int:
        static_dir = Path(__file__).resolve().parent / "static"
        candidates = [
            static_dir / "app.js",
            static_dir / "styles.css",
            static_dir / "service-worker.js",
            static_dir / "manifest.webmanifest",
        ]
        mtimes: list[int] = []
        for p in candidates:
            try:
                mtimes.append(int(p.stat().st_mtime))
            except OSError:
                continue
        return max(mtimes) if mtimes else int(datetime.now().timestamp())

    return {
        "version": get_version(),
        "asset_rev": get_asset_rev(),
        "current_year": datetime.now().year,
    }