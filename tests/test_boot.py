def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    j = r.get_json()
    assert j["ok"] is True
    assert j["islands"] > 0
    assert 0.09 < j["crf"] < 0.10   # CRF(0.08, 25) ≈ 0.0937

def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"BlueGrid" in r.data