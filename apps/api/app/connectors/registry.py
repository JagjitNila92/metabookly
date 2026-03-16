from app.connectors.base import AbstractDistributorConnector
from app.connectors.mock import MockDistributorConnector
from app.connectors.gardners import GardnersConnector

_REGISTRY: dict[str, AbstractDistributorConnector] = {
    "MOCK": MockDistributorConnector(),
    "GARDNERS": GardnersConnector(),
}


def get_connector(distributor_code: str) -> AbstractDistributorConnector:
    connector = _REGISTRY.get(distributor_code.upper())
    if not connector:
        raise ValueError(f"No connector registered for distributor: {distributor_code}")
    return connector


def list_connectors() -> list[str]:
    return list(_REGISTRY.keys())
