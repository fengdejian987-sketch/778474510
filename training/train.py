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
import multiprocessing

import evaluate
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
    parser.add_argument("--num_proc", type=int, default=0, help="num_proc for datasets.map; 0 -> auto")
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

    # determine num_proc
    if args.num_proc and args.num_proc > 0:
        num_proc = args.num_proc
    else:
        try:
            cpu_count = multiprocessing.cpu_count()
            num_proc = max(1, min(4, cpu_count - 1))
        except Exception:
            num_proc = 1

    # batched preprocessing to speed up tokenization
    def preprocess_batch(batch):
        # detect input & target column names
        if "description" in batch:
            srcs = batch["description"]
        elif "input" in batch:
            srcs = batch["input"]
        else:
            # fallback: take first key
            key = next(iter(batch.keys()))
            srcs = batch[key]

        tgt_key = None
        for k in ("formula", "target", "canonical_formula"):
            if k in batch:
                tgt_key = k
                break

        targets = batch[tgt_key] if tgt_key else [""] * len(srcs)
        sources = [("<FORMULA> " + (s or "").strip() + " </FORMULA>") for s in srcs]

        model_inputs = tokenizer(sources, max_length=args.max_source_length, truncation=True, padding=False)
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(targets, max_length=args.max_target_length, truncation=True, padding=False)
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    # map with batching & parallelism; remove original columns to keep dataset small
    remove_cols = ds["train"].column_names if "train" in ds else None
    tokenized = ds.map(preprocess_batch, batched=True, num_proc=num_proc, remove_columns=remove_cols)

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        evaluation_strategy="epoch" if "validation" in tokenized else "no",
        save_strategy="epoch",
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        predict_with_generate=True,
        generation_max_length=args.max_target_length,
        generation_num_beams=4,
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
        # determine pad token id with safe fallback
        pad_token_id = tokenizer.pad_token_id
        if pad_token_id is None:
            pad_token_id = getattr(tokenizer, 'eos_token_id', None) or getattr(tokenizer, 'unk_token_id', None)
            if pad_token_id is None:
                # try to derive from token strings
                try:
                    pad_token = tokenizer.pad_token or tokenizer.eos_token or tokenizer.unk_token
                    pad_token_id = tokenizer.convert_tokens_to_ids(pad_token) if pad_token else 0
                except Exception:
                    pad_token_id = 0
        # replace -100 in labels as tokenizer.pad_token_id
        labels = [[(l if l != -100 else pad_token_id) for l in label] for label in labels]
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

    # run a post-evaluation script if eval dataset exists (call in-process, batched)
    if "validation" in tokenized:
        post_eval_path = Path(args.output_dir) / "post_eval_results.json"
        logger.info("Running post-eval (detailed) -> %s", post_eval_path)
        # call evaluate function inside repo (avoid spawning new process)
        try:
            from evaluate.evaluate import evaluate_model
            evaluate_model(args.output_dir, args.eval_file, str(post_eval_path), max_length=args.max_target_length, batch_size=args.per_device_eval_batch_size)
        except Exception as e:
            logger.exception("Post-eval failed: %s", e)


if __name__ == '__main__':
    main()
