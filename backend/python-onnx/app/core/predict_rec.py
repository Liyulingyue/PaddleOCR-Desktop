import cv2
import numpy as np

from .rec_postprocess import CTCLabelDecode, AttnLabelDecode
from .predict_base import PredictBase


class TextRecognizer(PredictBase):
    def __init__(self, args):
        self.rec_image_shape = [int(v) for v in args.rec_image_shape.split(",")]
        self.rec_batch_num = args.rec_batch_num
        self.label_type = args.rec_char_type
        self.postprocess = None
        if args.rec_algorithm == "CTC" or args.rec_char_type == "en":
            self.postprocess = CTCLabelDecode(
                character_dict_path=args.rec_char_dict_path, use_space_char=args.use_space_char
            )
        else:
            self.postprocess = AttnLabelDecode(
                character_dict_path=args.rec_char_dict_path, use_space_char=args.use_space_char
            )

        self.rec_onnx_session = self.get_onnx_session(args.rec_model_dir, args.use_gpu, gpu_id=args.gpu_id)
        self.rec_input_name = self.get_input_name(self.rec_onnx_session)
        self.rec_output_name = self.get_output_name(self.rec_onnx_session)

    def resize_norm_img(self, img):
        imgC, imgH, imgW = self.rec_image_shape
        h, w = img.shape[0:2]
        ratio = w / float(h)
        target_w = int(np.ceil(imgH * ratio))
        if target_w > imgW:
            target_w = imgW
        resized_image = cv2.resize(img, (target_w, imgH))
        resized_image = resized_image.astype("float32")
        if imgC == 1:
            resized_image = resized_image / 255.0
            resized_image = resized_image[np.newaxis, :]
        else:
            resized_image = resized_image.transpose((2, 0, 1)) / 255.0
        resized_image -= 0.5
        resized_image /= 0.5
        padding_im = np.zeros((imgC, imgH, imgW), dtype=np.float32)
        padding_im[:, :, 0:target_w] = resized_image
        return padding_im

    def __call__(self, img_list):
        img_num = len(img_list)
        norm_img_batch = []
        for img in img_list:
            norm_img = self.resize_norm_img(img)
            norm_img = norm_img[np.newaxis, :]
            norm_img_batch.append(norm_img)

        if len(norm_img_batch) == 0:
            # 没有可用图片，直接返回空结果
            return []
        norm_img_batch = np.concatenate(norm_img_batch)
        norm_img_batch = norm_img_batch.copy()

        input_feed = self.get_input_feed(self.rec_input_name, norm_img_batch)
        outputs = self.rec_onnx_session.run(self.rec_output_name, input_feed=input_feed)

        preds = outputs[0]
        result = self.postprocess(preds)
        return result
