import argparse
import subprocess

from src.utils import copy_model_file, download_model, load_to_ollama, merge_adapter


def deploy_model(model_name: str):
    if not model_name.startswith("models/"):
        model_name = "models/" + model_name

    merged_model_path = model_name.replace("lora-adapter", "merged")

    # download_model.from_hf(
    #     model_name,
    # )

    # download_model.from_adapter(
    #     model_name,
    # )

    # merge_adapter.merge_adapter(
    #     model_name,
    #     merged_model_path,
    # )

    # result = subprocess.run(
    #     f"./scripts/llamacpp_convert.sh {merged_model_path} --quantize",
    #     shell=True,
    #     check=True,
    # )

    # if result.returncode != 0:
    #     print("Error during model conversion")
    #     return
    # print("Model conversion completed successfully")

    # copy_model_file.copy_model_file(merged_model_path)
    # print("Model file copied successfully")

    ollama_model_name = model_name.split("/")[-1].replace("-lora-adapter", "")

    load_to_ollama.load_model_to_ollama(
        model_name=ollama_model_name,
        modelfile_path=merged_model_path + "/Modelfile",
    )

    return ollama_model_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process model files")
    parser.add_argument("model_name", type=str, help="The name of the model to process")
    args = parser.parse_args()

    model_name = args.model_name

    deploy_model(model_name)
