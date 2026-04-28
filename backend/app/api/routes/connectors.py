from fastapi import APIRouter

from app.connectors import registered_connectors


router = APIRouter(prefix="/api/connectors", tags=["connectors"])


@router.get("")
def list_connectors() -> list[dict[str, object]]:
    return [
        {
            "type": connector.type,
            "name": connector.name,
            "capabilities": connector.capabilities,
            "realFetchEnabled": connector.real_fetch_enabled,
        }
        for connector in registered_connectors
    ]
