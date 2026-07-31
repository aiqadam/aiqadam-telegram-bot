"""AC-10 self-check: the bot's runtime must never READ the three forbidden
credential env vars, anywhere in src/. This mirrors the grep-based check
CodeDeveloper ran manually, turned into a regression test so any future
change re-introducing a live reference fails CI immediately.

Matches only actual env-var-read patterns (pydantic `alias="X"`,
`os.environ["X"]` / `os.environ.get("X")` / `os.getenv("X")`) rather than
a bare substring match — this file's own module docstrings are allowed to
name the forbidden vars in prose (as config.py's does, to document the
guarantee) without tripping a false positive.
"""

from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN_NAMES = ("DIRECTUS_TOKEN", "AUTHENTIK_API_TOKEN", "TWENTY_API_TOKEN")

SRC_DIR = Path(__file__).resolve().parent.parent / "src"

_READ_PATTERNS = [
    re.compile(rf'alias\s*=\s*["\']({"|".join(FORBIDDEN_NAMES)})["\']'),
    re.compile(rf'os\.environ(?:\.get)?\[?["\']({"|".join(FORBIDDEN_NAMES)})["\']'),
    re.compile(rf'os\.getenv\(["\']({"|".join(FORBIDDEN_NAMES)})["\']'),
]


def test_no_forbidden_credential_env_reads_in_source() -> None:
    offenders: list[str] = []
    for path in SRC_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in _READ_PATTERNS:
            for match in pattern.finditer(text):
                offenders.append(f"{path}: {match.group(0)}")

    assert not offenders, f"Thin-bot guarantee violated: {offenders}"
