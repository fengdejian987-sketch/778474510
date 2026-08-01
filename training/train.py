"""训练入口：使用 Hugging Face Transformers 的 Seq2Seq Trainer

功能：
- 从 JSONL 数据集加载（datasets 库）
- 支持 tokenizer 扩展 special tokens
- 使用 DataCollatorForSeq2Seq, Seq2SeqTrainer
- 保存 checkpoint 与推理输出

示例：
python training/train.py \
  --train_file data/train.jsonl \
  --eval_file data/valid.jsonl \
  --model_name_or_path google/mt5-small \
  --output_dir outputs/mt5-smoke \
  --per_device_train_batch_size 8 \
  --per_device_eval_batch_size 8 \
  --num_train_epochs 3

"""

import argparse
import logging
import os
import json
from pathlib import Path

import evaluate
from datasets import load_dataset, load_metric
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

BLEU = evaluate.load("sacrebleu")

SPECIAL_TOKENS = ["<FORMULA>", "</FORMULA>"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_file", type=str, required=True)
    parser.add_argument("--eval_file", type=str, required=False)
    parser.add_argument("--model_name_or_path", type=str, default="google/mt5-small")
    parser.add_argument("--output_dir", type=str, default="outputs/mt5-smoke")
    parser.add_argument("--per_device_train_batch_size", type=int, default=8)
    parser.add_argument("--per_device_eval_batch_size", type=int, default=8)
    parser.add_argument("--num_train_epochs", type=int, default=3)
    parser.add_argument("--learning_rate", type=float, default=5e-5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max_source_length", type=int, default=128)
    parser.add_argument("--max_target_length", type=int, default=128)
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

    # load datasets
    data_files = {"train": args.train_file}
    if args.eval_file:
        data_files["validation"] = args.eval_file
    ds = load_dataset("json", data_files=data_files)

    # preprocess
    def preprocess_sample(ex):
        # input: description; target: canonical_formula
        source = ex.get("description") or ex.get("input")
        target = ex.get("formula") or ex.get("target") or ex.get("canonical_formula")
        if source is None or target is None:
            return {"input_ids": [], "labels": []}
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
    )

    def compute_metrics(eval_preds):
        preds, labels = eval_preds
        if isinstance(preds, tuple):
            preds = preds[0]
        decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
        # replace -100 in labels as tokenizer.pad_token_id
        labels = [[(l if l != -100 else tokenizer.pad_token_id) for l in label] for label in labels]
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
        # sacrebleu expects list of references per prediction
        decoded_labels_refs = [[l] for l in decoded_labels]
        bleu = BLEU.compute(predictions=decoded_preds, references=decoded_labels_refs)
        return {"bleu": bleu["score"]}

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized.get("validation"),
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(args.output_dir)

    # save tokenizer
    tokenizer.save_pretrained(args.output_dir)

    # run a post-evaluation script if eval dataset exists
    if "validation" in tokenized:
        post_eval_path = Path(args.output_dir) / "post_eval_results.json"
        logger.info("Running post-eval (detailed) -> %s", post_eval_path)
        # call evaluate script (in same repo)
        os.system(f"python evaluate/evaluate.py --model_dir {args.output_dir} --eval_file {args.eval_file} --output {post_eval_path}")


if __name__ == '__main__':
    main()
