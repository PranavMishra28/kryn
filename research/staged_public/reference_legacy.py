"""Trusted reference for no-model oracle control."""


def parse_legacy_id(text: str) -> int:
    value = text.strip()
    if value.startswith("#"):
        value = value[1:]
    if not value or not value.isdecimal():
        raise ValueError("invalid legacy ID")
    number = int(value)
    if number <= 0:
        raise ValueError("invalid legacy ID")
    return number
