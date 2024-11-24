from PIL import Image
import numpy as np
import tensorflow as tf
import skimage.transform


class DD1():
    
    def __init__(self, config):
        self.model, self.tags, self.width, self.height = self.get_model(config)

    def get_model(self, config):
        model = tf.keras.models.load_model(
            config['deepdanbooru-model-path'], compile=False)
        with open(config['deepdanbooru-tags-path'], 'r') as tags_text:
            tags = [tag for tag in (tag.strip() for tag in tags_text) if tag]
        width = model.input_shape[2]
        height = model.input_shape[1]
        return model, tags, width, height

    def predict_tags(self, image: Image.Image,
                 threshold: float) -> dict[str, float]:
        image_array = load_image_for_evaluate(image, self.width, self.height)
        image_shape = image_array.shape
        image_array = image_array.reshape(
            (1, image_shape[0], image_shape[1], image_shape[2]))

        y = self.model.predict(image_array)[0]

        return {
            tag: float(y[i])
            for i, tag in enumerate(self.tags)
            if y[i] >= threshold
        }


def transform_and_pad_image(
    image,
    target_width,
    target_height,
    order=1,
    mode="edge",
):
    """
    Transform image and pad by edge pixles.
    """
    image_width = image.shape[1]
    image_height = image.shape[0]
    image_array = image

    # centerize
    t = skimage.transform.AffineTransform(
        translation=(-image_width * 0.5, -image_height * 0.5))

    t += skimage.transform.AffineTransform(
        translation=(target_width * 0.5, target_height * 0.5))

    warp_shape = (target_height, target_width)

    image_array = skimage.transform.warp(
        image_array, (t).inverse,
        output_shape=warp_shape,
        order=order,
        mode=mode)

    return image_array


def load_image_for_evaluate(image: Image.Image,
                            width: int,
                            height: int,
                            normalize: bool = True) -> np.ndarray:
    image = tf.convert_to_tensor(np.array(image))

    image = tf.image.resize(
        image,
        size=(height, width),
        method=tf.image.ResizeMethod.AREA,
        preserve_aspect_ratio=True,
    )
    # image = tf.image.resize_with_pad(
    #     image,
    #     target_height=512,
    #     target_width=512,
    #     antialias=False
    # )
    image = image.numpy()  # EagerTensor to np.array
    image = transform_and_pad_image(image, width, height)

    if normalize:
        image = image / 255.0

    return image



