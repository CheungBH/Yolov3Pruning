import os
from prune.prune_config import data, models, only_metric
from prune.prune_config import prune, shortcut_p, slim_params, layer_num, all_prune_params

cmds = []
prune_folder = models

prune_cmd = ["python prune/prune.py --cfg {1} --data {4} --weights {0} --percent {2} --only_metric {3}".
                 format(w, c, per, only_metric, data) for w, c in prune_folder.items() for per in prune]

shortcut_prune_cmd = ["python prune/shortcut_prune.py --cfg {1} --data {4} --weights {0} --percent {2} " \
                      "--only_metric {3}".
                          format(w, c, per, only_metric, data) for w, c in prune_folder.items() for per in shortcut_p]

layer_prune_cmd = ["python prune/layer_prune.py --cfg {1} --data {4} --weights {0} --shortcuts {2}  --only_metric {3}".
                       format(w, c, num, only_metric, data) for w, c in prune_folder.items() for num in layer_num]

slim_prune_cmd = ["python prune/slim_prune.py --cfg {1} --data {5} --weights {0} --global_percent {2} --layer_keep {3} " \
                  "--only_metric {4}".
                      format(w, c, param[0], param[1], only_metric, data) for w, c in prune_folder.items() for param in slim_params]

all_prune_cmd = ["python prune/layer_channel_prune.py --cfg {1} --data {6} --weights {0} --shortcuts {2} " \
                 "--global_percent {3} --layer_keep {4} --only_metric {5}".
                     format(w, c, param[0], param[1], param[2], only_metric, data) for w, c in prune_folder.items()
                 for param in all_prune_params]

cmds += prune_cmd
cmds += shortcut_prune_cmd
cmds += layer_prune_cmd
cmds += slim_prune_cmd
cmds += all_prune_cmd

for cmd in cmds:
    cmd = cmd.replace("--only_metric False", "")
    os.system(cmd)

