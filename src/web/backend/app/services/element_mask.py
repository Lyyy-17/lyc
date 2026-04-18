"""要素预报 valid mask 切片（与预测张量维度对齐）。"""


def extract_mask(mask_numpy, t_idx, c_idx, H, W):
    if mask_numpy is None:
        return None
    if mask_numpy.shape == (H, W):
        return mask_numpy
    if mask_numpy.ndim == 3:
        if mask_numpy.shape[0] == 4:
            return mask_numpy[min(c_idx, 3)]
        return mask_numpy[min(t_idx, mask_numpy.shape[0] - 1)]
    if mask_numpy.ndim == 4:
        return mask_numpy[min(t_idx, mask_numpy.shape[0] - 1), min(c_idx, mask_numpy.shape[1] - 1)]
    return mask_numpy
