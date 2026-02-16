from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..utils import sha256_file


@dataclass
class LoRAMath:
    rank: int
    alpha: float

    def scale(self) -> float:
        return self.alpha / float(self.rank)

    def description(self) -> str:
        return (
            "W' = W + (alpha/r) * A @ B, "
            f"rank={self.rank}, alpha={self.alpha}, scale={self.scale():.4f}"
        )


def lora_checksum(path: str | Path) -> str | None:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    return sha256_file(p)
