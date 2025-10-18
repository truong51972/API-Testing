import json
import subprocess


def from_hf(model_name: str) -> bool:
    result = subprocess.run(f"./scripts/hf_download.sh {model_name}", shell=True)
    print("Done!\n")
    return result.returncode == 0


def from_adapter(model_path: str) -> bool:
    """
    Load a language model by name.

    Args:
        model_name (str): The name of the model to load.

    Returns:
        str: The path to the directory where the merged model is saved.
    """
    if not model_path.startswith("models/"):
        model_path = f"models/{model_path}"

    adapter_config = json.load(open(f"{model_path}/adapter_config.json", "r"))
    base_model = adapter_config["base_model_name_or_path"]
    return from_hf(base_model)


if __name__ == "__main__":
    from_adapter(
        "Namtran0912/Qwen2.5-3B-Instruct-lora-adapter-v1",
    )
