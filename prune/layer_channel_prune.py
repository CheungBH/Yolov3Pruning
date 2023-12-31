from models import *
from utils.utils import *
# from prune.util import obtain_avg_forward_time
from test import test
from terminaltables import AsciiTable
import time
from utils.prune_utils import *
import argparse
from utils.compute_flops import print_model_param_nums, print_model_param_flops
import csv

def obtain_avg_forward_time(input, model, repeat=200):
    model.eval()
    start = time.time()
    with torch.no_grad():
        for i in range(repeat):
            output = model(input)
    avg_infer_time = (time.time() - start) / repeat

    return avg_infer_time, output
def write_info(m, metric, string):
    params = print_model_param_nums(m)
    flops = print_model_param_flops(m)
    if string == "origin":
        f.write(('\n' + '%50s' * 1) % "origin")
    else:
        f.write(('\n' + '%50s' * 1) % ("ALL-{}".format(folder_str)))
    f.write(('%15s' * 1) % ("{}".format(flops)))
    processed_metric = [round(m, 4) for m in metric[0]]
    inf_time, _ = obtain_avg_forward_time(random_input, m)
    inf_time = round(inf_time, 4)
    f.write(('%10s' * 9) % (
        "{}".format(inf_time), "{}".format(params), "{}".format(processed_metric[0]),
        "{}".format(processed_metric[1]),
        "{}".format(processed_metric[2]), "{}".format(processed_metric[3]), "{}".format(processed_metric[4]),
        "{}".format(processed_metric[5]), "{}\n".format(processed_metric[6]),))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', type=str, default='cfg/yolov3-1cls.cfg', help='cfg file path')
    parser.add_argument('--data', type=str, default='data/swim_gray/gray.data', help='*.data file path')
    parser.add_argument('--weights', type=str, default='weights/last.pt', help='sparse model weights')
    parser.add_argument('--shortcuts', type=int, default=8, help='how many shortcut layers will be pruned,\
        pruning one shortcut will also prune two CBL,yolov3 has 23 shortcuts')
    parser.add_argument('--global_percent', type=float, default=0.6, help='global channel prune percent')
    parser.add_argument('--layer_keep', type=float, default=0.01, help='channel keep percent per layer')
    parser.add_argument('--img_size', type=int, default=416, help='inference size (pixels)')
    parser.add_argument('--only_metric', type=bool, default=False, help="whether save cfg and model")
    opt = parser.parse_args()
    print(opt)

    only_metric = opt.only_metric
    img_size = opt.img_size
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = Darknet(opt.cfg, (img_size, img_size)).to(device)

    if opt.weights.endswith(".pt"):
        model.load_state_dict(torch.load(opt.weights, map_location=device)['model'])
    else:
        _ = load_darknet_weights(model, opt.weights)
    print('\nloaded weights from ',opt.weights)

    folder_str = f'prune_{opt.global_percent}_keep_{opt.layer_keep}_{opt.shortcuts}_shortcut'
    if opt.weights.endswith(".pt"):
        model_name = opt.weights.split("/")[-1][:-3]
    elif opt.weights.endswith(".pth"):
        model_name = opt.weights.split("/")[-1][:-4]
    elif opt.weights.endswith(".weight"):
        model_name = opt.weights.split("/")[-1][:-7]
    else:
        raise ValueError("Wrong model name")

    dest_folder = os.path.join("prune_result", opt.weights.split("/")[1], "{}-{}/ALL-{}".
                               format(opt.weights.split("/")[2], model_name, folder_str))
    os.makedirs(dest_folder, exist_ok=True)
    prune_res = open(os.path.join(dest_folder, "prune_log.txt"), "a+")

    eval_model = lambda model:test(model=model, cfg=opt.cfg, data=opt.data, batch_size=16, img_size=img_size, conf_thres=0.1)
    obtain_num_parameters = lambda model:sum([param.nelement() for param in model.parameters()])
    random_input = torch.rand((1, 3, img_size, img_size)).to(device)


    if not only_metric:
        print("\nlet's test the original model first:")
        with torch.no_grad():
            origin_model_metric = eval_model(model)
        origin_nparameters = obtain_num_parameters(model)
    else:
        folder_name = "/".join(opt.weights.split("/")[:-1])
        res_file = os.path.join("prune_result", opt.weights.split("/")[1], "{}-{}".
                                format(opt.weights.split("/")[2], model_name), "prune_result.txt")
        if not os.path.exists(res_file):
            f = open(res_file, "w")
            f.write(('\n' + '%50s' * 1) % "Model")
            f.write(('%15s' * 1) % "FLOPs")
            f.write(('%10s' * 9) % ("Time", "Params", "P", "R", "mAP", "F1", "test_GIoU", "test_obj", "test_cls\n"))
            with torch.no_grad():
                origin_metric = eval_model(model)
            write_info(model, origin_metric, "origin")
        else:
            f = open(res_file, "a+")


    ##############################################################
    #先剪通道
    print("we will prune the channels first")
    print("we will prune the channels first", file=prune_res)


    CBL_idx, Conv_idx, prune_idx, _, _= parse_module_defs2(model.module_defs)



    bn_weights = gather_bn_weights(model.module_list, prune_idx)

    sorted_bn = torch.sort(bn_weights)[0]
    sorted_bn, sorted_index = torch.sort(bn_weights)
    thresh_index = int(len(bn_weights) * opt.global_percent)
    thresh = sorted_bn[thresh_index].cuda()

    print(f'Global Threshold should be less than {thresh:.4f}.')
    print(f'Global Threshold should be less than {thresh:.4f}.', file=prune_res)


    #%%
    def obtain_filters_mask(model, thre, CBL_idx, prune_idx):

        pruned = 0
        total = 0
        num_filters = []
        filters_mask = []
        for idx in CBL_idx:
            bn_module = model.module_list[idx][1]
            if idx in prune_idx:

                weight_copy = bn_module.weight.data.abs().clone()
                
                channels = weight_copy.shape[0] #
                min_channel_num = int(channels * opt.layer_keep) if int(channels * opt.layer_keep) > 0 else 1
                mask = weight_copy.gt(thresh).float()
                
                if int(torch.sum(mask)) < min_channel_num: 
                    _, sorted_index_weights = torch.sort(weight_copy,descending=True)
                    mask[sorted_index_weights[:min_channel_num]]=1. 
                remain = int(mask.sum())
                pruned = pruned + mask.shape[0] - remain

                print(f'layer index: {idx:>3d} \t total channel: {mask.shape[0]:>4d} \t '
                        f'remaining channel: {remain:>4d}')
                print(f'layer index: {idx:>3d} \t total channel: {mask.shape[0]:>4d} \t '
                        f'remaining channel: {remain:>4d}', file=prune_res)
            else:
                mask = torch.ones(bn_module.weight.data.shape)
                remain = mask.shape[0]

            total += mask.shape[0]
            num_filters.append(remain)
            filters_mask.append(mask.clone())

        prune_ratio = pruned / total
        print(f'Prune channels: {pruned}\tPrune ratio: {prune_ratio:.3f}')
        print(f'Prune channels: {pruned}\tPrune ratio: {prune_ratio:.3f}', file=prune_res)

        return num_filters, filters_mask

    num_filters, filters_mask = obtain_filters_mask(model, thresh, CBL_idx, prune_idx)
    CBLidx2mask = {idx: mask for idx, mask in zip(CBL_idx, filters_mask)}
    CBLidx2filters = {idx: filters for idx, filters in zip(CBL_idx, num_filters)}

    for i in model.module_defs:
        if i['type'] == 'shortcut':
            i['is_access'] = False

    print('merge the mask of layers connected to shortcut!')
    print('merge the mask of layers connected to shortcut!', file=prune_res)
    merge_mask(model, CBLidx2mask, CBLidx2filters)


    def prune_and_eval(model, CBL_idx, CBLidx2mask):
        model_copy = deepcopy(model)

        for idx in CBL_idx:
            bn_module = model_copy.module_list[idx][1]
            mask = CBLidx2mask[idx].cuda()
            bn_module.weight.data.mul_(mask)

        with torch.no_grad():
            mAP = eval_model(model_copy)[0][2]

        print(f'mask the gamma as zero, mAP of the model is {mAP:.4f}')
        print(f'mask the gamma as zero, mAP of the model is {mAP:.4f}', file=prune_res)

    if not only_metric:
        prune_and_eval(model, CBL_idx, CBLidx2mask)


    for i in CBLidx2mask:
        CBLidx2mask[i] = CBLidx2mask[i].clone().cpu().numpy()


    pruned_model = prune_model_keep_size2(model, prune_idx, CBL_idx, CBLidx2mask)

    if not only_metric:
        print("\nnow prune the model but keep size,(actually add offset of BN beta to following layers), let's see how the mAP goes")
        print("\nnow prune the model but keep size,(actually add offset of BN beta to following layers), let's see how the mAP goes", file=prune_res)

        with torch.no_grad():
            eval_model(pruned_model)

    for i in model.module_defs:
        if i['type'] == 'shortcut':
            i.pop('is_access')

    compact_module_defs = deepcopy(model.module_defs)
    for idx in CBL_idx:
        assert compact_module_defs[idx]['type'] == 'convolutional'
        compact_module_defs[idx]['filters'] = str(CBLidx2filters[idx])


    compact_model1 = Darknet([model.hyperparams.copy()] + compact_module_defs, (img_size, img_size)).to(device)
    compact_nparameters1 = obtain_num_parameters(compact_model1)

    init_weights_from_loose_model(compact_model1, pruned_model, CBL_idx, Conv_idx, CBLidx2mask)

    if not only_metric:
        print('testing the channel pruned model...')
        with torch.no_grad():
            compact_model_metric1 = eval_model(compact_model1)


    #########################################################
    #再剪层
    print('\nnow we prune shortcut layers and corresponding CBLs')
    print('\nnow we prune shortcut layers and corresponding CBLs', file=prune_res)


    CBL_idx, Conv_idx, shortcut_idx = parse_module_defs4(compact_model1.module_defs)
    print('all shortcut_idx:', [i + 1 for i in shortcut_idx])
    print('all shortcut_idx:', [i + 1 for i in shortcut_idx], file=prune_res)


    bn_weights = gather_bn_weights(compact_model1.module_list, shortcut_idx)

    sorted_bn = torch.sort(bn_weights)[0]


    # highest_thre = torch.zeros(len(shortcut_idx))
    # for i, idx in enumerate(shortcut_idx):
    #     highest_thre[i] = compact_model1.module_list[idx][1].weight.data.abs().max().clone()
    # _, sorted_index_thre = torch.sort(highest_thre)
    
    #这里更改了选层策略，由最大值排序改为均值排序，均值一般表现要稍好，但不是绝对，可以自己切换尝试；前面注释的四行为原策略。
    bn_mean = torch.zeros(len(shortcut_idx))
    for i, idx in enumerate(shortcut_idx):
        bn_mean[i] = compact_model1.module_list[idx][1].weight.data.abs().mean().clone()
    _, sorted_index_thre = torch.sort(bn_mean)
    
    prune_shortcuts = torch.tensor(shortcut_idx)[[sorted_index_thre[:opt.shortcuts]]]
    prune_shortcuts = [int(x) for x in prune_shortcuts]

    index_all = list(range(len(compact_model1.module_defs)))
    index_prune = []
    for idx in prune_shortcuts:
        index_prune.extend([idx - 1, idx, idx + 1])
    index_remain = [idx for idx in index_all if idx not in index_prune]

    print('These shortcut layers and corresponding CBL will be pruned :', index_prune)
    print('These shortcut layers and corresponding CBL will be pruned :', index_prune, file=prune_res)



    def prune_and_eval2(model, prune_shortcuts=[]):
        model_copy = deepcopy(model)
        for idx in prune_shortcuts:
            for i in [idx, idx-1]:
                bn_module = model_copy.module_list[i][1]

                mask = torch.zeros(bn_module.weight.data.shape[0]).cuda()
                bn_module.weight.data.mul_(mask)
         

        with torch.no_grad():
            mAP = eval_model(model_copy)[0][2]

        print(f'simply mask the BN Gama of to_be_pruned CBL as zero, now the mAP is {mAP:.4f}')
        print(f'simply mask the BN Gama of to_be_pruned CBL as zero, now the mAP is {mAP:.4f}', file=prune_res)

    if not only_metric:
        prune_and_eval2(compact_model1, prune_shortcuts)

    #%%
    def obtain_filters_mask2(model, CBL_idx, prune_shortcuts):

        filters_mask = []
        for idx in CBL_idx:
            bn_module = model.module_list[idx][1]
            mask = np.ones(bn_module.weight.data.shape[0], dtype='float32')
            filters_mask.append(mask.copy())
        CBLidx2mask = {idx: mask for idx, mask in zip(CBL_idx, filters_mask)}
        for idx in prune_shortcuts:
            for i in [idx, idx - 1]:
                bn_module = model.module_list[i][1]
                mask = np.zeros(bn_module.weight.data.shape[0], dtype='float32')
                CBLidx2mask[i] = mask.copy()
        return CBLidx2mask


    CBLidx2mask = obtain_filters_mask2(compact_model1, CBL_idx, prune_shortcuts)

    pruned_model = prune_model_keep_size2(compact_model1, CBL_idx, CBL_idx, CBLidx2mask)

    if not only_metric:
        with torch.no_grad():
            mAP = eval_model(pruned_model)[0][2]
        print("after transfering the offset of pruned CBL's activation, map is {}".format(mAP))
        print("after transfering the offset of pruned CBL's activation, map is {}".format(mAP), file=prune_res)


    compact_module_defs = deepcopy(compact_model1.module_defs)


    for module_def in compact_module_defs:
        if module_def['type'] == 'route':
            from_layers = [int(s) for s in module_def['layers'].split(',')]
            if len(from_layers) == 2:
                count = 0
                for i in index_prune:
                    if i <= from_layers[1]:
                        count += 1
                from_layers[1] = from_layers[1] - count
                from_layers = ', '.join([str(s) for s in from_layers])
                module_def['layers'] = from_layers

    compact_module_defs = [compact_module_defs[i] for i in index_remain]
    compact_model2 = Darknet([compact_model1.hyperparams.copy()] + compact_module_defs, (img_size, img_size)).to(device)
    for i, index in enumerate(index_remain):
        compact_model2.module_list[i] = pruned_model.module_list[index]

    compact_nparameters2 = obtain_num_parameters(compact_model2)

    print('testing the final model')
    with torch.no_grad():
        compact_model_metric2 = eval_model(compact_model2)


    if not only_metric:
        ################################################################
        # 剪枝完毕，测试速度
        random_input = torch.rand((1, 3, img_size, img_size)).to(device)

        print('testing inference time...')
        pruned_forward_time, output = obtain_avg_forward_time(random_input, model)
        compact_forward_time1, compact_output1 = obtain_avg_forward_time(random_input, compact_model1)
        compact_forward_time2, compact_output2 = obtain_avg_forward_time(random_input, compact_model2)

        metric_table = [
            ["Metric", "Before", "After prune channels", "After prune layers(final)"],
            ["mAP", f'{origin_model_metric[0][2]:.6f}', f'{compact_model_metric1[0][2]:.6f}',
             f'{compact_model_metric2[0][2]:.6f}'],
            ["Parameters", f"{origin_nparameters}", f"{compact_nparameters1}", f"{compact_nparameters2}"],
            ["Inference", f'{pruned_forward_time:.4f}', f'{compact_forward_time1:.4f}', f'{compact_forward_time2:.4f}']
        ]
        print(AsciiTable(metric_table).table)
        print(AsciiTable(metric_table).table, file=open(os.path.join(dest_folder, "metric.txt"), "w"))
        #save csv file
        csv_path = os.path.join("prune_result", opt.weights.split("/")[1], "{}-{}".
                               format(opt.weights.split("/")[2], model_name))
        exist = os.path.exists(os.path.join(csv_path, 'prune.csv'))
        with open(os.path.join(csv_path, 'prune.csv'), 'a+') as f:
            f_csv = csv.writer(f)
            if not exist:
                title = [
                    ['model','mAP','para','time'],
                    ['original', f'{origin_model_metric[0][2]:.6f}', f"{origin_nparameters}",
                     f'{pruned_forward_time:.4f}']
                ]
                f_csv.writerows(title)
            info_list = [f"ALL-{folder_str}",f'{compact_model_metric2[0][2]:.6f}',f"{compact_nparameters2}", f'{compact_forward_time2:.4f}']
            f_csv.writerow(info_list)

        cfg_name = os.path.join(dest_folder, folder_str + ".cfg")
        pruned_cfg_file = write_cfg(cfg_name, [model.hyperparams.copy()] + compact_module_defs)
        print(f'Config file has been saved: {pruned_cfg_file}')

        model_name = os.path.join(dest_folder, folder_str + ".weights")
        save_weights(compact_model2, model_name)
        print(f'Compact model has been saved: {model_name}')
    else:
        write_info(compact_model2, compact_model_metric2, "ALL")
        f.close()