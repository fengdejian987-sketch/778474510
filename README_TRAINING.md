训练与评估说明

主要文件：
- training/train.py : 使用 Hugging Face Trainer 的训练入���
- data/prepare_dataset.py : 生成合成训练数据（POC 用）
- evaluate/evaluate.py : 生成后处理评估：sympy parse + DimensionValidator
- scripts/run_smoke_train.sh : 一键本地 smoke-test 脚本

快速开始（本地单机）
1) 创建虚拟环境并安装依赖：
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2) 运行 smoke 训练：
   bash scripts/run_smoke_train.sh

3) 查看评估结果：
   outputs/mt5-smoke/eval_results.jsonl

工程建议：
- 将数据替换为真实标注数据（canonical_formula）后放大训练样本
- 在训练前先用 tokenizer.add_tokens 增加特殊 token，并确保数据标准化
- 用 HF Trainer 的分布式/accelerate/混合精度来放大训练
