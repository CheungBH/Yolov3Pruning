import os
from prune.sparse_config import models, data, sparse_type, p_max, p_min

cmds = []
if "shortcut" in sparse_type:
    cmd = ["python prune/sparse.py --cfg {} --weights {} --percent_max {} --percent_min {}".format(
        cfg, weight, p_max, p_min) for weight, cfg in models.items()]
    cmds += cmd

if "ordinary" in sparse_type:
    cmd = ["python prune/sparse_shortcut.py --cfg {} --weights {} --percent_max {} --percent_min {}"
               .format(cfg, weight, p_max, p_min) for weight, cfg in models.items()]
    cmds += cmd

if "metric" in sparse_type:
    for weight, cfg in models.items():
        cmd = "python prune/metric.py --cfg {} --weights {} --data {}".format(cfg, weight, data)
        cmds.append(cmd)

for c in cmds:
    os.system(c)
