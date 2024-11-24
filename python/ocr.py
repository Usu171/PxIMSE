from paddleocr import PaddleOCR


class POCR():
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='ch')

    def get_ocr_result(self, file, ocr_threshold):
        result = self.ocr.ocr(file, cls=True)
        if result != [None]:
            filtered_texts = []
            for item in result[0]:
                text, confidence = item[1]
                if confidence >= ocr_threshold:
                    filtered_texts.append(text)
            return ' '.join(filtered_texts)
        else:
            return None

