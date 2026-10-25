"""Repository-relative runtime configuration."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class AppConfig:
    root: Path
    code: Path
    dataset: Path
    cache: Path
    tesseract_cmd: str | None

    @classmethod
    def from_entrypoint(cls, entrypoint: str | Path) -> 'AppConfig':
        code=Path(entrypoint).resolve().parent
        root=code.parent
        return cls(root=root,code=code,dataset=root/'dataset',cache=code/'.cache',tesseract_cmd=os.getenv('TESSERACT_CMD'))
