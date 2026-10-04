from __future__ import annotations

import unicodedata


def normalize_search_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text.strip())
