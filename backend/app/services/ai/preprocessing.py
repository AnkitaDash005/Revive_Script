from pathlib import Path

import cv2


class ImagePreprocessor:
    """
    Handles image preprocessing before OCR.
    """

    def load_image(self, image_path: str):
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        image = cv2.imread(str(path))

        if image is None:
            raise ValueError(
                f"Unable to read image: {image_path}"
            )

        return image

    def resize(self, image, max_width: int = 2000):
        """
        Resize very large images while maintaining aspect ratio.
        """

        height, width = image.shape[:2]

        if width <= max_width:
            return image

        scale = max_width / width

        new_width = int(width * scale)
        new_height = int(height * scale)

        return cv2.resize(
            image,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA,
        )

    def grayscale(self, image):
        return cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

    def denoise(self, image):
        return cv2.GaussianBlur(
            image,
            (3, 3),
            0,
        )

    def enhance_contrast(self, image):
        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8),
        )

        return clahe.apply(image)

    def threshold(self, image):
        return cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )

    def process(self, image_path: str):
        """
        Run the complete preprocessing pipeline.
        """

        original = self.load_image(image_path)

        resized = self.resize(original)

        grayscale = self.grayscale(resized)

        denoised = self.denoise(grayscale)

        enhanced = self.enhance_contrast(
            denoised
        )

        binary = self.threshold(
            enhanced
        )

        return {
            "original": resized,
            "grayscale": grayscale,
            "denoised": denoised,
            "enhanced": enhanced,
            "binary": binary,
        }