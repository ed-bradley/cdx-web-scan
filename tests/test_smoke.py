def test_index_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"


def test_submit_invalid_barcode_returns_200(client):
    resp = client.post("/submit", data={"barcode": "not-a-barcode", "source": "manual"})
    assert resp.status_code == 200
