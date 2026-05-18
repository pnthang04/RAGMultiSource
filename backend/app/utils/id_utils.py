from uuid import uuid4


def generate_id(prefix: str | None = None) -> str:
    value = str(uuid4())
    return f"{prefix}_{value}" if prefix else value
