def merge_adapter(model_path: str, save_directory: str) -> str:
    """
    Load a language model by name.

    Args:
        model_name (str): The name of the model to load.

    Returns:
        str: The path to the directory where the merged model is saved.
    """
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        dtype=None,  # None for auto detection
        max_seq_length=1024,  # Choose any for long context!
        load_in_4bit=True,  # 4 bit quantization to reduce memory
        full_finetuning=False,  # [NEW!] We have full finetuning now!
        # token = "hf_...", # use one if using gated models
    )

    if "-lora-adapter" in model_path:
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

    model.save_pretrained_merged(save_directory, tokenizer)

    return save_directory
