"""Data models (synthetic)."""
from dataclasses import dataclass


@dataclass
class Note:
    id: str
    owner: str
    body: str
