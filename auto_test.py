from test import test
import os
import torch

target_weight_names = ["last.pt"]
conf = 0.5
data = "data/2022_11_03_cloudy_thermal/rgb.data"
bs = 8

src_folder = "weights/pruning_firstTrial"
test_file = os.path.join(src_folder, "test.txt")
models, cfgs = [], []
for folder in os.listdir(src_folder):
    sub_folder = os.path.join(src_folder, folder)
    if not os.path.isdir(sub_folder):
        continue
    cfg_file = os.path.join(sub_folder, "cfg.cfg")
    for file in os.listdir(sub_folder):
        if file in target_weight_names:
            models.append(os.path.join(sub_folder, file))
            cfgs.append(cfg_file)

if os.path.exists(test_file):
    file = open(test_file, "a+")
else:
    file = open(test_file, "w")
    file.write("Model, P, R, mAP, F1, reg_loss, obj_loss, cls_loss\n")
for idx, (model, cfg) in enumerate(zip(models, cfgs)):
    if idx % 5 == 0:
        print("Processing model {}".format(idx))
    with torch.no_grad():
        metrics, _ = test(cfg, data, model, batch_size=bs, conf_thres=conf)
    test_str = model + "," + ",".join([str(round(item, 4)) for item in metrics])
    file.write(test_str + "\n")






