#!/usr/bin/env bash

# Run training with accelerate (requires `accelerate` config to be set up)
set -euo pipefail

accelerate launch training/train_accelerate.py \
  --train_file data/train.jsonl \
  --eval_file data/train.jsonl \
  --model_name_or_path google/mt5-small \
  --output_dir outputs/mt5-accel \
  --per_device_train_batch_size 4 \
  --per_device_eval_batch_size 4 \
  --num_train_epochs 3 \
  --deepspeed_config configs/deepspeed_config.json
