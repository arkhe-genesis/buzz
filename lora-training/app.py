# app.py — Gradio Interface para One-Click LoRA Fine-Tuning
import gradio as gr
import torch
import os
import subprocess
import json
from threading import Thread
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    pipeline
)
from peft import LoraConfig, get_peft_model, PeftModel
from trl import SFTTrainer
from datasets import load_dataset
import bitsandbytes as bnb

# ============================================================================
# CONFIGURAÇÃO PADRÃO (PODE SER SOBRESCRITA PELA UI)
# ============================================================================
DEFAULT_CONFIG = {
    "model_id": "meta-llama/Llama-3.2-3B-Instruct",
    "dataset_id": "argilla/distilabel-capybara-dpo-7k-binarized",
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
    "quantization": "4bit_nf4",
    "batch_size": 2,
    "grad_accum": 8,
    "learning_rate": 2e-4,
    "epochs": 1,
    "max_seq_length": 2048,
    "output_dir": "./lora_adapter"
}

# ============================================================================
# FUNÇÕES DE TREINO (NÃO BLOQUEIAM A UI)
# ============================================================================
training_status = {"running": False, "progress": 0.0, "log": "", "done": False}

def train_model(config, progress=gr.Progress()):
    """Função de treino executada em thread separada."""
    global training_status
    training_status["running"] = True
    training_status["progress"] = 0.0
    training_status["log"] = ""
    training_status["done"] = False

    try:
        progress(0.0, desc="Carregando modelo...")
        training_status["log"] = "Carregando modelo e tokenizer...\n"

        # 1. Quantização (se configurada)
        bnb_config = None
        if config["quantization"] == "4bit_nf4":
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True
            )
        elif config["quantization"] == "8bit":
            bnb_config = BitsAndBytesConfig(load_in_8bit=True)

        # 2. Carregar modelo
        model = AutoModelForCausalLM.from_pretrained(
            config["model_id"],
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )
        tokenizer = AutoTokenizer.from_pretrained(
            config["model_id"],
            trust_remote_code=True
        )
        tokenizer.pad_token = tokenizer.eos_token

        progress(0.2, desc="Configurando LoRA...")
        training_status["log"] += "Configurando LoRA...\n"

        # 3. Configurar LoRA
        lora_config = LoraConfig(
            r=config["lora_r"],
            lora_alpha=config["lora_alpha"],
            target_modules=config["target_modules"],
            lora_dropout=config["lora_dropout"],
            bias="none",
            task_type="CAUSAL_LM"
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

        progress(0.3, desc="Carregando dataset...")
        training_status["log"] += f"Carregando dataset {config['dataset_id']}...\n"

        # 4. Carregar dataset (formato instrução)
        dataset = load_dataset(config["dataset_id"], split="train")
        # Se o dataset não estiver no formato esperado, aplica template
        if "messages" in dataset.column_names:
            # Formato ShareGPT/chat
            def format_chat(example):
                messages = example["messages"]
                text = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=False
                )
                return {"text": text}
            dataset = dataset.map(format_chat)
        elif "instruction" in dataset.column_names and "response" in dataset.column_names:
            # Formato Alpaca
            def format_instruction(example):
                return {"text": f"### Instruction:\n{example['instruction']}\n\n### Response:\n{example['response']}"}
            dataset = dataset.map(format_instruction)
        elif "text" not in dataset.column_names:
            raise ValueError("Dataset não possui coluna 'text', 'messages', ou 'instruction'/'response'")

        progress(0.4, desc="Preparando treino...")
        training_status["log"] += "Preparando treino...\n"

        # 5. Argumentos de treino
        training_args = TrainingArguments(
            per_device_train_batch_size=config["batch_size"],
            gradient_accumulation_steps=config["grad_accum"],
            learning_rate=config["learning_rate"],
            warmup_ratio=0.03,
            lr_scheduler_type="cosine",
            num_train_epochs=config["epochs"],
            logging_steps=10,
            save_steps=100,
            output_dir=config["output_dir"],
            report_to="none",  # Desativa wandb/tensorboard para simplicidade
            fp16=torch.cuda.is_available(),
            bf16=False,
            max_grad_norm=0.3,
        )

        # 6. Trainer
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            args=training_args,
            max_seq_length=config["max_seq_length"],
            packing=False,
        )

        # 7. Executar treino com callback de progresso
        progress(0.5, desc="Treinando...")
        training_status["log"] += "Treinando... (isso pode levar alguns minutos)\n"

        # Callback para atualizar progresso
        class ProgressCallback:
            def __init__(self, progress, status):
                self.progress = progress
                self.status = status
                self.steps = 0
                self.total_steps = None
            def on_step_end(self, args, state, control, **kwargs):
                if self.total_steps is None:
                    self.total_steps = state.max_steps
                self.steps += 1
                if self.total_steps > 0:
                    pct = 0.5 + 0.4 * (self.steps / self.total_steps)
                    self.progress(pct, desc=f"Treinando... {self.steps}/{self.total_steps}")
                    self.status["progress"] = pct

        trainer.add_callback(ProgressCallback(progress, training_status))
        trainer.train()

        # 8. Salvar adaptador
        progress(0.9, desc="Salvando adaptador...")
        training_status["log"] += "Salvando adaptador LoRA...\n"
        trainer.save_model(config["output_dir"])

        # 9. Merge opcional (não fazemos aqui, mantemos adaptador separado)
        training_status["log"] += f"✅ Treino concluído! Adaptador salvo em {config['output_dir']}\n"
        training_status["done"] = True
        training_status["running"] = False
        progress(1.0, desc="Concluído!")

    except Exception as e:
        training_status["log"] += f"❌ ERRO: {str(e)}\n"
        training_status["running"] = False
        training_status["done"] = False
        progress(1.0, desc="Erro!")
        raise e

def start_training(config, progress=gr.Progress()):
    """Inicia o treino em uma thread separada."""
    if training_status["running"]:
        return "⚠️ Já existe um treino em andamento."
    Thread(target=train_model, args=(config, progress), daemon=True).start()
    return "🚀 Treino iniciado! Acompanhe o progresso abaixo."

# ============================================================================
# FUNÇÕES DE CHAT (APÓS TREINO)
# ============================================================================
def load_finetuned_model():
    """Carrega o modelo base + adaptador LoRA para inferência."""
    base_model = AutoModelForCausalLM.from_pretrained(
        DEFAULT_CONFIG["model_id"],
        device_map="auto",
        torch_dtype=torch.bfloat16
    )
    model = PeftModel.from_pretrained(base_model, DEFAULT_CONFIG["output_dir"])
    tokenizer = AutoTokenizer.from_pretrained(DEFAULT_CONFIG["model_id"])
    return model, tokenizer

def chat(message, history):
    """Função de chat para a interface Gradio."""
    model, tokenizer = load_finetuned_model()
    messages = [{"role": "user", "content": message}]
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to("cuda")

    outputs = model.generate(
        inputs,
        max_new_tokens=512,
        temperature=0.7,
        do_sample=True,
        top_p=0.95,
        pad_token_id=tokenizer.eos_token_id
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Extrai apenas a resposta (remove o prompt)
    response = response.split("assistant")[-1].strip()
    return response

# ============================================================================
# INTERFACE GRADIO
# ============================================================================
def create_interface():
    with gr.Blocks(title="One-Click LoRA Fine-Tuning", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🧬 One-Click LoRA Fine-Tuning — O "Raygun" para LLMs
        Edite modelos de linguagem preservando sua estrutura, assim como o Raygun faz com proteínas.
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📁 Modelo & Dataset")
                model_id = gr.Textbox(
                    label="Modelo Base",
                    value=DEFAULT_CONFIG["model_id"],
                    info="ID do modelo no Hugging Face Hub"
                )
                dataset_id = gr.Textbox(
                    label="Dataset de Treino",
                    value=DEFAULT_CONFIG["dataset_id"],
                    info="ID do dataset no Hugging Face Hub"
                )

            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ LoRA Config")
                lora_r = gr.Slider(1, 64, value=DEFAULT_CONFIG["lora_r"], step=1, label="LoRA Rank (r)")
                lora_alpha = gr.Slider(1, 128, value=DEFAULT_CONFIG["lora_alpha"], step=1, label="LoRA Alpha (α)")
                lora_dropout = gr.Slider(0.0, 0.5, value=DEFAULT_CONFIG["lora_dropout"], step=0.01, label="LoRA Dropout")
                target_modules = gr.Textbox(
                    label="Target Modules (separados por vírgula)",
                    value=",".join(DEFAULT_CONFIG["target_modules"]),
                    info="Ex: q_proj,v_proj,k_proj,o_proj"
                )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 🧮 Hiperparâmetros de Treino")
                quantization = gr.Dropdown(
                    choices=["none", "4bit_nf4", "8bit"],
                    value=DEFAULT_CONFIG["quantization"],
                    label="Quantização"
                )
                batch_size = gr.Slider(1, 16, value=DEFAULT_CONFIG["batch_size"], step=1, label="Batch Size")
                grad_accum = gr.Slider(1, 32, value=DEFAULT_CONFIG["grad_accum"], step=1, label="Gradient Accumulation")
                learning_rate = gr.Number(value=DEFAULT_CONFIG["learning_rate"], label="Learning Rate")
                epochs = gr.Slider(1, 5, value=DEFAULT_CONFIG["epochs"], step=1, label="Epochs")
                max_seq_length = gr.Slider(512, 4096, value=DEFAULT_CONFIG["max_seq_length"], step=512, label="Max Sequence Length")

            with gr.Column(scale=1):
                gr.Markdown("### 🚀 Ações")
                train_btn = gr.Button("🔥 Iniciar Treino", variant="primary")
                status = gr.Textbox(label="Status", lines=4, interactive=False)
                progress_bar = gr.Slider(0, 1, value=0, label="Progresso", interactive=False)

        with gr.Row():
            with gr.Column():
                gr.Markdown("### 💬 Chat com Modelo Fine-Tunado")
                chat_interface = gr.ChatInterface(
                    fn=chat,
                    title="Chat com Modelo",
                    description="Modelo carregado após o treino. Pode demorar alguns segundos para carregar."
                )

        # Atualiza configuração com os valores da UI
        def get_config_from_ui(
            model_id, dataset_id, lora_r, lora_alpha, lora_dropout, target_modules,
            quantization, batch_size, grad_accum, learning_rate, epochs, max_seq_length
        ):
            return {
                "model_id": model_id,
                "dataset_id": dataset_id,
                "lora_r": int(lora_r),
                "lora_alpha": int(lora_alpha),
                "lora_dropout": float(lora_dropout),
                "target_modules": [m.strip() for m in target_modules.split(",") if m.strip()],
                "quantization": quantization,
                "batch_size": int(batch_size),
                "grad_accum": int(grad_accum),
                "learning_rate": float(learning_rate),
                "epochs": int(epochs),
                "max_seq_length": int(max_seq_length),
                "output_dir": DEFAULT_CONFIG["output_dir"]
            }

        # Evento do botão de treino
        train_btn.click(
            fn=start_training,
            inputs=[
                model_id, dataset_id, lora_r, lora_alpha, lora_dropout, target_modules,
                quantization, batch_size, grad_accum, learning_rate, epochs, max_seq_length
            ],
            outputs=[status]
        )

        # Atualização de progresso (simulada por enquanto)
        def update_progress():
            if training_status["running"]:
                return gr.update(value=training_status["progress"]), training_status["log"]
            elif training_status["done"]:
                return gr.update(value=1.0), training_status["log"]
            return gr.update(value=0.0), "Aguardando início..."

        # Timer para atualizar status
        demo.load(
            fn=update_progress,
            inputs=[],
            outputs=[progress_bar, status],
            every=1.0
        )

    return demo

# ============================================================================
# PONTO DE ENTRADA
# ============================================================================
if __name__ == "__main__":
    demo = create_interface()
    demo.queue()  # Para filas de requisições
    demo.launch(share=True, server_name="0.0.0.0")