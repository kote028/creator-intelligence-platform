def test_brand_profile_me_flow(client):
    # Register brand user
    reg = client.post(
        "/auth/register",
        json={
            "email": "branduser@nike.com",
            "password": "brandpassword123",
            "role": "brand"
        }
    )
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Getting profile before creation should return 404
    get_me = client.get("/brands/me", headers=headers)
    assert get_me.status_code == 404

    # Create brand profile via /brands/me
    create_me = client.post(
        "/brands/me",
        headers=headers,
        json={
            "company_name": "Nike Global",
            "email": "branduser@nike.com",
            "website": "https://nike.com",
            "industry": "Sportswear"
        }
    )
    assert create_me.status_code == 200
    brand_data = create_me.json()
    assert brand_data["company_name"] == "Nike Global"
    assert brand_data["user_id"] is not None

    # Getting profile now should return 200
    get_me2 = client.get("/brands/me", headers=headers)
    assert get_me2.status_code == 200
    assert get_me2.json()["company_name"] == "Nike Global"

    # Update brand profile via /brands/me
    update_me = client.put(
        "/brands/me",
        headers=headers,
        json={
            "industry": "Athletic Apparel & Footwear"
        }
    )
    assert update_me.status_code == 200
    assert update_me.json()["industry"] == "Athletic Apparel & Footwear"

    # /auth/me should reflect the brand_id
    auth_me = client.get("/auth/me", headers=headers)
    assert auth_me.status_code == 200
    assert auth_me.json()["brand_id"] == brand_data["brand_id"]


def test_campaign_crud_and_recommendations(client):
    # Create brand
    brand_res = client.post(
        "/brands/",
        json={
            "company_name": "Gymshark",
            "email": "collabs@gymshark.com",
            "industry": "Fitness"
        }
    )
    assert brand_res.status_code == 200
    brand_id = brand_res.json()["brand_id"]

    # Create campaign
    camp_res = client.post(
        "/campaigns/",
        json={
            "brand_id": brand_id,
            "campaign_name": "Summer Fitness 2026",
            "description": "Promote summer collection",
            "budget": 20000.0,
            "target_niche": "Fitness",
            "target_country": "UK",
            "target_platform": "Instagram",
            "min_followers": 10000,
            "max_followers": 100000
        }
    )
    assert camp_res.status_code == 200
    campaign = camp_res.json()
    campaign_id = campaign["campaign_id"]
    assert campaign["budget"] == 20000.0

    # Get single campaign
    get_camp = client.get(f"/campaigns/{campaign_id}")
    assert get_camp.status_code == 200
    assert get_camp.json()["campaign_name"] == "Summer Fitness 2026"

    # Update campaign
    put_camp = client.put(
        f"/campaigns/{campaign_id}",
        json={
            "budget": 25000.0,
            "status": "active"
        }
    )
    assert put_camp.status_code == 200
    assert put_camp.json()["budget"] == 25000.0

    # Create candidate creator matching campaign
    creator_res = client.post(
        "/creators/",
        json={
            "username": "london_trainer",
            "display_name": "London Trainer",
            "niche": "Fitness",
            "country": "UK"
        }
    )
    assert creator_res.status_code == 200
    creator_id = creator_res.json()["creator_id"]

    # Add Instagram account
    acc_res = client.post(
        "/social-accounts/",
        json={
            "creator_id": creator_id,
            "platform": "Instagram",
            "username": "londontrainer",
            "followers": 45000
        }
    )
    assert acc_res.status_code == 200
    account_id = acc_res.json()["account_id"]

    # Add metric snapshots
    client.post(
        "/creator-metrics/",
        json={
            "account_id": account_id,
            "followers": 40000,
            "avg_views": 15000,
            "engagement_rate": "5.50",
            "metric_date": "2026-01-01"
        }
    )
    client.post(
        "/creator-metrics/",
        json={
            "account_id": account_id,
            "followers": 45000,
            "avg_views": 20000,
            "engagement_rate": "6.20",
            "metric_date": "2026-02-01"
        }
    )

    # Test campaign recommendations
    rec_res = client.get(f"/campaigns/{campaign_id}/recommendations")
    assert rec_res.status_code == 200
    recommendations = rec_res.json()
    assert len(recommendations) >= 1
    top_rec = recommendations[0]
    assert top_rec["creator_id"] == creator_id
    assert top_rec["platform"] == "Instagram"
    assert top_rec["match_score"] > 0
    assert "Strong niche match" in top_rec["reasons"]
    assert "Target country match" in top_rec["reasons"]
    assert "Target platform match" in top_rec["reasons"]

    # Delete campaign
    del_res = client.delete(f"/campaigns/{campaign_id}")
    assert del_res.status_code == 200
    assert client.get(f"/campaigns/{campaign_id}").status_code == 404
