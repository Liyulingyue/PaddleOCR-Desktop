import time

from .predict_system import TextSystem
from pathlib import Path
from ..config import get_models_dir
from .utils import str2bool
import argparse


class ONNXPaddleOcr(TextSystem):
    def __init__(self, **kwargs):
        parser = argparse.ArgumentParser()
        # Add all the arguments as in infer_args
        parser.add_argument("--use_gpu", type=str2bool, default=True)
        parser.add_argument("--use_xpu", type=str2bool, default=False)
        parser.add_argument("--use_npu", type=str2bool, default=False)
        parser.add_argument("--ir_optim", type=str2bool, default=True)
        parser.add_argument("--use_tensorrt", type=str2bool, default=False)
        parser.add_argument("--min_subgraph_size", type=int, default=15)
        parser.add_argument("--precision", type=str, default="fp32")
        parser.add_argument("--gpu_mem", type=int, default=500)
        parser.add_argument("--gpu_id", type=int, default=0)

        parser.add_argument("--image_dir", type=str)
        parser.add_argument("--page_num", type=int, default=0)
        parser.add_argument("--det_algorithm", type=str, default="DB")
        parser.add_argument(
            "--det_model_dir",
            type=str,
            default=str(Path(get_models_dir()) / "ppocrv5/det/det.onnx"),
        )
        parser.add_argument("--det_limit_side_len", type=float, default=960)
        parser.add_argument("--det_limit_type", type=str, default="max")
        parser.add_argument("--det_box_type", type=str, default="quad")

        parser.add_argument("--det_db_thresh", type=float, default=0.3)
        parser.add_argument("--det_db_box_thresh", type=float, default=0.6)
        parser.add_argument("--det_db_unclip_ratio", type=float, default=1.5)
        parser.add_argument("--max_batch_size", type=int, default=10)
        parser.add_argument("--use_dilation", type=str2bool, default=False)
        parser.add_argument("--det_db_score_mode", type=str, default="fast")

        parser.add_argument("--det_east_score_thresh", type=float, default=0.8)
        parser.add_argument("--det_east_cover_thresh", type=float, default=0.1)
        parser.add_argument("--det_east_nms_thresh", type=float, default=0.2)

        parser.add_argument("--det_sast_score_thresh", type=float, default=0.5)
        parser.add_argument("--det_sast_nms_thresh", type=float, default=0.2)

        parser.add_argument("--rec_algorithm", type=str, default="CRNN")
        parser.add_argument("--rec_char_type", type=str, default="en")
        parser.add_argument(
            "--rec_model_dir",
            type=str,
            default=str(Path(get_models_dir()) / "ppocrv5/rec/rec.onnx"),
        )
        parser.add_argument("--rec_image_shape", type=str, default="3, 48, 320")
        parser.add_argument("--rec_batch_num", type=int, default=6)
        parser.add_argument("--max_text_length", type=int, default=25)
        parser.add_argument(
            "--rec_char_dict_path",
            type=str,
            default=str(Path(get_models_dir()) / "ppocrv5/ppocrv5_dict.txt"),
        )
        parser.add_argument("--use_space_char", type=str2bool, default=True)
        parser.add_argument("--vis_font_path", type=str, default="./doc/fonts/simfang.ttf")
        parser.add_argument("--drop_score", type=float, default=0.5)

        parser.add_argument("--e2e_algorithm", type=str, default="PGNet")
        parser.add_argument("--e2e_model_dir", type=str)
        parser.add_argument("--e2e_limit_side_len", type=float, default=768)
        parser.add_argument("--e2e_limit_type", type=str, default="max")

        parser.add_argument("--e2e_pgnet_score_thresh", type=float, default=0.5)
        parser.add_argument("--e2e_char_dict_path", type=str, default="./ppocr/utils/ic15_dict.txt")
        parser.add_argument("--e2e_pgnet_valid_set", type=str, default="totaltext")
        parser.add_argument("--e2e_pgnet_mode", type=str, default="fast")

        parser.add_argument("--use_angle_cls", type=str2bool, default=True)
        parser.add_argument("--cls_algorithm", type=str, default="CLS")
        parser.add_argument(
            "--cls_model_dir",
            type=str,
            default=str(Path(get_models_dir()) / "ppocrv5/cls/cls.onnx"),
        )
        parser.add_argument("--cls_image_shape", type=str, default="3, 48, 192")
        parser.add_argument("--label_list", type=list, default=["0", "180"])
        parser.add_argument("--cls_batch_num", type=int, default=6)
        parser.add_argument("--cls_thresh", type=float, default=0.9)

        parser.add_argument("--enable_mkldnn", type=str2bool, default=False)
        parser.add_argument("--cpu_threads", type=int, default=10)
        parser.add_argument("--use_pdserving", type=str2bool, default=False)
        parser.add_argument("--warmup", type=str2bool, default=False)

        parser.add_argument("--draw_img_save_dir", type=str, default="./inference_results")
        parser.add_argument("--save_crop_res", type=str2bool, default=False)
        parser.add_argument("--crop_res_save_dir", type=str, default="./output")

        parser.add_argument("--save_log_path", type=str, default="./log_output/")

        parser.add_argument("--show_log", type=str2bool, default=True)
        parser.add_argument("--use_mp", type=str2bool, default=False)
        parser.add_argument("--total_process_num", type=int, default=1)
        parser.add_argument("--process_id", type=int, default=0)

        parser.add_argument("--benchmark", type=str2bool, default=False)
        parser.add_argument("--save_mem_path", type=str, default="./output")
        parser.add_argument("--collect_shape_info", type=str2bool, default=False)
        parser.add_argument("--shape_info_filename", type=str, default="shape_info.txt")

        parser.add_argument("--use_onnx", type=str2bool, default=False)

        inference_args_dict = {}
        for action in parser._actions:
            inference_args_dict[action.dest] = action.default
        params = argparse.Namespace(**inference_args_dict)

        params.rec_image_shape = "3, 48, 320"
        params.__dict__.update(**kwargs)
        super().__init__(params)

    def ocr(self, img, det=True, rec=True, cls=True):
        if cls == True and self.use_angle_cls == False:
            print(
                "Since the angle classifier is not initialized, the angle classifier will not be used during the forward process"
            )

        if det and rec:
            ocr_res = []
            dt_boxes, rec_res = self.__call__(img, cls)
            tmp_res = [[box.tolist(), res] for box, res in zip(dt_boxes, rec_res)]
            ocr_res.append(tmp_res)
            return ocr_res
        elif det and not rec:
            ocr_res = []
            dt_boxes = self.text_detector(img)
            tmp_res = [box.tolist() for box in dt_boxes]
            ocr_res.append(tmp_res)
            return ocr_res
        else:
            ocr_res = []
            cls_res = []

            if not isinstance(img, list):
                img = [img]
            if self.use_angle_cls and cls:
                img, cls_res_tmp = self.text_classifier(img)
                if not rec:
                    cls_res.append(cls_res_tmp)
            rec_res = self.text_recognizer(img)
            ocr_res.append(rec_res)

            if not rec:
                return cls_res
            return ocr_res


def sav2Img(org_img, result, name="draw_ocr.jpg"):
    from PIL import Image

    result = result[0]
    image = org_img[:, :, ::-1]
    boxes = [line[0] for line in result]
    txts = [line[1][0] for line in result]
    scores = [line[1][1] for line in result]
    im_show = draw_ocr(image, boxes, txts, scores)
    im_show = Image.fromarray(im_show)
    im_show.save(name)
