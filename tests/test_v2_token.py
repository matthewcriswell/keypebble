def test_v2_token_endpoint(client):
    resp = client.get("/v2/token?account=tester&scope=repository:demo/payload:pull")
    assert resp.status_code == 200
    data = resp.get_json()
    claims = data["claims"]
    assert claims["service"] == "docker-registry"
    assert claims["scope"] == "repository:demo/payload:pull"
    assert claims["sub"] == "tester"
