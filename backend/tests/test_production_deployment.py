from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_private_vps_deployment_files_are_present():
    compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    caddyfile = (ROOT / "Caddyfile.prod").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "deployment-production.md").read_text(encoding="utf-8")

    assert "Dockerfile.prod" in compose
    assert "80:80" in compose
    assert "443:443" in compose
    assert "ports:" not in _service_block(compose, "backend:")
    assert "ports:" not in _service_block(compose, "db:")
    assert "basic_auth" in caddyfile
    assert "@api path /api/*" in caddyfile
    assert "BASIC_AUTH_HASH=" in env_example
    assert "X_BEARER_TOKEN=" in env_example
    assert "YOUTUBE_API_KEY=" in env_example
    assert "完全私有" in docs
    assert "BASIC_AUTH_HASH='$2a$14$example'" in docs
    assert "第一版不自动生成自然周周报" in docs


def _service_block(compose: str, service_header: str) -> str:
    start = compose.index(f"  {service_header}")
    next_marker = compose.find("\n  ", start + len(service_header) + 2)
    while next_marker != -1 and compose[next_marker + 3] == " ":
        next_marker = compose.find("\n  ", next_marker + 1)
    return compose[start:] if next_marker == -1 else compose[start:next_marker]
