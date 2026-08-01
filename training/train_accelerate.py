"""Accelerate-friendly training entry using Hugging Face Trainer.

Usage (with accelerate):
  accelerate launch training/train_accelerate.py \
    --train_file data/train.jsonl \
    --eval_file data/valid.jsonl \
    --model_name_or_path google/mt5-small \
    --output_dir outputs/mt5-accel \
    --per_device_train_batch_size 4 \
    --per_device_eval_batch_size 4 \
    --num_train_epochs 3 \
    --deepspeed_config configs/deepspeed_config.json

Notes:
- This script is compatible with accelerate/deepspeed when launched through `accelerate launch`.
- It still uses Seq2SeqTrainer for convenience and compatibility with HF tooling.
"""

import argparse
import logging
import os
from pathlib import Path

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoConfig,
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SPECIAL_TOKENS = ["<FORMULA>", "</FORMULA>"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_file", type=str, required=True)
    parser.add_argument("--eval_file", type=str, required=False)
    parser.add_argument("--model_name_or_path", type=str, default="google/mt5-small")
    parser.add_argument("--output_dir", type=str, default="outputs/mt5-accel")
    parser.add_argument("--per_device_train_batch_size", type=int, default=4)
    parser.add_argument("--per_device_eval_batch_size", type=int, default=4)
    parser.add_argument("--num_train_epochs", type=int, default=3)
    parser.add_argument("--learning_rate", type=float, default=5e-5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max_source_length", type=int, default=128)
    parser.add_argument("--max_target_length", type=int, default=128)
    parser.add_argument("--deepspeed_config", type=str, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    logger.info("Loading tokenizer and model: %s", args.model_name_or_path)
    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path)
    config = AutoConfig.from_pretrained(args.model_name_or_path)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model_name_or_path, config=config)

    # add special tokens if not present
    added = tokenizer.add_tokens(SPECIAL_TOKENS)
    if added:
        model.resize_token_embeddings(len(tokenizer))
        logger.info("Added %d special tokens", added)

    data_files = {"train": args.train_file}
    if args.eval_file:
        data_files["validation"] = args.eval_file
    ds = load_dataset("json", data_files=data_files)

    def preprocess_sample(ex):
        source = ex.get("description") or ex.get("input")
        target = ex.get("formula") or ex.get("target") or ex.get("canonical_formula")
        if source is None or target is None:
            return {}
        source = "<FORMULA> " + source.strip() + " </FORMULA>"
        model_inputs = tokenizer(source, max_length=args.max_source_length, truncation=True)
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(target, max_length=args.max_target_length, truncation=True)
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    tokenized = ds.map(lambda ex: preprocess_sample(ex), batched=False)

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        evaluation_strategy="epoch" if "validation" in tokenized else "no",
        save_strategy="epoch",
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        predict_with_generate=True,
        fp16=True,
        num_train_epochs=args.num_train_epochs,
        learning_rate=args.learning_rate,
        save_total_limit=3,
        logging_dir=os.path.join(args.output_dir, "logs"),
        load_best_model_at_end=True if "validation" in tokenized else False,
        metric_for_best_model="bleu",
        # enable deepspeed if provided
        deepspeed=args.deepspeed_config if args.deepspeed_config else None,
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized.get("validation"),
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)


if __name__ == '__main__':
    main()
