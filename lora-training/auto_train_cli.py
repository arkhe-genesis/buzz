from autotrain import Trainer
trainer = Trainer(
    model="meta-llama/Llama-3.2-3B-Instruct",
    dataset="argilla/distilabel-capybara-dpo-7k-binarized",
    task="causal_lm",
    lora_r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    batch_size=2,
    gradient_accumulation=8,
    learning_rate=2e-4,
    num_train_epochs=1,
    quantization="4bit",
    output_dir="./lora_adapter"
)
trainer.train()