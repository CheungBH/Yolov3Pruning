import os

models_folder = "weight/pruning_firstTrial"
models = {}
for folder in os.listdir(models_folder):
    if not os.path.isdir(folder):
        models[os.path.join(models_folder, folder, "last.pt" )] = "cfg/yolov3-1cls.cfg"

data = "data/2022_11_03_cloudy_thermal/rgb.data"

# Sparse option
sparse_type = ["shortcut", "ordinary"]
p_max, p_min = 99, 50

