from keypebble.core.token import decode_token, issue_token


def test_decode_token_roundtrip():
    config = {"hs256_secret": "secret", "issuer": "test", "audience": "keypebble-test"}
    claims = {"sub": "user1", "scope": "repo:demo/pull"}

    token = issue_token(config, claims)
    decoded = decode_token(config, token)

    # Same keys and values should be recovered
    for k, v in claims.items():
        assert decoded[k] == v

    # Issuer should also appear
    assert decoded["iss"] == "test"
