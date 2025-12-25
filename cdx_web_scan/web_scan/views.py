# cdx_web_scan/web_scan/views.py
# Python Imports
import os
import time

# Third-party imports
from flask import render_template, Blueprint, request
from sqlalchemy import desc, func

# Local imports
from cdx_web_scan import app
from cdx_web_scan.models import Scan, ScanSource, IntakeStatus

# blueprint router configuration
web_scan = Blueprint("web_scan", __name__)


@web_scan.route("/", methods=["GET"])
def index():
    """Route to display the home page of the application"""
    
    # pass the data to the template and render the page
    return render_template("index.html")