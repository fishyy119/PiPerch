from typing import cast


def string(value: object) -> str:
    return cast("str", value)


def optional_string(value: object) -> str | None:
    return cast("str | None", value)


def integer(value: object) -> int:
    return cast("int", value)


def optional_integer(value: object) -> int | None:
    return cast("int | None", value)
