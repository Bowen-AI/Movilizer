from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..utils import get_logger

logger = get_logger("models.adapters")


class ReferenceAdapter:
    name = "base"

    def apply(self, generation_kwargs: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
        return generation_kwargs


class NoOpReferenceAdapter(ReferenceAdapter):
    name = "noop"

    def apply(self, generation_kwargs: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
        generation_kwargs["_ref_adapter"] = "noop"
        generation_kwargs["_references"] = references
        return generation_kwargs


@dataclass
class IPAdapterConfig:
    enabled: bool = False
    weight: float = 0.7


class IPAdapterReferenceAdapter(ReferenceAdapter):
    name = "ip_adapter"

    def __init__(self, config: IPAdapterConfig | None = None) -> None:
        self.config = config or IPAdapterConfig()

    def apply(self, generation_kwargs: dict[str, Any], references: dict[str, Any]) -> dict[str, Any]:
        generation_kwargs["_ref_adapter"] = "ip_adapter"
        generation_kwargs["_references"] = references
        generation_kwargs["_ip_adapter_weight"] = self.config.weight
        logger.info(
            "IP-Adapter selected; baseline implementation keeps references in kwargs. "
            "Replace this method with diffusers IP-Adapter conditioning for production."
        )
        return generation_kwargs


def make_reference_adapter(adapter_cfg: dict[str, Any] | None) -> ReferenceAdapter:
    cfg = adapter_cfg or {}
    name = str(cfg.get("name", "noop")).lower()
    if name == "ip_adapter" and cfg.get("enabled", False):
        return IPAdapterReferenceAdapter(
            IPAdapterConfig(enabled=True, weight=float(cfg.get("weight", 0.7)))
        )
    return NoOpReferenceAdapter()
