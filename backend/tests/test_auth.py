from app.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hashing():
    password = "supersecretpassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_token_encoding_decoding():
    data = {"sub": "42", "role": "creator"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"
    assert decoded["role"] == "creator"


def test_register_and_login_flow(client):
    # Register creator
    reg_response = client.post(
        "/auth/register",
        json={
            "email": "creator@example.com",
            "password": "strongpassword123",
            "role": "creator"
        }
    )
    assert reg_response.status_code == 200
    reg_data = reg_response.json()
    assert "access_token" in reg_data
    assert reg_data["role"] == "creator"

    # Duplicate registration should fail
    dup_response = client.post(
        "/auth/register",
        json={
            "email": "creator@example.com",
            "password": "strongpassword123",
            "role": "creator"
        }
    )
    assert dup_response.status_code == 400
    assert "already registered" in dup_response.json()["detail"]

    # Invalid role should fail
    role_response = client.post(
        "/auth/register",
        json={
            "email": "invalid@example.com",
            "password": "strongpassword123",
            "role": "admin"
        }
    )
    assert role_response.status_code == 400

    # Short password should fail
    short_pw = client.post(
        "/auth/register",
        json={
            "email": "short@example.com",
            "password": "123",
            "role": "creator"
        }
    )
    assert short_pw.status_code == 400

    # Login successfully
    login_response = client.post(
        "/auth/login",
        json={
            "email": "creator@example.com",
            "password": "strongpassword123"
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Authenticated /auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "creator@example.com"
    assert me_data["role"] == "creator"

    # Role guard test: creator access
    creator_only = client.get("/auth/creator-only", headers=headers)
    assert creator_only.status_code == 200

    # Role guard test: brand access should be forbidden for creator
    brand_only = client.get("/auth/brand-only", headers=headers)
    assert brand_only.status_code == 403
