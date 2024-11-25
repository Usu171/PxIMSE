import torch
import clip


class CLIP1():
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        
    def get_clip_result(self, image):
        image = self.preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            image_features = self.model.encode_image(image)
            return self.post_processing(image_features)

    def get_clip_text_result(self, text):
        text = clip.tokenize(text).to(self.device)
        with torch.no_grad():
            text_features = self.model.encode_text(text)
            return self.post_processing(text_features)

    # FP16
    def post_processing(self, data):
        data = data / data.norm(dim=1, keepdim=True)
        data = data.detach().cpu().numpy()
        return data
