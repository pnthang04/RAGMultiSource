import re


def extract_heading(line: str) -> str | None:
    match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
    return match.group(2).strip() if match else None
