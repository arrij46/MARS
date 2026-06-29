

import torch
import torch.nn as nn

class SiameseBERT(nn.Module):
    def __init__(self, bert_model, num_classes=3, dropout_rate=0.3, pooling_strategy='mean'):
        super().__init__()
        
        self.bert = bert_model
        self.hidden_size = self.bert.config.hidden_size
        self.pooling_strategy = pooling_strategy
        
        # Feature dimension after concatenation
        # [emb1, emb2, abs_diff, element_wise_mult]
        feature_dim = self.hidden_size * 4
        
        # Enhanced multi-classification head with residual connections
        self.fc1 = nn.Linear(feature_dim, 512)
        self.bn1 = nn.BatchNorm1d(512)
        self.dropout1 = nn.Dropout(dropout_rate)
        
        self.fc2 = nn.Linear(512, 256)
        self.bn2 = nn.BatchNorm1d(256)
        self.dropout2 = nn.Dropout(dropout_rate)
        
        self.fc3 = nn.Linear(256, 128)
        self.bn3 = nn.BatchNorm1d(128)
        self.dropout3 = nn.Dropout(dropout_rate)
        
        self.classifier = nn.Linear(128, num_classes)
        
        # Attention mechanism for weighted pooling
        self.attention = nn.Sequential(
            nn.Linear(self.hidden_size, 1),
            nn.Tanh()
        )
        
        self._init_weights()
        
    def _init_weights(self):
        """Initialize weights with better initialization"""
        for module in [self.fc1, self.fc2, self.fc3, self.classifier]:
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, mode='fan_out', nonlinearity='relu')
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0)
        
        # Initialize attention weights
        for module in self.attention:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def attention_pooling(self, hidden_states, attention_mask):
        """Apply attention-based pooling"""
        # hidden_states: [batch_size, seq_len, hidden_size]
        # attention_mask: [batch_size, seq_len]
        
        # Compute attention scores
        attention_scores = self.attention(hidden_states).squeeze(-1)  # [batch_size, seq_len]
        
        # Mask padded tokens
        attention_scores = attention_scores.masked_fill(attention_mask == 0, -1e9)
        
        # Apply softmax
        attention_weights = torch.softmax(attention_scores, dim=1).unsqueeze(-1)  # [batch_size, seq_len, 1]
        
        # Weighted sum
        pooled = torch.sum(hidden_states * attention_weights, dim=1)  # [batch_size, hidden_size]
        
        return pooled

    def mean_pooling(self, hidden_states, attention_mask):
        """Apply mean pooling with attention mask"""
        # Expand attention mask
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
        
        # Sum embeddings
        sum_embeddings = torch.sum(hidden_states * input_mask_expanded, 1)
        
        # Sum mask
        sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        
        return sum_embeddings / sum_mask

    def get_embeddings(self, input_ids, attention_mask):
        """Extract embeddings with specified pooling strategy"""
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        hidden_states = outputs.last_hidden_state
        
        if self.pooling_strategy == 'cls':
            return hidden_states[:, 0, :]
        elif self.pooling_strategy == 'mean':
            return self.mean_pooling(hidden_states, attention_mask)
        elif self.pooling_strategy == 'attention':
            return self.attention_pooling(hidden_states, attention_mask)
        else:
            return hidden_states[:, 0, :]

    def forward(self, input_ids1, attention_mask1, input_ids2, attention_mask2):
        # Get embeddings with advanced pooling
        emb1 = self.get_embeddings(input_ids1, attention_mask1)
        emb2 = self.get_embeddings(input_ids2, attention_mask2)
        
        # Enhanced feature combination
        abs_diff = torch.abs(emb1 - emb2)
        element_wise_mult = emb1 * emb2
        
        # Concatenate all features
        combined = torch.cat([emb1, emb2, abs_diff, element_wise_mult], dim=1)
        
        # Forward through enhanced classifier with batch normalization
        x = self.fc1(combined)
        x = self.bn1(x)
        x = torch.relu(x)
        x = self.dropout1(x)
        
        x = self.fc2(x)
        x = self.bn2(x)
        x = torch.relu(x)
        x = self.dropout2(x)
        
        x = self.fc3(x)
        x = self.bn3(x)
        x = torch.relu(x)
        x = self.dropout3(x)
        
        output = self.classifier(x)
        
        return output
