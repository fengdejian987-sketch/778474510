#!/usr/bin/env python3
"""
ML 模型训练脚本 - Seq2Seq 公式生成模型
需要 GPU 支持
"""

import os
import json
import torch
from pathlib import Path
from typing import List, Dict, Optional
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer, AutoModelForSeq2SeqLM,
    Trainer, TrainingArguments, Seq2SeqTrainingArguments
)
import logging

logger = logging.getLogger(__name__)


class FormulaDataset(Dataset):
    """公式生成数据集"""
    
    def __init__(
        self,
        descriptions: List[str],
        formulas: List[str],
        tokenizer,
        max_input_length: int = 256,
        max_target_length: int = 128
    ):
        self.descriptions = descriptions
        self.formulas = formulas
        self.tokenizer = tokenizer
        self.max_input_length = max_input_length
        self.max_target_length = max_target_length
    
    def __len__(self) -> int:
        return len(self.descriptions)
    
    def __getitem__(self, idx: int) -> Dict:
        description = self.descriptions[idx]
        formula = self.formulas[idx]
        
        # 编码输入
        inputs = self.tokenizer(
            description,
            max_length=self.max_input_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        # 编码目标
        with self.tokenizer.as_target_tokenizer():
            targets = self.tokenizer(
                formula,
                max_length=self.max_target_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
        
        return {
            'input_ids': inputs['input_ids'].squeeze(),
            'attention_mask': inputs['attention_mask'].squeeze(),
            'labels': targets['input_ids'].squeeze(),
            'decoder_attention_mask': targets['attention_mask'].squeeze()
        }


class FormulaSeq2SeqModel:
    """公式生成 Seq2Seq 模型包装器"""
    
    def __init__(
        self,
        model_name: str = "google/mt5-base",
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        self.model_name = model_name
        self.device = device
        
        # 加载分词器
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # 加载预训练模型
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.model.to(device)
        
        logger.info(f"Loaded model: {model_name} on device: {device}")
    
    def prepare_data(
        self,
        descriptions: List[str],
        formulas: List[str],
        batch_size: int = 16,
        shuffle: bool = True
    ) -> DataLoader:
        """特备数据集"""
        dataset = FormulaDataset(
            descriptions=descriptions,
            formulas=formulas,
            tokenizer=self.tokenizer
        )
        
        return DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle
        )
    
    def train(
        self,
        train_loader: DataLoader,
        eval_loader: Optional[DataLoader] = None,
        epochs: int = 3,
        learning_rate: float = 5e-5,
        output_dir: str = "./formula_model"
    ):
        """训练模型"""
        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=learning_rate
        )
        
        # 训练循环
        for epoch in range(epochs):
            self.model.train()
            total_loss = 0
            
            for batch_idx, batch in enumerate(train_loader):
                # 加载数据到设备
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                # 前向传递
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                
                loss = outputs.loss
                
                # 反向传递
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
                
                if batch_idx % 10 == 0:
                    logger.info(
                        f"Epoch {epoch+1}/{epochs}, "
                        f"Batch {batch_idx}/{len(train_loader)}, "
                        f"Loss: {loss.item():.4f}"
                    )
            
            avg_loss = total_loss / len(train_loader)
            logger.info(f"Epoch {epoch+1} completed. Average loss: {avg_loss:.4f}")
        
        # 保存模型
        self.save(output_dir)
        logger.info(f"Model saved to {output_dir}")
    
    def generate(
        self,
        description: str,
        max_length: int = 128,
        num_beams: int = 4,
        temperature: float = 1.0
    ) -> str:
        """使用模型生成公式"""
        # 编码输入
        inputs = self.tokenizer(
            description,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=256
        ).to(self.device)
        
        # 生成
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=inputs['input_ids'],
                attention_mask=inputs['attention_mask'],
                max_length=max_length,
                num_beams=num_beams,
                temperature=temperature,
                do_sample=temperature > 1.0,
                early_stopping=True
            )
        
        # 解码输出
        formula = self.tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        )
        
        return formula
    
    def batch_generate(
        self,
        descriptions: List[str],
        batch_size: int = 32
    ) -> List[str]:
        """批��生成公式"""
        formulas = []
        
        for i in range(0, len(descriptions), batch_size):
            batch = descriptions[i:i+batch_size]
            
            # 编码批量
            inputs = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=256
            ).to(self.device)
            
            # 生成
            with torch.no_grad():
                outputs = self.model.generate(
                    input_ids=inputs['input_ids'],
                    attention_mask=inputs['attention_mask'],
                    max_length=128,
                    num_beams=4
                )
            
            # 解码
            batch_formulas = [
                self.tokenizer.decode(output, skip_special_tokens=True)
                for output in outputs
            ]
            
            formulas.extend(batch_formulas)
        
        return formulas
    
    def save(self, output_dir: str):
        """保存模型"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        # 保存配置
        config = {
            'model_name': self.model_name,
            'device': str(self.device)
        }
        
        with open(os.path.join(output_dir, 'config.json'), 'w') as f:
            json.dump(config, f, indent=2)
    
    @classmethod
    def load(cls, model_dir: str):
        """加载保存的模型"""
        with open(os.path.join(model_dir, 'config.json'), 'r') as f:
            config = json.load(f)
        
        model = cls(model_name=config['model_name'])
        model.model = AutoModelForSeq2SeqLM.from_pretrained(model_dir)
        model.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        
        logger.info(f"Loaded model from {model_dir}")
        return model


def generate_training_data() -> tuple:
    """生成示例训练数据"""
    descriptions = [
        "质量与能量的换算",
        "物体受力形成的加速度",
        "常正幻按加速度下的速度变化",
        "常正幻按加速度下的位移",
        "有效批需的功率",
        "氧化物的密度计算",
        "波的基本关系式",
        "标准氧化此类氻汽溜墜方程",
        "理想气体状态方程",
        "库他冇正电路及电阻关系"
    ]
    
    formulas = [
        "E = m*c**2",
        "F = m*a",
        "v = u + a*t",
        "x = u*t + 0.5*a*t**2",
        "P = E/t",
        "rho = m/V",
        "v = f*lambda",
        "PV = nRT",
        "PV = nRT",
        "U = I*R"
    ]
    
    return descriptions, formulas


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建模型
    model = FormulaSeq2SeqModel(model_name="google/mt5-small")
    
    # 特备数据
    descriptions, formulas = generate_training_data()
    train_loader = model.prepare_data(
        descriptions=descriptions * 10,  # 扩展数据
        formulas=formulas * 10,
        batch_size=4
    )
    
    # 训练模型
    logger.info("Starting training...")
    model.train(
        train_loader=train_loader,
        epochs=2,
        output_dir="./models/formula_seq2seq"
    )
    
    # 测试推理
    logger.info("Testing inference...")
    test_description = "质量与能量的换算"
    result = model.generate(test_description)
    logger.info(f"Input: {test_description}")
    logger.info(f"Output: {result}")
