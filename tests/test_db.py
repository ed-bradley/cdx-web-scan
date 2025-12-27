def test_can_create_scan_row(app, db):
    with app.app_context():
        from cdx_web_scan.models import Scan, ScanSource

        scan = Scan(source=ScanSource.manual, notes="test")
        db.session.add(scan)
        db.session.commit()

        assert Scan.query.count() == 1
