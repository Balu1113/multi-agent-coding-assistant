"""Fine-tuning pipeline for customizing models on coding workflows.

Supports PEFT/LoRA for efficient fine-tuning of code LLMs.
"""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)


class TrainingExample(BaseModel):
    instruction: str
    input: str = ""
    output: str


class FineTuningConfig(BaseModel):
    base_model: str = "codellama/CodeLlama-7b-hf"
    output_dir: str = "./models/fine-tuned"
    num_epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-4
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    max_seq_length: int = 2048


class FineTuner:
    def __init__(self, config: FineTuningConfig | None = None) -> None:
        self.config = config or FineTuningConfig()

    async def prepare_dataset(self, examples: list[TrainingExample]) -> str:
        dataset_path = Path(tempfile.mkdtemp()) / "training_data.jsonl"
        with open(dataset_path, "w", encoding="utf-8") as f:
            for ex in examples:
                record = {
                    "instruction": ex.instruction,
                    "input": ex.input,
                    "output": ex.output,
                }
                f.write(json.dumps(record) + "\n")
        logger.info("Prepared %d training examples at %s", len(examples), dataset_path)
        return str(dataset_path)

    async def train(self, dataset_path: str) -> str:
        """
        Fine-tune the model using PEFT/LoRA.
        Falls back to simulated training if torch/transformers not available.
        """
        try:
            return await self._train_real(dataset_path)
        except ImportError as exc:
            logger.warning("Training dependencies not available (%s), using simulation", exc)
            return await self._train_simulated(dataset_path)

    async def _train_real(self, dataset_path: str) -> str:
        import torch
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            Trainer,
            DataCollatorForLanguageModeling,
        )
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, TaskType

        model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        tokenizer = AutoTokenizer.from_pretrained(self.config.base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            target_modules=["q_proj", "v_proj"],
        )
        model = get_peft_model(model, lora_config)

        dataset = load_dataset("json", data_files=dataset_path, split="train")

        def tokenize_fn(examples):
            texts = [
                f"### Instruction:\n{instr}\n### Input:\n{inp}\n### Output:\n{out}"
                for instr, inp, out in zip(
                    examples["instruction"], examples["input"], examples["output"]
                )
            ]
            return tokenizer(
                texts,
                truncation=True,
                padding="max_length",
                max_length=self.config.max_seq_length,
            )

        tokenized = dataset.map(tokenize_fn, batched=True, remove_columns=dataset.column_names)

        args = TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_epochs,
            per_device_train_batch_size=self.config.batch_size,
            learning_rate=self.config.learning_rate,
            logging_steps=10,
            save_strategy="epoch",
            report_to="none",
        )

        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=tokenized,
            data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
        )

        trainer.train()
        trainer.save_model(self.config.output_dir)
        logger.info("Fine-tuning complete, model saved to %s", self.config.output_dir)
        return self.config.output_dir

    async def _train_simulated(self, dataset_path: str) -> str:
        output = Path(self.config.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "adapter_config.json").write_text(
            json.dumps(self.config.model_dump(), indent=2)
        )
        (output / "training_complete.txt").write_text(
            f"Simulated training complete.\n"
            f"Base model: {self.config.base_model}\n"
            f"Dataset: {dataset_path}\n"
            f"Epochs: {self.config.num_epochs}\n"
        )
        logger.info("Simulated fine-tuning complete at %s", output)
        return str(output)
