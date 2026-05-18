def test_saas_control_plane_tracks_org_plan_quota_task_alert_scope_and_audit(client):
    user = client.post("/api/team/users", json={"displayName": "Owner", "role": "owner"}).json()
    org = client.post(
        "/api/saas/organizations",
        json={"name": "Acme Intelligence", "slug": "acme", "actorUserId": user["id"]},
    ).json()
    membership = client.post(
        "/api/saas/memberships",
        json={
            "organizationId": org["id"],
            "userId": user["id"],
            "role": "owner",
            "permissionsJson": ["sources:write", "briefs:review"],
            "actorUserId": user["id"],
        },
    )
    plan = client.post(
        "/api/saas/plans",
        json={
            "name": "Pro",
            "code": "pro",
            "priceCents": 9900,
            "quotaJson": {"sources": 100, "aiRuns": 10000},
            "actorUserId": user["id"],
        },
    ).json()
    subscription = client.post(
        "/api/saas/subscriptions",
        json={"organizationId": org["id"], "planId": plan["id"], "actorUserId": user["id"]},
    )
    quota = client.post(
        "/api/saas/quota-usage",
        json={"organizationId": org["id"], "metric": "aiRuns", "used": 120, "limit": 100, "actorUserId": user["id"]},
    )
    task = client.post(
        "/api/saas/tasks",
        json={
            "organizationId": org["id"],
            "taskType": "refresh_sources",
            "priority": 5,
            "payloadJson": {"sourceIds": []},
            "actorUserId": user["id"],
        },
    ).json()
    updated_task = client.patch(
        f"/api/saas/tasks/{task['id']}",
        json={"status": "running", "attempts": 1, "actorUserId": user["id"]},
    )
    alert = client.post(
        "/api/saas/alerts",
        json={"organizationId": org["id"], "name": "AI quota", "metric": "aiRuns", "threshold": 90, "actorUserId": user["id"]},
    )
    scope = client.post(
        "/api/saas/data-scopes",
        json={
            "organizationId": org["id"],
            "entityType": "Source",
            "entityId": "source-1",
            "accessLevel": "owned",
            "actorUserId": user["id"],
        },
    )
    summary = client.get("/api/saas/summary")

    assert membership.status_code == 201
    assert subscription.status_code == 201
    assert quota.status_code == 201
    assert quota.json()["overLimit"] is True
    assert updated_task.status_code == 200
    assert updated_task.json()["status"] == "running"
    assert alert.status_code == 201
    assert scope.status_code == 201
    assert summary.status_code == 200
    payload = summary.json()
    assert len(payload["organizations"]) == 1
    assert len(payload["plans"]) == 1
    assert len(payload["quotaUsage"]) == 1
    assert len(payload["tasks"]) == 1
    actions = {item["action"] for item in payload["auditLogs"]}
    assert {
        "organization.created",
        "organization_membership.created",
        "subscription_plan.created",
        "subscription.created",
        "quota_usage.recorded",
        "task.queued",
        "task.updated",
        "alert.created",
        "tenant_scope.created",
    }.issubset(actions)


def test_saas_control_plane_rejects_missing_organization(client):
    response = client.post(
        "/api/saas/quota-usage",
        json={"organizationId": "missing", "metric": "sources", "used": 1, "limit": 1},
    )

    assert response.status_code == 404
