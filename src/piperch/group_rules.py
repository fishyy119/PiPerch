"""本地分组名称与数量规则，供请求校验、持久化和收藏标签导入共用。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from piperch.errors import AppError

if TYPE_CHECKING:
    from collections.abc import Sequence


MAX_GROUP_NAME_LENGTH = 20
MAX_ARTWORK_GROUPS = 10


def normalize_group_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise AppError("invalid_group_name", "本地分组名称不能为空。")
    if len(name) > MAX_GROUP_NAME_LENGTH:
        raise AppError("invalid_group_name", f"本地分组名称不能超过 {MAX_GROUP_NAME_LENGTH} 个字符。")
    if any(character.isspace() for character in name):
        raise AppError("invalid_group_name", "本地分组名称不能包含空白字符。")
    return name


def validate_imported_group_names(values: Sequence[str]) -> tuple[str, ...]:
    groups = tuple(dict.fromkeys(values))
    if len(groups) > MAX_ARTWORK_GROUPS:
        raise AppError("invalid_remote_bookmark_tags", f"Pixiv 收藏标签超过本地允许的 {MAX_ARTWORK_GROUPS} 个分组。")
    for group in groups:
        if normalize_group_name(group) != group:
            raise AppError("invalid_remote_bookmark_tags", "Pixiv 收藏标签不满足本地分组名称约束。")
    return groups
