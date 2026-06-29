import torch
from torch.utils.data import Dataset
import pandas as pd
import json

class RequirementPairsDataset(Dataset):
    def __init__(self, json_file: str, tokenizer, max_length=128):
        
        # Load JSON file
        with open(json_file, 'r') as f:
            self.data = json.load(f)

        # Validate keys
        if not all(key in entry for entry in self.data for key in ["Number", "Requirement1", "Requirement2", "Label"]):
            raise ValueError(f"JSON file must contain keys: 'Number', 'Requirement1', 'Requirement2', 'Label'")
        
        # Create a DataFrame for easy manipulation
        self.df = pd.DataFrame(self.data)

        # Validate column names
        self.req1_col = 'Requirement1'
        self.req2_col = 'Requirement2'
        self.label_col = 'Label'

        # Map string labels to integers
        self.label_mapping = {"Duplicate": 0, "Conflict": 1, "Neutral": 2}

        # Convert labels
        self.df['label_num'] = self.df[self.label_col].map(self.label_mapping)

        # Check for invalid labels
        if self.df['label_num'].isna().any():
            invalid_labels = self.df[self.df['label_num'].isna()][self.label_col].unique()
            raise ValueError(f"Invalid labels found: {invalid_labels}. Must be: {list(self.label_mapping.keys())}")
        
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        print(f"Loaded {len(self.df)} samples from JSON")
        print(f"Using columns: {self.req1_col}, {self.req2_col}, {self.label_col}")
        
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        req1 = str(row[self.req1_col])
        req2 = str(row[self.req2_col])
        label = int(row['label_num'])
        
        # Tokenize both requirements
        enc1 = self.tokenizer(
            req1.lower(),
            padding='max_length',
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )
        
        enc2 = self.tokenizer(
            req2.lower(),
            padding='max_length',
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )
        
        return {
            'input_ids1': enc1['input_ids'].squeeze(0),
            'attention_mask1': enc1['attention_mask'].squeeze(0),
            'input_ids2': enc2['input_ids'].squeeze(0),
            'attention_mask2': enc2['attention_mask'].squeeze(0),
            'labels': torch.tensor(label, dtype=torch.long)
        }
    
    def get_label_distribution(self):
        """Get distribution of labels in the dataset"""
        return self.df[self.label_col].value_counts()
