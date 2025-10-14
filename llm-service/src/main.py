import subprocess

from utils import download_model, load_to_ollama, merge_adapter


def main(model_name: str):
    download_model.from_hf(
        model_name,
    )

    download_model.from_adapter(
        model_name,
    )

    merged_model_path = model_name.replace("lora-adapter", "merged")

    merge_adapter.merge_adapter(
        model_name,
        merged_model_path,
    )

    result = subprocess.run(
        f"./scripts/llamacpp_convert.sh {merged_model_path} --quantize",
        shell=True,
        check=True,
    )

    if result.returncode != 0:
        print("Error during model conversion")
        return
    print("Model conversion completed successfully")

    load_to_ollama.load_model_to_ollama(
        model_name=model_name.split("/")[-1].replace("-lora-adapter", ""),
        modelfile_path=merged_model_path + "/Modelfile",
    )


if __name__ == "__main__":
    model_name = "models/Namtran0912/Qwen2.5-3B-Instruct-lora-adapter-v1"
    main(model_name)
