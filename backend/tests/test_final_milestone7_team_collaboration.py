from datetime import datetime, timezone

from app.db.models import BriefExport, EventCluster, Source


def test_team_collaboration_flow_records_annotations_reviews_and_audit(client, db_session):
    analyst = client.post(
        "/api/team/users",
        json={"displayName": "Analyst", "email": "analyst@example.com", "role": "analyst"},
    ).json()
    reviewer = client.post(
        "/api/team/users",
        json={"displayName": "Reviewer", "email": "reviewer@example.com", "role": "reviewer"},
    ).json()
    space = client.post(
        "/api/team/spaces",
        json={"name": "AI Intel Room", "description": "Shared workspace", "actorUserId": analyst["id"]},
    ).json()

    membership = client.post(
        "/api/team/memberships",
        json={"spaceId": space["id"], "userId": analyst["id"], "role": "owner", "actorUserId": analyst["id"]},
    )

    source = _source(db_session)
    source_link = client.post(
        "/api/team/source-links",
        json={"spaceId": space["id"], "sourceId": source.id, "actorUserId": analyst["id"]},
    )
    cluster = _cluster(db_session)
    bookmark = client.post(
        "/api/team/bookmarks",
        json={
            "spaceId": space["id"],
            "userId": analyst["id"],
            "eventClusterId": cluster.id,
            "note": "Track for daily brief",
        },
    )
    annotation = client.post(
        "/api/team/annotations",
        json={
            "spaceId": space["id"],
            "userId": analyst["id"],
            "eventClusterId": cluster.id,
            "label": "risk",
            "note": "Potential customer impact",
        },
    )
    export = _brief_export(db_session, cluster.id)
    review = client.post(
        "/api/team/brief-reviews",
        json={
            "spaceId": space["id"],
            "briefExportId": export.id,
            "requestedByUserId": analyst["id"],
            "reviewerUserId": reviewer["id"],
            "notes": "Please review before sending",
        },
    ).json()
    approved = client.patch(
        f"/api/team/brief-reviews/{review['id']}",
        json={"actorUserId": reviewer["id"], "status": "approved", "notes": "Approved"},
    )

    summary = client.get("/api/team/summary")
    logs = client.get("/api/team/audit-logs")

    assert membership.status_code == 201
    assert source_link.status_code == 201
    assert bookmark.status_code == 201
    assert annotation.status_code == 201
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert summary.status_code == 200
    assert len(summary.json()["bookmarks"]) == 1
    assert len(summary.json()["annotations"]) == 1
    actions = {item["action"] for item in logs.json()}
    assert {
        "team_user.created",
        "team_space.created",
        "source.shared",
        "event.bookmarked",
        "event.annotated",
        "brief_review.requested",
        "brief_review.updated",
    }.issubset(actions)


def test_team_endpoints_reject_missing_entities(client):
    response = client.post(
        "/api/team/bookmarks",
        json={
            "spaceId": "missing",
            "userId": "missing",
            "eventClusterId": "missing",
        },
    )

    assert response.status_code == 404


def _source(db_session) -> Source:
    source = Source(type="rss", name="Shared RSS", url="https://example.com/feed", config_json={})
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


def _cluster(db_session) -> EventCluster:
    cluster = EventCluster(
        title="Shared event",
        summary="Shared event summary",
        hot_score=70,
        score_reason_json=[],
        confidence=80,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster


def _brief_export(db_session, cluster_id: str) -> BriefExport:
    export = BriefExport(
        template_id="template",
        title="Team brief",
        brief_type="team_brief",
        event_cluster_ids_json=[cluster_id],
        manual_notes_json={},
        export_formats_json=["markdown"],
        delivery_targets_json=[],
        markdown="# Team brief\n",
    )
    db_session.add(export)
    db_session.commit()
    db_session.refresh(export)
    return export
