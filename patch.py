import sys
content = open('src/element_forecasting/evaluator.py').read()
to_insert = """

def masked_relative_mse_percent(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
\t\"\"\"掩膜版 Relative MSE 百分比（大赛标准）。\"\"\"
\tp = pred.float()
\tt = target.float()
\tm = mask.float()
\tdiff2 = (p - t).pow(2)
\tnum = torch.sum(diff2 * m)
\tden = torch.sum(t.pow(2) * m).clamp_min(eps)
\treturn (num / den) * 100.0
"""
content = content.replace("def masked_weighted_mse(", to_insert.lstrip() + "\ndef masked_weighted_mse(")
open('src/element_forecasting/evaluator.py', 'w').write(content)
