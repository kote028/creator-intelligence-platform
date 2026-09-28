def test_sponsorship_lifecycle(client):
    # Setup Brand and Campaign
    brand_res = client.post(
        "/brands/",
        json={
            "company_name": "Puma",
            "email": "partnerships@puma.com"
        }
    )
    brand_id = brand_res.json()["brand_id"]

    camp_res = client.post(
        "/campaigns/",
        json={
            "brand_id": brand_id,
            "campaign_name": "Autumn Running",
            "budget": 5000.0
        }
    )
    campaign_id = camp_res.json()["campaign_id"]

    # Setup Creator
    creator_res = client.post(
        "/creators/",
        json={
            "username": "marathon_mike",
            "niche": "Running"
        }
    )
    creator_id = creator_res.json()["creator_id"]

    # Create sponsorship exceeding campaign budget should fail
    over_res = client.post(
        "/sponsorships/",
        json={
            "creator_id": creator_id,
            "campaign_id": campaign_id,
            "agreed_amount": 6000.0,
            "status": "pending"
        }
    )
    assert over_res.status_code == 400
    assert "exceeds campaign budget" in over_res.json()["detail"]

    # Create valid sponsorship
    spon_res = client.post(
        "/sponsorships/",
        json={
            "creator_id": creator_id,
            "campaign_id": campaign_id,
            "agreed_amount": 3000.0,
            "status": "pending"
        }
    )
    assert spon_res.status_code == 200
    sponsorship = spon_res.json()
    spon_id = sponsorship["sponsorship_id"]
    assert sponsorship["status"] == "pending"

    # Duplicate sponsorship should fail
    dup_res = client.post(
        "/sponsorships/",
        json={
            "creator_id": creator_id,
            "campaign_id": campaign_id,
            "agreed_amount": 2000.0,
            "status": "pending"
        }
    )
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # Test status filter
    filter_pending = client.get("/sponsorships/?status=pending")
    assert filter_pending.status_code == 200
    assert len(filter_pending.json()) >= 1

    filter_completed = client.get("/sponsorships/?status=completed")
    assert filter_completed.status_code == 200
    assert len(filter_completed.json()) == 0

    # Illegal transition: pending -> completed directly should fail
    bad_transition = client.patch(
        f"/sponsorships/{spon_id}/status",
        json={"status": "completed"}
    )
    assert bad_transition.status_code == 400
    assert "Cannot transition status" in bad_transition.json()["detail"]

    # Valid transition: pending -> accepted
    accept_res = client.patch(
        f"/sponsorships/{spon_id}/status",
        json={"status": "accepted"}
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "accepted"

    # Valid transition: accepted -> in_progress
    progress_res = client.patch(
        f"/sponsorships/{spon_id}/status",
        json={"status": "in_progress"}
    )
    assert progress_res.status_code == 200
    assert progress_res.json()["status"] == "in_progress"

    # Valid transition: in_progress -> completed
    complete_res = client.patch(
        f"/sponsorships/{spon_id}/status",
        json={"status": "completed"}
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == "completed"

    # Transition from terminal completed state should fail
    fail_reopen = client.patch(
        f"/sponsorships/{spon_id}/status",
        json={"status": "accepted"}
    )
    assert fail_reopen.status_code == 400

    # Delete sponsorship
    del_res = client.delete(f"/sponsorships/{spon_id}")
    assert del_res.status_code == 200
    assert client.get(f"/sponsorships/{spon_id}").status_code == 404
