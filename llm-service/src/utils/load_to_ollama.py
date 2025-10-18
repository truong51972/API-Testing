import subprocess


def load_model_to_ollama(model_name: str, modelfile_path: str):
    result = subprocess.run(
        f"docker exec llm-service_ollama ollama create {model_name} -f {modelfile_path}",
        shell=True,
        check=True,
    )

    if result.returncode != 0:
        print("Error during model import to Ollama")
        return
    print("Model imported to Ollama successfully")
