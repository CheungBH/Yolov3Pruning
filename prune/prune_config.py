import os
models = {
    # "sparse_result/0909_test/test1/backup170.pt": "cfg/yolov3-1cls.cfg",
    # "weight/pruning_firstTrial/original/last.pt": "cfg/yolov3-1cls.cfg",
    "weight/pruning_firstTrial/normal_s5e-3/last.pt": "cfg/yolov3-1cls.cfg",
    # "sparse_result/0920/gray26_s2E-3/last.pt": "cfg/yolov3-1cls.cfg",
    # "sparse_result/0920/gray26_s3E-3/last.pt": "cfg/yolov3-1cls.cfg",
    # "sparse_result/0920/gray26_s4E-3/last.pt": "cfg/yolov3-1cls.cfg",
    # '0902_origin/best.weights': 'cfg/yolov3-1cls.cfg',
    # "sparse_result/0915/black/best.weights": "cfg/yolov3-1cls.cfg",
    # "sparse_result/0915/gray/best.weights": "cfg/yolov3-1cls.cfg"
}


data = "data/2022_11_03_cloudy_thermal/rgb.data"

# Sparse option
sparse_type = ["shortcut", "ordinary"]
p_max, p_min = 99, 50

# Prune option
only_metric = False

prune = []
shortcut_p = []
layer_num = []
slim_params = []
all_prune_params = [(8, 0.6, 0.01), (6, 0.7, 0.01)]

# Finetune option
# finetune_folders = [
#     # "prune_result/0909_test/test1-best/ALL-prune_0.95_keep_0.01_10_shortcut",
#     # os.path.join('prune_result/0909_test/test1-best',i)  for i in os.listdir('./prune_result/0909_test/test1-best')
#     # if os.path.isdir(os.path.join('prune_result/0909_test/test1-best',i))
# os.path.join('prune_result/0920_test/gray26_sE-3-last', i)
# for i in os.listdir('./prune_result/0920_test/gray26_sE-3-last')
# if os.path.isdir(os.path.join('prune_result/0920_test/gray26_sE-3-last', i))
#     # "prune_result/0909_test/test1-backup170-layer_prune-prune_12_shortcut",
#     # "prune_result/0909_test/test1-backup170-ordinary_prune-prune_0.85",
#     # "prune_result/0909_test/test1-backup170-shortcut_prune-prune_0.9",
# ]
# # print(finetune_folders)
# batch_size = 16
# epoch = 100
# ms = True
#
# # (Distillation)
# t_cfg = "weights/teacher/146/yolov3-original-1cls-leaky.cfg"
# t_weight = "weights/teacher/146/best.pt"
