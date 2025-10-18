import shutil
from pathlib import Path

AVAILABLE_MODELS = ["Llama-3.2", "Qwen2.5"]


def copy_model_file(model_name: str) -> bool:
    base_path = Path("assets/models")

    for available_model in AVAILABLE_MODELS:
        name = model_name.split("/")[-1]
        print(f"Checking if {name} starts with {available_model}")
        if name.startswith(available_model):
            src = base_path / available_model / "Modelfile"
            dest = Path(model_name) / "Modelfile"
            break

    try:
        shutil.copy(src, dest)
        print(f"Copied {src} to {dest}")
        return True
    except Exception as e:
        print(f"Error copying file: {e}")
        return False
