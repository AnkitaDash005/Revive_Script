import cv2
import numpy
import torch
import transformers
import qdrant_client
from PIL import Image
from importlib.metadata import version


def check_environment() -> dict:
    return {
        "opencv": cv2.__version__,
        "numpy": numpy.__version__,
        "pytorch": torch.__version__,
        "transformers": transformers.__version__,
        "pillow": Image.__version__,
        "qdrant_client": version("qdrant-client"),
        "cuda_available": torch.cuda.is_available(),
    }


if __name__ == "__main__":
    environment = check_environment()

    print("=== Revive_Script AI Environment ===")

    for name, version in environment.items():
        print(f"{name}: {version}")