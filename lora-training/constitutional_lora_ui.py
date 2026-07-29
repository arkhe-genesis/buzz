import gradio as gr
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer, SFTConfig
from huggingface_hub import hf_hub_download, list_models, list_datasets
import os

# --- GLOBAL STATE ---
class AppState:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.peft_model_id = None

state = AppState()

# --- INFRASTRUCTURE FUNCTIONS ---
def search_models(query):
    """I3 (Substrate): Abstracted search across HF Hub."""
    models = list_models(search=query, limit=5)
    return [m.id for m in models]

def search_datasets(query):
    datasets = list_datasets(search=query, limit=5)
    return [ds.id for ds in datasets]

def train_model(model_id, dataset_id, lora_r, lora_alpha, lr, batch_size, quantization, progress=gr.Progress()):
    """O4 (Executive): Executes training. Enforces I4 (Polynomial) via LoRA bounds."""
    progress(0, desc="Initializing configuration...")

    try:
        # I1 (Physical): Memory constraints via Quantization
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=quantization == "4-bit",
            load_in_8bit=quantization == "8-bit",
            bnb_4bit_compute_dtype=torch.float16
        ) if quantization != "None" else None

        progress(0.2, desc="Loading Base Model...")
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )

        progress(0.4, desc="Applying LoRA Configuration...")
        # I4 (Complexity): Low-rank bounds ensure O(N*k) instead of O(N^2)
        peft_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=0.05,
            target_modules=["q_proj", "v_proj"] # Standardized for Llama/Mistral
        )
        model = get_peft_model(model, peft_config)

        progress(0.5, desc="Loading Dataset...")
        dataset = load_dataset(dataset_id, split="train")

        # Naive formatting (assumes single 'text' column for simplicity)
        def formatting_func(examples):
            return {"text": examples["text"]}
        dataset = dataset.map(formatting_func, batched=True)

        progress(0.6, desc="Initializing SFTTrainer...")
        training_args = SFTConfig(
            output_dir="./lora_adapter",
            per_device_train_batch_size=batch_size,
            learning_rate=lr,
            num_train_epochs=1, # Kept short for UI demo
            logging_steps=1,
            max_seq_length=512,
            save_strategy="epoch",
            fp16=torch.cuda.is_available(),
        )

        trainer = SFTTrainer(
            model=model,
            train_dataset=dataset,
            args=training_args,
            processing_class=tokenizer,
        )

        progress(0.7, desc="Executing Training Loop...")
        trainer.train()

        progress(0.9, desc="Saving Adapter...")
        adapter_path = f"./lora_adapter_{model_id.replace('/', '_')}"
        model.save_pretrained(adapter_path)
        tokenizer.save_pretrained(adapter_path)

        # Unload to free I1 (Physical) memory for Chat
        del model
        del trainer
        torch.cuda.empty_cache()

        state.peft_model_id = adapter_path
        state.tokenizer = tokenizer

        progress(1.0, desc="Training Complete.")
        return "✅ Training Successful. Adapter saved. Proceed to Chat."

    except Exception as e:
        return f"❌ Training Failed: {str(e)}"

def chat_with_model(message, history):
    """O3 (Decision): Inference loop."""
    if not state.peft_model_id or not state.tokenizer:
        yield history + [(message, "⚠️ Model not trained or loaded.")], ""
        return

    # Reload base + adapter for chat
    if state.model is None:
        base_model_id = state.peft_model_id.split("_lora_adapter_")[0] if "_lora_adapter_" in state.peft_model_id else "meta-llama/Llama-2-7b-hf" # Fallback
        try:
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_id, device_map="auto", torch_dtype=torch.float16
            )
            from peft import PeftModel
            state.model = PeftModel.from_pretrained(base_model, state.peft_model_id)
        except Exception as e:
            yield history + [(message, f"Failed to load model for chat: {e}")], ""
            return

    inputs = state.tokenizer(message, return_tensors="pt").to(state.model.device)
    outputs = state.model.generate(**inputs, max_new_tokens=256, pad_token_id=state.tokenizer.eos_token_id)
    response = state.tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Simple cleanup to remove prompt echo
    if message in response:
        response = response.replace(message, "").strip()

    yield history + [(message, response)], ""

# --- GRADIO UI (O1: Perceptual Interface) ---
with gr.Blocks(title="Constitutional LoRA UI") as ui:
    gr.Markdown("## 🏛️ One-Click LoRA Fine-Tuning Interface (v2.0 INFRA)")

    with gr.Tab("⚙️ Configure & Train"):
        with gr.Row():
            with gr.Column():
                model_search = gr.Textbox(label="Search Base Model (e.g., meta-llama)", scale=3)
                search_model_btn = gr.Button("Search", scale=1)
                model_dropdown = gr.Dropdown(label="Select Model", allow_custom_value=True)
            with gr.Column():
                dataset_search = gr.Textbox(label="Search Dataset (e.g., tatsu-lab/alpaca)", scale=3)
                search_ds_btn = gr.Button("Search", scale=1)
                dataset_dropdown = gr.Dropdown(label="Select Dataset", allow_custom_value=True)

        with gr.Row():
            lora_r = gr.Slider(4, 64, value=16, step=4, label="LoRA Rank (r)")
            lora_alpha = gr.Slider(8, 128, value=32, step=8, label="LoRA Alpha")
            lr = gr.Slider(1e-6, 1e-3, value=5e-5, label="Learning Rate", info="Log scale")
            batch_size = gr.Slider(1, 8, value=2, step=1, label="Batch Size")
            quant = gr.Dropdown(["4-bit", "8-bit", "None"], value="4-bit", label="Quantization (I1 Memory Bound)")

        train_btn = gr.Button("🚀 Execute Training", variant="primary")
        train_log = gr.Textbox(label="Training Log", lines=5, interactive=False)

    with gr.Tab("💬 Chat"):
        chatbot = gr.Chatbot(height=500)
        msg = gr.Textbox(label="Prompt")
        clear = gr.ClearButton([chatbot, msg])

    # --- EVENT BINDINGS ---
    search_model_btn.click(search_models, inputs=model_search, outputs=model_dropdown)
    search_ds_btn.click(search_datasets, inputs=dataset_search, outputs=dataset_dropdown)
    train_btn.click(train_model, [model_dropdown, dataset_dropdown, lora_r, lora_alpha, lr, batch_size, quant], train_log)
    msg.submit(chat_with_model, [msg, chatbot], [chatbot, msg])

if __name__ == "__main__":
    ui.launch()