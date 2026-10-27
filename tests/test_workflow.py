from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.db import get_session

@pytest.fixture()
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_full_workflow_lifecycle(client, org_id):
    # 1. Create a review with title and creator
    payload = {
        "text": "The tool is revolutionary and used by over 5 million customers.",
        "title": "Q4 Enterprise Campaign",
        "channel": "LinkedIn post",
        "creator_name": "Maya (Content Creator)",
        "use_ai": False,
    }
    res = client.post(f"/orgs/{org_id}/review/text", json=payload)
    assert res.status_code == 200
    data = res.json()
    review_id = data["review_id"]
    assert review_id is not None
    assert data["status"] == "draft"

    # 2. Verify list reviews returns this review
    r_list = client.get(f"/orgs/{org_id}/reviews").json()
    assert len(r_list) >= 1
    item = next(r for r in r_list if r["id"] == review_id)
    assert item["title"] == "Q4 Enterprise Campaign"
    assert item["status"] == "draft"
    assert item["open_count"] >= 1

    # 3. Add comment to review
    c_res = client.post(
        f"/reviews/{review_id}/comments",
        json={
            "user_name": "Jordan (Brand Manager)",
            "user_role": "manager",
            "message": "Please fix the outdated customer number before submitting for sign-off.",
        },
    )
    assert c_res.status_code == 200
    assert c_res.json()["user_name"] == "Jordan (Brand Manager)"

    # 4. Advance workflow: submit for review
    wf_res = client.post(
        f"/reviews/{review_id}/workflow",
        json={
            "action": "submit_for_review",
            "actor_name": "Maya (Content Creator)",
            "actor_role": "creator",
            "notes": "Addressed initial feedback, ready for manager sign-off.",
        },
    )
    assert wf_res.status_code == 200
    assert wf_res.json()["status"] == "in_review"

    # 5. Manager requests changes
    wf_res2 = client.post(
        f"/reviews/{review_id}/workflow",
        json={
            "action": "request_changes",
            "actor_name": "Jordan (Brand Manager)",
            "actor_role": "manager",
            "notes": "Change 'the tool' to FlowDesk and update count to 3 million.",
        },
    )
    assert wf_res2.status_code == 200
    assert wf_res2.json()["status"] == "changes_requested"

    # 6. Creator revises the draft
    rev_res = client.post(
        f"/reviews/{review_id}/revisions",
        json={
            "content": "FlowDesk is used by more than 3 million teams.",
            "change_summary": "Replaced 'the tool' with FlowDesk and updated customer metric to 3M teams",
            "actor_name": "Maya (Content Creator)",
        },
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["version"] == 2
    assert rev_res.json()["findings_count"] == 0  # No violations left!

    # 7. Manager approves
    wf_res3 = client.post(
        f"/reviews/{review_id}/workflow",
        json={
            "action": "approve",
            "actor_name": "Jordan (Brand Manager)",
            "actor_role": "manager",
            "notes": "Approved for publication.",
        },
    )
    assert wf_res3.status_code == 200
    assert wf_res3.json()["status"] == "approved"

    # 8. Check full review details
    full_r = client.get(f"/reviews/{review_id}").json()
    assert full_r["status"] == "approved"
    assert len(full_r["revisions"]) == 2
    assert len(full_r["comments"]) == 1
    assert len(full_r["audit_logs"]) >= 4

    # 9. Check governance summary insights
    summary = client.get(f"/orgs/{org_id}/insights/summary").json()
    assert summary["total_reviews"] >= 1
    assert summary["approved_reviews"] >= 1
    assert summary["compliance_score"] >= 50

    # 10. Check demo presets
    presets = client.get(f"/orgs/{org_id}/demo-presets").json()
    assert len(presets) == 4
