#!/usr/bin/env bash

# 快速 smoke 训练脚本（单 GPU）
# 使用前确保创建虚拟环境并安装 requirements.txt

set -euo pipefail

python data/prepare_dataset.py

python training/train.py \
  --train_file data/train.jsonl \
  --eval_file data/train.jsonl \
  --model_name_or_path google/mt5-small \
  --output_dir outputs/mt5-smoke \
  --per_device_train_batch_size 4 \
  --per_device_eval_batch_size 4 \
  --num_train_epochs 2

# 评估并输出详情
python evaluate/evaluate.py --model_dir outputs/mt5-smoke --eval_file data/train.jsonl --output outputs/mt5-smoke/eval_results.jsonl
