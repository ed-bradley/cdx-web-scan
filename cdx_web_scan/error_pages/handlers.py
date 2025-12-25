# /cdx_web_scan/error_pages/handlers.py

# Third-party imports
from flask import Blueprint, render_template, request


# Local imports
from cdx_web_scan import app

# blueprint router configuration
error_pages = Blueprint("error_pages", __name__)

def log_message(message):
    """Helper function to prefix Log messages with user name and source IP address"""
    source_ip = (
        request.headers.get("X-Forwarded-For", request.remote_addr)
        .split(",")[0]
        .strip()
    )
    return f"[IP: {source_ip}] {message}"

@error_pages.app_errorhandler(404)
def error_404(error):
    """Error 404 page handler"""
    incoming_url = request.path
    app.logger.error(log_message(f"404 Error: {error}, URL: {incoming_url}"))
    return render_template("error_pages/404.html"), 404


@error_pages.app_errorhandler(500)
def error_500(error):
    """Error 500 page handler"""
    app.logger.error(log_message(error))
    return render_template("error_pages/500.html"), 500