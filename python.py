# check_requirements.py

import importlib
import sys
import pkg_resources

packages = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "python-multipart": "multipart",
    "numpy": "numpy",
    "pandas": "pandas",
    "scikit-learn": "sklearn",
    "matplotlib": "matplotlib",
    "opencv-python": "cv2",
    "opencv-contrib-python": "cv2",
    "torch": "torch",
    "torchvision": "torchvision",
    "facenet-pytorch": "facenet_pytorch",
    "transformers": "transformers",
    "moviepy": "moviepy",
    "tensorflow": "tensorflow",
    "keras": "keras",
    "requests": "requests",
    "tqdm": "tqdm",
    "fer": "fer",
    "speechbrain": "speechbrain",
    "pydub": "pydub",
    "whisper": "whisper"   # openai-whisper (speech-to-text)
}

print("Checking installed packages...\n")

for pkg_name, import_name in packages.items():
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, "__version__", None)
        if not version:
            version = pkg_resources.get_distribution(pkg_name).version
        print(f"{pkg_name}: Installed, version {version}")
    except Exception as e:
        print(f"{pkg_name}: NOT installed or error -> {e}")

print("\nAll checks completed!")
