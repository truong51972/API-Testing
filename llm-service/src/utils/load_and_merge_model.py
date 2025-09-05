import argparse


def load_and_merge_model(model_path: str):
    """
    Load a language model by name.

    Args:
        model_name (str): The name of the model to load.

    Returns:
        model: The loaded language model.
        tokenizer: The tokenizer associated with the model.
    """
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        dtype=None,  # None for auto detection
        max_seq_length=512,  # Choose any for long context!
        load_in_4bit=True,  # 4 bit quantization to reduce memory
        full_finetuning=False,  # [NEW!] We have full finetuning now!
        # token = "hf_...", # use one if using gated models
    )

    if model_path.endswith("-lora-adapter"):
        model_path = model_path.replace("-lora-adapter", "")
    else:
        model = FastLanguageModel.get_peft_model(
            model,
            r=8,  # Choose any number > 0 ! Suggested 8, 16, 32, 64, 128
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
            lora_alpha=16,
            lora_dropout=0,  # Supports any, but = 0 is optimized
            bias="none",  # Supports any, but = "none" is optimized
            # [NEW] "unsloth" uses 30% less VRAM, fits 2x larger batch sizes!
            use_gradient_checkpointing="unsloth",  # True or "unsloth" for very long context
            random_state=3407,
            use_rslora=False,  # We support rank stabilized LoRA
            loftq_config=None,  # And LoftQ
        )

    save_directory = f"{model_path}-merged"
    model.save_pretrained_merged(save_directory, tokenizer)

    return model, tokenizer


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="load and merge model")
    parser.add_argument("model_path", type=str, help="Model path to load")

    args = parser.parse_args()

    model_path = args.model_path

    load_and_merge_model(model_path)
