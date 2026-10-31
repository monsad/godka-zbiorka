"""Pule gotowych zdań: do czytania na głos i tłumaczenia Bielika do poprawienia."""
from __future__ import annotations

import json
import random
from pathlib import Path


class Pula:
    def __init__(self, wpisy: list[dict]):
        self.wpisy = wpisy

    @classmethod
    def z_pliku(cls, path: Path) -> "Pula":
        path = Path(path)
        if not path.exists():
            return cls([])
        with path.open(encoding="utf-8") as f:
            return cls([json.loads(l) for l in f if l.strip()])

    def __len__(self) -> int:
        return len(self.wpisy)

    def losuj(self, poprzednie: str | None = None) -> dict | None:
        kandydaci = [w for w in self.wpisy if w["id"] != poprzednie] or self.wpisy
        return random.choice(kandydaci) if kandydaci else None
