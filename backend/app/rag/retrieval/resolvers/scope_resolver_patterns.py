from __future__ import annotations

import re
import unicodedata
from typing import Any


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(char for char in normalized if not unicodedata.combining(char))
    stripped = stripped.replace("Ä‘", "d")
    return re.sub(r"\s+", " ", stripped).strip()


def _strip_quotes(value: str) -> str:
    return value.strip(" \t\r\n\"'â€œâ€â€˜â€™`")


def _and(*conditions: dict[str, Any]) -> dict[str, Any]:
    clean_conditions = [condition for condition in conditions if condition]
    if not clean_conditions:
        return {}
    if len(clean_conditions) == 1:
        return clean_conditions[0]
    return {"$and": clean_conditions}


def _or(*conditions: dict[str, Any]) -> dict[str, Any]:
    clean_conditions = [condition for condition in conditions if condition]
    if not clean_conditions:
        return {}
    if len(clean_conditions) == 1:
        return clean_conditions[0]
    return {"$or": clean_conditions}


CURRENT_UPLOAD_PATTERNS = (
    "file nay",
    "tai lieu nay",
    "file vua upload",
    "tai lieu vua upload",
    "file moi upload",
    "file vua tai len",
    "tai lieu vua tai len",
    "tai lieu hien tai",
    "trong session nay",
    "session nay",
)

AMBIGUOUS_DOCUMENT_PATTERNS = (
    "file do",
    "tai lieu do",
    "van ban do",
    "noi dung do",
    "cai do",
)

USER_HISTORY_PATTERNS = (
    "file cu",
    "file toi upload truoc do",
    "file da upload",
    "tai lieu lan truoc",
    "hom qua toi upload",
    "tai lieu da tai len",
    "file truoc do",
)

COMPARE_PATTERNS = (
    "so sanh",
    "doi chieu",
    "khac nhau",
    "giong nhau",
    "dap ung",
    "doi voi file cua toi",
)

SYSTEM_GENERAL_PATTERNS = (
    "thu tuc",
    "quy trinh",
    "ho so",
    "quy dinh",
    "quy che",
    "thong tu",
    "nghi dinh",
    "quyet dinh",
)

FOLLOW_UP_PATTERNS = (
    "the",
    "con",
    "vay",
    "thi sao",
    "bao lau",
    "le phi",
    "chi phi",
    "phi",
    "tiep theo",
    "phia tren",
    "no",
    "noi do",
    "muc do",
)

FILENAME_PATTERN = re.compile(
    r"""(?ix)
    (?:
        (?:file|tai\s+lieu|document)\s*
        (?:nay|nay\s+co|co\s+ten|ten\s+la|la)?\s*
        (?:[:\-]\s*)?
    )?
    ["'â€œâ€â€˜â€™`]?
    (?P<filename>[a-z0-9][a-z0-9_\-\s().\[\]]*\.(?:pdf|docx?|xlsx?|pptx?|txt|md))
    ["'â€œâ€â€˜â€™`]?
    """
)

PROCEDURE_INTENT_TAIL_PATTERN = re.compile(
    r"""(?ix)
    \s*
    (?:
        can\s+(?:ho\s+so(?:\s+gi)?|giay\s+to(?:\s+gi)?|nhung\s+gi|gi)|
        gom\s+(?:nhung\s+gi|gi)|
        co\s+(?:nhung\s+gi|gi)|
        thoi\s+han\s+(?:bao\s+lau|la\s+bao\s+lau|giai\s+quyet\s+bao\s+lau)|
        le\s+phi\s+(?:bao\s+nhieu|la\s+bao\s+nhieu|thi\s+sao)|
        phi\s+(?:bao\s+nhieu|la\s+bao\s+nhieu|thi\s+sao)|
        mat\s+bao\s+lau|
        xu\s+ly\s+bao\s+lau|
        la\s+gi|
        nhu\s+the\s+nao|
        ra\s+sao|
        o\s+dau|
        nao
    )
    \s*\??\s*$
    """
)

