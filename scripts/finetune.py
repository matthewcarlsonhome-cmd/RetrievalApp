#!/usr/bin/env python3
"""
Fine-tuning Pipeline for RAG Feedback Data

This script:
1. Exports positive feedback data from your RAG system
2. Prepares it in the correct format for training
3. Fine-tunes a LLaMA model using LoRA (Low-Rank Adaptation)
4. Saves the trained adapter weights

Requirements:
    pip install torch transformers datasets peft bitsandbytes accelerate trl

For GPU: NVIDIA GPU with 8GB+ VRAM (16GB+ recommended)
For CPU-only: Use cloud services (Together.ai, Replicate, etc.)
"""

import os
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# STEP 1: DATA EXPORT & PREPARATION
# =============================================================================

def export_training_data(
    api_url: str = "http://localhost:5000",
    output_path: str = "training_data.jsonl",
    min_examples: int = 50
) -> List[Dict]:
    """
    Export positive feedback examples from the RAG system.

    What this does:
    - Fetches all queries where users gave positive feedback
    - These are examples where the model gave GOOD answers
    - We'll use these to teach the model to give more answers like these
    """
    import requests

    logger.info(f"Exporting training data from {api_url}")

    response = requests.get(
        f"{api_url}/api/analytics/export",
        params={"format": "jsonl", "filter": "positive"}
    )

    if response.status_code != 200:
        raise Exception(f"Export failed: {response.text}")

    # Parse JSONL
    examples = []
    for line in response.text.strip().split('\n'):
        if line:
            examples.append(json.loads(line))

    logger.info(f"Exported {len(examples)} training examples")

    if len(examples) < min_examples:
        logger.warning(
            f"Only {len(examples)} examples. Recommend at least {min_examples} "
            "for effective fine-tuning. Continue collecting feedback!"
        )

    # Save to file
    with open(output_path, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')

    return examples


def prepare_training_format(
    input_path: str = "training_data.jsonl",
    output_path: str = "training_prepared.jsonl",
    system_prompt: str = None
) -> str:
    """
    Convert exported data to the exact format needed for training.

    The format varies by model:
    - LLaMA/Mistral: Uses chat template with special tokens
    - The model learns to predict the assistant's response given the user's query
    """

    if system_prompt is None:
        system_prompt = (
            "You are a helpful AI assistant for Matthew Carlson Consulting. "
            "Answer questions accurately based on the company's knowledge base. "
            "Be concise, professional, and helpful."
        )

    with open(input_path, 'r') as f:
        examples = [json.loads(line) for line in f if line.strip()]

    prepared = []
    for ex in examples:
        messages = ex.get('messages', [])

        # Add system prompt if not present
        if not messages or messages[0].get('role') != 'system':
            messages.insert(0, {'role': 'system', 'content': system_prompt})

        prepared.append({'messages': messages})

    with open(output_path, 'w') as f:
        for item in prepared:
            f.write(json.dumps(item) + '\n')

    logger.info(f"Prepared {len(prepared)} examples -> {output_path}")
    return output_path


# =============================================================================
# STEP 2: THE ACTUAL FINE-TUNING (What's Really Happening)
# =============================================================================

"""
## HOW FINE-TUNING ACTUALLY WORKS

### The Neural Network Perspective

A language model like LLaMA is a neural network with billions of "weights"
(numbers). These weights determine how the model transforms input text into
output text.

Before fine-tuning:
    Input: "What services do you offer?"
    Model weights: [w1, w2, w3, ... w8,000,000,000]
    Output: Generic response (trained on internet data)

After fine-tuning:
    Input: "What services do you offer?"
    Model weights: [w1', w2', w3', ... w8,000,000,000']  (slightly adjusted)
    Output: YOUR specific response about YOUR services

### What Happens During Training

1. FORWARD PASS:
   - Input your question: "What services do you offer?"
   - Model generates a prediction for each next token
   - Compare prediction to the ACTUAL answer from your data

2. LOSS CALCULATION:
   - Measure how "wrong" the model's prediction was
   - Loss = difference between predicted tokens and actual tokens
   - Lower loss = model is closer to your desired answers

3. BACKPROPAGATION:
   - Calculate how each weight contributed to the error
   - This uses calculus (gradients) to trace the error back
   - Each weight gets a "blame score" (gradient)

4. WEIGHT UPDATE:
   - Adjust weights to reduce the error
   - new_weight = old_weight - (learning_rate × gradient)
   - Small adjustments, repeated thousands of times

### Why LoRA (Low-Rank Adaptation)?

Full fine-tuning would update ALL 8 billion weights. Problems:
- Needs 100GB+ RAM
- Takes days
- Can "break" the model

LoRA is smarter:
- Freezes the original weights
- Adds small "adapter" matrices (only ~0.1% of parameters)
- Only trains these adapters
- Result: Same quality, 100x less compute

Visual:
    Original Model (frozen):     [████████████████████]  8B params
    LoRA Adapters (trained):     [█]                     8M params

The adapters learn "corrections" to the frozen model's behavior.

### The Math (Simplified)

For a weight matrix W (frozen), LoRA adds:
    W' = W + BA

Where:
    B = small matrix (e.g., 8B × 16)
    A = small matrix (e.g., 16 × 8B)
    BA = low-rank approximation of the "correction"

Only B and A are trained. This captures most of the learning
with a tiny fraction of the parameters.

### After Training

The trained LoRA weights are saved as a small file (~50-200MB).
To use the fine-tuned model:
    1. Load the original LLaMA model
    2. Load your LoRA adapter
    3. Merge them (or apply adapter dynamically)

The model now "remembers" your training data's patterns.
"""


def finetune_local(
    training_data: str,
    model_name: str = "meta-llama/Llama-3.2-3B-Instruct",
    output_dir: str = "./fine-tuned-model",
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
    max_seq_length: int = 2048,
    use_4bit: bool = True
):
    """
    Fine-tune a model locally using LoRA.

    Args:
        training_data: Path to JSONL training file
        model_name: HuggingFace model ID
        output_dir: Where to save the fine-tuned adapter
        epochs: Number of training passes through the data
        batch_size: Examples per training step
        learning_rate: How fast to adjust weights (too high = unstable)
        lora_r: Rank of LoRA matrices (higher = more capacity, more memory)
        lora_alpha: LoRA scaling factor
        max_seq_length: Maximum tokens per example
        use_4bit: Use 4-bit quantization (reduces memory 4x)
    """

    # Check for GPU
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    if device == "cpu":
        logger.warning(
            "No GPU detected! Training on CPU is VERY slow. "
            "Consider using cloud services (Together.ai, Replicate, etc.)"
        )
        use_4bit = False  # 4-bit requires CUDA

    # Import training libraries
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        BitsAndBytesConfig
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from datasets import load_dataset
    from trl import SFTTrainer

    # =========================================================================
    # LOAD THE BASE MODEL
    # =========================================================================
    logger.info(f"Loading base model: {model_name}")

    # Quantization config (4-bit reduces memory from ~16GB to ~4GB)
    if use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",  # Normalized Float 4-bit
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True  # Nested quantization
        )
    else:
        bnb_config = None

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32
    )

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Prepare model for training (required for quantized models)
    if use_4bit:
        model = prepare_model_for_kbit_training(model)

    # =========================================================================
    # CONFIGURE LoRA ADAPTERS
    # =========================================================================
    logger.info("Configuring LoRA adapters")

    # These are the layers we'll add adapters to
    # Attention layers are most important for learning new behaviors
    target_modules = [
        "q_proj",  # Query projection (attention)
        "k_proj",  # Key projection (attention)
        "v_proj",  # Value projection (attention)
        "o_proj",  # Output projection (attention)
        "gate_proj",  # MLP gate
        "up_proj",    # MLP up
        "down_proj"   # MLP down
    ]

    lora_config = LoraConfig(
        r=lora_r,                    # Rank: higher = more capacity
        lora_alpha=lora_alpha,       # Scaling: alpha/r = effective learning rate
        target_modules=target_modules,
        lora_dropout=0.05,           # Regularization
        bias="none",                 # Don't train biases
        task_type="CAUSAL_LM"        # Autoregressive language model
    )

    # Wrap model with LoRA adapters
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()  # Shows how few parameters we're training

    # =========================================================================
    # LOAD AND PREPARE DATASET
    # =========================================================================
    logger.info(f"Loading training data: {training_data}")

    dataset = load_dataset("json", data_files=training_data, split="train")

    # Format for chat
    def format_example(example):
        """Convert messages to model's expected format."""
        messages = example["messages"]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )
        return {"text": text}

    dataset = dataset.map(format_example)

    logger.info(f"Training on {len(dataset)} examples")

    # =========================================================================
    # TRAINING CONFIGURATION
    # =========================================================================

    # Calculate steps
    total_steps = (len(dataset) // batch_size) * epochs
    warmup_steps = min(100, total_steps // 10)

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,  # Effective batch = 4 × batch_size
        learning_rate=learning_rate,
        weight_decay=0.01,              # L2 regularization
        warmup_steps=warmup_steps,      # Gradually increase LR
        logging_steps=10,
        save_steps=100,
        save_total_limit=2,             # Keep only 2 checkpoints
        fp16=device == "cuda",          # Mixed precision training
        optim="paged_adamw_8bit" if use_4bit else "adamw_torch",
        lr_scheduler_type="cosine",     # LR decay schedule
        report_to="none",               # Disable wandb etc.
    )

    # =========================================================================
    # TRAIN!
    # =========================================================================
    logger.info("Starting training...")
    logger.info(f"  Epochs: {epochs}")
    logger.info(f"  Batch size: {batch_size}")
    logger.info(f"  Learning rate: {learning_rate}")
    logger.info(f"  Total steps: {total_steps}")

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        tokenizer=tokenizer,
    )

    # This is where the magic happens:
    # - For each batch of examples:
    #   1. Forward pass: model predicts next tokens
    #   2. Loss: compare predictions to actual responses
    #   3. Backward pass: calculate gradients
    #   4. Update: adjust LoRA weights
    trainer.train()

    # =========================================================================
    # SAVE THE TRAINED MODEL
    # =========================================================================
    logger.info(f"Saving fine-tuned model to {output_dir}")

    # Save LoRA adapter (small, ~50-200MB)
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Save training info
    info = {
        "base_model": model_name,
        "training_data": training_data,
        "num_examples": len(dataset),
        "epochs": epochs,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "timestamp": datetime.now().isoformat()
    }
    with open(f"{output_dir}/training_info.json", "w") as f:
        json.dump(info, f, indent=2)

    logger.info("Training complete!")
    return output_dir


# =============================================================================
# STEP 3: CLOUD FINE-TUNING ALTERNATIVES
# =============================================================================

def finetune_together(
    training_data: str,
    model_name: str = "meta-llama/Llama-3-8b-chat-hf",
    n_epochs: int = 3,
    api_key: str = None
):
    """
    Fine-tune using Together.ai (no local GPU needed).

    Together.ai handles all the infrastructure:
    - They have the GPUs
    - They run the training
    - They host the fine-tuned model

    Cost: ~$5-20 for small datasets
    """
    try:
        import together
    except ImportError:
        raise ImportError("Install together: pip install together")

    if api_key:
        together.api_key = api_key
    elif os.environ.get("TOGETHER_API_KEY"):
        together.api_key = os.environ["TOGETHER_API_KEY"]
    else:
        raise ValueError("Set TOGETHER_API_KEY environment variable")

    # Upload training file
    logger.info("Uploading training data to Together.ai...")
    file_response = together.Files.upload(file=training_data)
    file_id = file_response["id"]
    logger.info(f"Uploaded file: {file_id}")

    # Start fine-tuning job
    logger.info(f"Starting fine-tuning job for {model_name}...")
    job = together.FineTuning.create(
        model=model_name,
        training_file=file_id,
        n_epochs=n_epochs,
        learning_rate=1e-5,
        batch_size=4,
    )

    job_id = job["id"]
    logger.info(f"Fine-tuning job started: {job_id}")
    logger.info("This will take 30-60 minutes. Check status with:")
    logger.info(f"  together fine-tuning get {job_id}")

    return job_id


def finetune_replicate(
    training_data: str,
    api_key: str = None
):
    """
    Fine-tune using Replicate (another cloud option).
    """
    try:
        import replicate
    except ImportError:
        raise ImportError("Install replicate: pip install replicate")

    # Similar process to Together.ai
    # See: https://replicate.com/docs/guides/fine-tune-a-language-model
    logger.info("Replicate fine-tuning - see docs for setup")
    raise NotImplementedError("See Replicate docs for implementation")


# =============================================================================
# STEP 4: MERGE AND EXPORT
# =============================================================================

def merge_lora_weights(
    base_model: str,
    lora_path: str,
    output_path: str
):
    """
    Merge LoRA adapters into the base model for easier deployment.

    This creates a single model file that doesn't need the adapter
    to be loaded separately.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    logger.info(f"Loading base model: {base_model}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model)

    logger.info(f"Loading LoRA adapter: {lora_path}")
    model = PeftModel.from_pretrained(model, lora_path)

    logger.info("Merging weights...")
    model = model.merge_and_unload()

    logger.info(f"Saving merged model: {output_path}")
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)

    logger.info("Done! Merged model saved.")
    return output_path


def export_to_gguf(model_path: str, output_path: str):
    """
    Convert model to GGUF format for use with llama.cpp / Ollama.

    GGUF is a quantized format that:
    - Reduces model size 4-8x
    - Enables CPU inference
    - Works with Ollama
    """
    logger.info("Converting to GGUF format...")
    logger.info("This requires llama.cpp to be installed.")
    logger.info("Run:")
    logger.info(f"  python llama.cpp/convert.py {model_path} --outtype f16")
    logger.info(f"  ./llama.cpp/quantize {model_path}/model.gguf {output_path} Q4_K_M")


def create_ollama_modelfile(
    model_path: str,
    output_path: str = "Modelfile",
    system_prompt: str = None
):
    """
    Create an Ollama Modelfile for easy local deployment.
    """
    if system_prompt is None:
        system_prompt = (
            "You are a helpful AI assistant for Matthew Carlson Consulting. "
            "Answer questions accurately and professionally."
        )

    content = f'''# Ollama Modelfile for fine-tuned RAG assistant
FROM {model_path}

# Set parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "<|eot_id|>"

# System prompt
SYSTEM """
{system_prompt}
"""
'''

    with open(output_path, 'w') as f:
        f.write(content)

    logger.info(f"Created Modelfile: {output_path}")
    logger.info("To use with Ollama:")
    logger.info(f"  ollama create my-assistant -f {output_path}")
    logger.info("  ollama run my-assistant")


# =============================================================================
# MAIN CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Fine-tune a language model with your RAG feedback data"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export training data from RAG system")
    export_parser.add_argument("--url", default="http://localhost:5000", help="RAG API URL")
    export_parser.add_argument("--output", default="training_data.jsonl", help="Output file")

    # Prepare command
    prep_parser = subparsers.add_parser("prepare", help="Prepare data for training")
    prep_parser.add_argument("--input", default="training_data.jsonl", help="Input file")
    prep_parser.add_argument("--output", default="training_prepared.jsonl", help="Output file")
    prep_parser.add_argument("--system-prompt", help="System prompt to use")

    # Train command (local)
    train_parser = subparsers.add_parser("train", help="Fine-tune model locally")
    train_parser.add_argument("--data", default="training_prepared.jsonl", help="Training data")
    train_parser.add_argument("--model", default="meta-llama/Llama-3.2-3B-Instruct", help="Base model")
    train_parser.add_argument("--output", default="./fine-tuned-model", help="Output directory")
    train_parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    train_parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    train_parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")

    # Train command (cloud)
    cloud_parser = subparsers.add_parser("train-cloud", help="Fine-tune using Together.ai")
    cloud_parser.add_argument("--data", default="training_prepared.jsonl", help="Training data")
    cloud_parser.add_argument("--model", default="meta-llama/Llama-3-8b-chat-hf", help="Base model")
    cloud_parser.add_argument("--epochs", type=int, default=3, help="Training epochs")

    # Merge command
    merge_parser = subparsers.add_parser("merge", help="Merge LoRA weights into base model")
    merge_parser.add_argument("--base", required=True, help="Base model path")
    merge_parser.add_argument("--lora", required=True, help="LoRA adapter path")
    merge_parser.add_argument("--output", required=True, help="Output path")

    # Ollama command
    ollama_parser = subparsers.add_parser("ollama", help="Create Ollama Modelfile")
    ollama_parser.add_argument("--model", required=True, help="Model path (GGUF)")
    ollama_parser.add_argument("--output", default="Modelfile", help="Output file")

    args = parser.parse_args()

    if args.command == "export":
        export_training_data(args.url, args.output)

    elif args.command == "prepare":
        prepare_training_format(args.input, args.output, args.system_prompt)

    elif args.command == "train":
        finetune_local(
            args.data,
            args.model,
            args.output,
            args.epochs,
            args.batch_size,
            args.lr
        )

    elif args.command == "train-cloud":
        finetune_together(args.data, args.model, args.epochs)

    elif args.command == "merge":
        merge_lora_weights(args.base, args.lora, args.output)

    elif args.command == "ollama":
        create_ollama_modelfile(args.model, args.output)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
