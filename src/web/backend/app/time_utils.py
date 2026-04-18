"""时间戳规范化（与 anomaly 数据集 epoch 对齐）。"""


def to_epoch_seconds(ts_raw: int) -> int:
    t = int(ts_raw)
    at = abs(t)
    if at >= 10**17:
        return t // 10**9
    if at >= 10**14:
        return t // 10**6
    if at >= 10**11:
        return t // 10**3
    return t
