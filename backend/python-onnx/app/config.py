import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_MODELS_DIR = os.path.join(BASE_DIR, "models")

def get_models_dir():
    return os.environ.get("PPOCR_MODELS_DIR", DEFAULT_MODELS_DIR)
