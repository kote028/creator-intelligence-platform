from datetime import date


def test_creator_profile_me_flow(client):
    # Register creator user
    reg = client.post(
        "/auth/register",
        json={
            "email": "sarah@example.com",
            "password": "securepassword123",
            "role": "creator"
        }
    )
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Getting profile before creation should return 404
    get_me = client.get("/creators/me", headers=headers)
    assert get_me.status_code == 404

    # Create creator profile via /creators/me
    create_me = client.post(
        "/creators/me",
        headers=headers,
        json={
            "username": "sarahcodes",
            "display_name": "Sarah Developer",
            "bio": "Tech & AI creator",
            "niche": "Technology",
            "country": "USA",
            "city": "San Francisco"
        }
    )
    assert create_me.status_code == 200
    creator_data = create_me.json()
    assert creator_data["username"] == "sarahcodes"
    assert creator_data["user_id"] is not None

    # Getting profile now should return 200
    get_me2 = client.get("/creators/me", headers=headers)
    assert get_me2.status_code == 200
    assert get_me2.json()["username"] == "sarahcodes"

    # Update creator profile via /creators/me
    update_me = client.put(
        "/creators/me",
        headers=headers,
        json={
            "bio": "Senior AI & Tech Reviewer",
            "city": "New York"
        }
    )
    assert update_me.status_code == 200
    assert update_me.json()["bio"] == "Senior AI & Tech Reviewer"
    assert update_me.json()["city"] == "New York"

    # /auth/me should reflect the creator_id
    auth_me = client.get("/auth/me", headers=headers)
    assert auth_me.status_code == 200
    assert auth_me.json()["creator_id"] == creator_data["creator_id"]


def test_creator_crud_and_discovery(client):
    # Create creator
    c1_res = client.post(
        "/creators/",
        json={
            "username": "alexfitness",
            "display_name": "Alex Fitness",
            "niche": "Fitness",
            "country": "UK",
            "city": "London"
        }
    )
    assert c1_res.status_code == 200
    c1 = c1_res.json()
    c1_id = c1["creator_id"]

    # Duplicate username should return 400
    c1_dup = client.post(
        "/creators/",
        json={
            "username": "alexfitness"
        }
    )
    assert c1_dup.status_code == 400

    # Get single creator by ID
    get_c1 = client.get(f"/creators/{c1_id}")
    assert get_c1.status_code == 200
    assert get_c1.json()["username"] == "alexfitness"

    # Update creator
    put_c1 = client.put(
        f"/creators/{c1_id}",
        json={
            "display_name": "Alex Pro Fitness"
        }
    )
    assert put_c1.status_code == 200
    assert put_c1.json()["display_name"] == "Alex Pro Fitness"

    # Add social account
    acc_res = client.post(
        "/social-accounts/",
        json={
            "creator_id": c1_id,
            "platform": "YouTube",
            "username": "alexfitness_yt",
            "followers": 50000,
            "total_posts": 100
        }
    )
    assert acc_res.status_code == 200
    acc_id = acc_res.json()["account_id"]

    # Add historical metric snapshot 1
    m1_res = client.post(
        "/creator-metrics/",
        json={
            "account_id": acc_id,
            "followers": 40000,
            "total_views": 400000,
            "avg_views": 15000,
            "total_likes": 20000,
            "total_comments": 2000,
            "engagement_rate": "4.50",
            "metric_date": "2026-01-01"
        }
    )
    assert m1_res.status_code == 200

    # Add historical metric snapshot 2 (latest)
    m2_res = client.post(
        "/creator-metrics/",
        json={
            "account_id": acc_id,
            "followers": 50000,
            "total_views": 600000,
            "avg_views": 25000,
            "total_likes": 35000,
            "total_comments": 3000,
            "engagement_rate": "6.00",
            "metric_date": "2026-02-01"
        }
    )
    assert m2_res.status_code == 200

    # Test latest account metric endpoint
    latest_metric = client.get(f"/creator-metrics/account/{acc_id}/latest")
    assert latest_metric.status_code == 200
    assert latest_metric.json()["followers"] == 50000

    # Check creator performance endpoint
    perf_res = client.get(f"/creators/{c1_id}/performance")
    assert perf_res.status_code == 200
    perf_data = perf_res.json()
    assert perf_data["followers"] == 50000
    assert perf_data["performance_score"] > 0
    assert perf_data["follower_growth"] == 25.0  # (50k - 40k) / 40k * 100

    # Check rankings endpoint
    rankings_res = client.get("/creators/rankings")
    assert rankings_res.status_code == 200
    assert len(rankings_res.json()) >= 1
    assert rankings_res.json()[0]["creator_id"] == c1_id

    # Check discover endpoint
    disc_res = client.get("/creators/discover?niche=Fitness")
    assert disc_res.status_code == 200
    assert len(disc_res.json()) >= 1
    assert disc_res.json()[0]["creator_name"] == "Alex Pro Fitness"
    assert disc_res.json()[0]["marketplace_score"] > 0

    # Delete creator
    del_res = client.delete(f"/creators/{c1_id}")
    assert del_res.status_code == 200
    get_again = client.get(f"/creators/{c1_id}")
    assert get_again.status_code == 404
