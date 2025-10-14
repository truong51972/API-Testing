def convert_to_gguf(model_path: str, output_path: str) -> None:
    """
    Convert a model to GGUF format using the llama.cpp converter.

    Args:
        model_path (str): Path to the original model file.
        output_path (str): Path where the converted GGUF model will be saved.
    """
    import subprocess

    try:
        subprocess.run(["llama.cpp/convert", model_path, output_path], check=True)
        print(f"Model converted to GGUF format and saved at {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e}")
