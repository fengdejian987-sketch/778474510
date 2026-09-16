import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from torch.utils.data import DataLoader, Dataset

class FormulaDataset(Dataset):
    """公式生成数据集：store raw texts and tokenize in collate_fn"""
    def __init__(self, descriptions, formulas):
        self.descriptions = descriptions
        self.formulas = formulas

    def __len__(self):
        return len(self.descriptions)

    def __getitem__(self, idx):
        return {"description": self.descriptions[idx], "formula": self.formulas[idx]}

def make_collate_fn(tokenizer, max_source_length=512, max_target_length=512):
    def collate_fn(batch):
        sources = [("<FORMULA> " + (b["description"] or "").strip() + " </FORMULA>") for b in batch]
        targets = [b["formula"] or "" for b in batch]
        inputs = tokenizer(sources, max_length=max_source_length, padding=True, truncation=True, return_tensors='pt')
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(targets, max_length=max_target_length, padding=True, truncation=True, return_tensors='pt')
        inputs["labels"] = labels["input_ids"]
        return inputs
    return collate_fn

class FormulaSeq2SeqModel:
    def __init__(self, model_name='google/mt5-base'):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    def train(self, train_dataset: Dataset, epochs=3, lr=5e-5, batch_size=8, num_workers=4):
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(device)

        collate_fn = make_collate_fn(self.tokenizer)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True, collate_fn=collate_fn)

        scaler = torch.cuda.amp.GradScaler(enabled=torch.cuda.is_available())
        for epoch in range(epochs):
            total_loss = 0.0
            self.model.train()
            for batch in train_loader:
                optimizer.zero_grad()
                # move batch tensors to device
                batch = {k: v.to(device) for k, v in batch.items()}
                with torch.cuda.amp.autocast(enabled=torch.cuda.is_available()):
                    outputs = self.model(input_ids=batch['input_ids'], attention_mask=batch['attention_mask'], labels=batch['labels'])
                    loss = outputs.loss
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
                total_loss += loss.item()
            print(f"Epoch {epoch+1}, Loss: {total_loss/len(train_loader):.4f}")

    def generate(self, description: str, max_length=128) -> str:
        input_ids = self.tokenizer.encode(description, return_tensors='pt')
        outputs = self.model.generate(input_ids, max_length=max_length, num_beams=4)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
