import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from torch.utils.data import DataLoader, Dataset

class FormulaDataset(Dataset):
    """公式生成数据集"""
    def __init__(self, descriptions, formulas, tokenizer, max_length=512):
        self.descriptions = descriptions
        self.formulas = formulas
        self.tokenizer = tokenizer
        self.max_length = max_length
    def __len__(self):
        return len(self.descriptions)
    def __getitem__(self, idx):
        desc = self.descriptions[idx]
        formula = self.formulas[idx]
        inputs = self.tokenizer(desc, max_length=self.max_length, padding='max_length', truncation=True, return_tensors='pt')
        targets = self.tokenizer(formula, max_length=self.max_length, padding='max_length', truncation=True, return_tensors='pt')
        return {
            'input_ids': inputs['input_ids'].squeeze(),
            'attention_mask': inputs['attention_mask'].squeeze(),
            'labels': targets['input_ids'].squeeze()
        }

class FormulaSeq2SeqModel:
    def __init__(self, model_name='google/mt5-base'):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    def train(self, train_loader, epochs=3, lr=5e-5):
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(device)
        for epoch in range(epochs):
            total_loss = 0
            for batch in train_loader:
                optimizer.zero_grad()
                outputs = self.model(input_ids=batch['input_ids'].to(device), attention_mask=batch['attention_mask'].to(device), labels=batch['labels'].to(device))
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_loader):.4f}")
    def generate(self, description: str, max_length=128) -> str:
        input_ids = self.tokenizer.encode(description, return_tensors='pt')
        outputs = self.model.generate(input_ids, max_length=max_length, num_beams=4)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
