# /app.py

from cdx_web_scan import app, db
from cdx_web_scan.models import Scan, ScanSource, IntakeStatus

@app.shell_context_processor
def make_shell_context():
    """Create a shell context for the application - 
    for working with the CDX Web Scan database in the Flask shell"""
    return {'db': db, 'Scan': Scan, 'ScanSource': ScanSource, 'IntakeStatus': IntakeStatus}