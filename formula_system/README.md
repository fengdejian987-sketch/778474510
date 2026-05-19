# 公式生成系统文档

## 📋 目录

1. [快速开始](#快速开始)
2. [系统架构](#系统架构)
3. [文件说明](#文件说明)
4. [使用指南](#使用指南)
5. [常见问题](#常见问题)

---

## 🚀 快速开始

### 环境安装

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt
```

### 一键体验（无需GPU）

```bash
# 1. 生成示例数据
python generate_training_data.py \
  --readme_path ../README.md \
  --output example_data.jsonl

# 2. 查看生成的数据
head -5 example_data.jsonl

# 3. 测试评估脚本
python eval_metrics.py \
  --predictions example_test_cases.jsonl \
  --output eval_report.json
```

### 完整训练流程（需GPU）

```bash
# Step 1: 准备数据
python generate_training_data.py \
  --readme_path ../README.md \
  --output data_train.jsonl \
  --split

# Step 2: 训练模型（单GPU）
CUDA_VISIBLE_DEVICES=0 python train_improved.py \
  --train_file data_train_train.jsonl \
  --eval_file data_train_valid.jsonl \
  --model_name_or_path google/mt5-small \
  --output_dir ./formula-model-mt5 \
  --num_train_epochs 3

# Step 3: 推理生成
python inference_batch.py \
  --model_dir ./formula-model-mt5 \
  --input "写出牛顿第二定律"

# Step 4: 批量推理和评估
python inference_batch.py \
  --model_dir ./formula-model-mt5 \
  --batch_file example_test_cases.jsonl \
  --output predictions.jsonl

python eval_metrics.py \
  --predictions predictions.jsonl \
  --output eval_report.json
```

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│                README文档库                          │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  generate_training_data.py                          │
│  - 提取标题                                          │
│  - 匹配公式库                                        │
│  - 数据增强（中英文）                                │
│  - 生成JSONL训练数据                                 │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  训练数据 (data_train.jsonl)                         │
│  格式: {"input":"中文描述","target":"LaTeX"}        │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  train_improved.py                                  │
│  - 加载mT5预训练模型                                 │
│  - Seq2Seq微调                                       │
│  - 支持单GPU/多GPU                                   │
│  - 自动保存checkpoint                               │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  微调模型 (formula-model-mt5/)                       │
│  - model.safetensors                                │
│  - tokenizer.model                                  │
│  - config.json                                      │
└─────────────────┬──────���────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  inference_batch.py                                 │
│  - 单个/批量推理                                     │
│  - Beam search解码                                   │
│  - 保存预测结果                                      │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  预测结果 (predictions.jsonl)                        │
│  格式: {"input":"...","prediction":"..."}           │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  eval_metrics.py                                    │
│  - BLEU-1/2/4分数                                    │
│  - Token重叠率                                       │
│  - LaTeX结构相似度                                   │
│  - 编辑距离                                          │
│  - 精确匹配率                                        │
└─────────────────┬───────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────┐
│  评估报告 (eval_report.json)                         │
└─────────────────────────────────────────────────────┘
```

---

## 📁 文件说明

### 核心脚本

| 文件 | 功能 | 输入 | 输出 |
|-----|------|------|------|
| **generate_training_data.py** | 生成训练数据 | README.md | JSONL数据集 |
| **train_improved.py** | 模型微调 | JSONL数据 | 微调模型 |
| **inference_batch.py** | 推理生成 | 模型+文本 | 预测结果 |
| **eval_metrics.py** | 质量评估 | 预测+参考 | 评估报告 |

### 数据文件

| 文件 | 说明 |
|-----|------|
| **requirements.txt** | Python依赖包 |
| **example_test_cases.jsonl** | 示例测试数据（10条） |
| **data_train.jsonl** | 生成的训练数据 |
| **data_train_train.jsonl** | 训练集（分割后） |
| **data_train_valid.jsonl** | 验证集（分割后） |

---

## 📖 使用指南

### 1️⃣ 生成训练数据

```bash
python generate_training_data.py \
  --readme_path ../README.md \
  --output data_train.jsonl \
  --split
```

**参数说明:**
- `--readme_path`: README文件路径
- `--output`: 输出文件名
- `--split`: 是否自动分割为训练/验证集

**输出示例:**
```
✓ 提取到 120 个唯一标题
✓ 已生成 480 个训练样本到 data_train.jsonl
✓ 训练集: 384 样本 -> data_train_train.jsonl
✓ 验证集: 96 样本 -> data_train_valid.jsonl
```

### 2️⃣ 训练模型

```bash
# 单GPU
CUDA_VISIBLE_DEVICES=0 python train_improved.py \
  --train_file data_train_train.jsonl \
  --eval_file data_train_valid.jsonl \
  --model_name_or_path google/mt5-small \
  --output_dir ./formula-model \
  --num_train_epochs 3

# 多GPU（需要torchrun）
torchrun --nproc_per_node 4 train_improved.py \
  --train_file data_train_train.jsonl \
  --eval_file data_train_valid.jsonl \
  --output_dir ./formula-model \
  --per_device_train_batch_size 4  # 减半以适应内存
```

**训练参数:**
- `--model_name_or_path`: 预训练模型
  - `google/mt5-small` ✅ 推荐（3.7B参数）
  - `google/mt5-base` （580M参数）
  - `google/t5-small` （60M参数）
- `--num_train_epochs`: 训练轮数（3-5推荐）
- `--learning_rate`: 学习率（默认5e-5）
- `--per_device_train_batch_size`: 批大小（GPU显存允许范围）
- `--fp16`: 是否使用半精度加速

**训练耗时估计:**
- mT5-small: ~1-2小时（单GPU，总数据）
- 受数据量和硬件影响

### 3️⃣ 推理生成公式

```bash
# 单个推理
python inference_batch.py \
  --model_dir ./formula-model \
  --input "写出牛顿第二定律"

# 批量推理
python inference_batch.py \
  --model_dir ./formula-model \
  --batch_file example_test_cases.jsonl \
  --output predictions.jsonl \
  --batch_size 16
```

**推理参数:**
- `--model_dir`: 微调模型目录
- `--input`: 单个输入文本
- `--batch_file`: 批量输入文件（JSONL）
- `--output`: 输出文件
- `--max_length`: 最大生成长度（默认128）
- `--num_beams`: Beam search宽度（默认4）
- `--batch_size`: 推理批大小

**输出示例:**
```
输入: 写出牛顿第二定律
输出: F = m a
```

### 4️⃣ 评估质量

```bash
python eval_metrics.py \
  --predictions predictions.jsonl \
  --references example_test_cases.jsonl \
  --output eval_report.json
```

**评估指标:**
- **BLEU-1/2/4**: 标准机器翻译指标
- **精确匹配率**: 完全相同的比例
- **Token重叠率**: 词汇重叠百分比
- **LaTeX结构相似度**: 结构命令相似度
- **编辑距离**: 字符级相似度

**输出示例:**
```
精确匹配率:     0.4000
BLEU-1:         0.7234
BLEU-2:         0.5123
BLEU-4:         0.2891
Token重叠率:    0.6543
LaTeX结构相似度: 0.8234
```

---

## 💡 公式库管理

### 添加新公式

编辑 `generate_training_data.py` 中的 `PHYSICS_FORMULA_DATABASE`:

```python
PHYSICS_FORMULA_DATABASE = {
    "新公式名称": {
        "formulas": [
            "LaTeX形式1",
            "LaTeX形式2"
        ],
        "category": "类别名称",
        "keywords": ["关键词1", "关键词2"]
    },
    ...
}
```

### 支���的类别

- ✅ 运动学 (kinematics)
- ✅ 万有引力 (gravitation)
- ✅ 能量 (energy)
- ✅ 相对论 (relativity)
- ✅ 电磁学 (electromagnetism)
- ✅ 热力学 (thermodynamics)
- ✅ 波动 (waves)
- ✅ 光学 (optics)
- ✅ 量子物理 (quantum)
- ✅ 宇宙学 (cosmology)

---

## ❓ 常见问题

### Q1: 没有GPU怎么办？

A: 可以使用更小的模型或CPU推理（较慢）：

```bash
# 使用最小模型
python train_improved.py \
  --model_name_or_path google/mt5-small \
  --per_device_train_batch_size 2  # 减少批大小

# CPU推理
python inference_batch.py \
  --model_dir ./formula-model \
  --device cpu
```

### Q2: 如何改进模型性能？

A:
1. **增加数据**: 生成更多高质量的README标题
2. **调整参数**:
   - 增加 `--num_train_epochs`（5-10）
   - 降低 `--learning_rate`（2e-5）
   - 增加 `--warmup_steps`（1000）
3. **使用更大模型**: 换成 `google/mt5-base`
4. **数据质量**: 手动修正生成的不准确样本

### Q3: 内存不足怎么办？

A:
```bash
# 减少批大小
--per_device_train_batch_size 4

# 启用梯度检查点
--gradient_checkpointing True

# 启用半精度
--fp16

# 使用梯度累积
--gradient_accumulation_steps 2
```

### Q4: 如何保存最优模型？

A: 训练脚本自动保存最优checkpoint：
```bash
--save_total_limit 3  # 只保留最近3个
--save_strategy epoch  # 每个epoch保存
```

### Q5: 推理速度如何提升？

A:
```bash
# 减少beam search宽度
--num_beams 2

# 批量处理
--batch_size 32
```

---

## 🔗 参考资源

- [Hugging Face Transformers](https://huggingface.co/transformers/)
- [mT5 模型](https://huggingface.co/google/mt5-small)
- [BLEU评分](https://en.wikipedia.org/wiki/BLEU)
- [Seq2Seq训练](https://huggingface.co/course/chapter6/)

---

## 📝 许可证

MIT License

---

**更新日期**: 2026-05-19
**版本**: 1.0
