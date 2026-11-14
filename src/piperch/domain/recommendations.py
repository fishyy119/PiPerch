from __future__ import annotations

from math import log, log1p
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


# 以一个基准强度的共享标签为评分单位，定义额外关联的标签等效数。
SAME_AUTHOR_EQUIVALENT_TAGS = 4.0
SHARED_GROUP_EQUIVALENT_TAGS = 1.5


def inverse_document_frequency(artwork_count: int, frequency: int) -> float:
    """以作品为文档，计算标签或分组的平滑 IDF。"""
    return log((artwork_count + 1) / (frequency + 1)) + 1


def shared_idf_baseline(artwork_count: int, frequencies: Iterable[int]) -> float:
    """按出现次数的对数加权，计算可共享标签或分组的 IDF 基准。"""
    weighted_idf = 0.0
    total_weight = 0.0
    for frequency in frequencies:
        if frequency < 2:
            continue
        weight = log1p(frequency)
        weighted_idf += weight * inverse_document_frequency(artwork_count, frequency)
        total_weight += weight
    # 启动时没有共享命中的维度，以一个普通命中作为分值基准。
    return weighted_idf / total_weight if total_weight else 1.0
