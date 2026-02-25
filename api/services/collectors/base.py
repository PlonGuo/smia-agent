"""Collector Protocol and self-registration registry."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from models.digest_schemas import RawCollectorItem

COLLECTOR_REGISTRY: dict[str, "Collector"] = {}


@runtime_checkable
class Collector(Protocol):
    name: str

    async def collect(self) -> list[RawCollectorItem]: ...


def register_collector(collector: Collector) -> None:
    """Register a collector instance. Called at import time."""
    COLLECTOR_REGISTRY[collector.name] = collector
