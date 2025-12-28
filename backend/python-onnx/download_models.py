import os
import requests
from pathlib import Path

def download_models():
    """Download PP-OCRv5 models from OnnxOCR GitHub repository"""
    base_url = "https://raw.githubusercontent.com/jingsongliujing/OnnxOCR/main/onnxocr/models/ppocrv5/"
    models_dir = Path(__file__).parent / "models" / "ppocrv5"

    files = [
        "det/det.onnx",
        "rec/rec.onnx",
        "cls/cls.onnx",
        "ppocrv5_dict.txt"
    ]

    print("Starting model download...")

    for file_path in files:
        url = base_url + file_path
        local_path = models_dir / file_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            print(f"Downloading {file_path}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                f.write(response.content)

            print(f"Successfully downloaded {file_path}")

        except requests.exceptions.RequestException as e:
            print(f"Failed to download {file_path}: {e}")
            return False

    print("All models downloaded successfully!")
    return True

if __name__ == "__main__":
    download_models()