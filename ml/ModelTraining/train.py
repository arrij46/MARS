import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split, WeightedRandomSampler
import matplotlib.pyplot as plt
from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup
from datetime import datetime
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, f1_score
import seaborn as sns
from collections import Counter
import json
import shutil

from model import SiameseBERT
from dataset import RequirementPairsDataset

class SiameseTrainer:
    def __init__(self, bert_model_path: str = "./model/mpnet-base-v2", device: str = None):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        print(f"Using device: {self.device}")
        
        self.bert_model_path = bert_model_path
        self._load_bert_model()
        
        self.training_history = {
            'train_loss': [],
            'train_accuracy': [],
            'train_f1': [],
            'val_loss': [],
            'val_accuracy': [],
            'val_f1': []
        }
        
        self.CLASS_NAMES = {
            0: "Duplicate",
            1: "Conflict", 
            2: "Neutral"
        }
        self.CLASS_TO_IDX = {v: k for k, v in self.CLASS_NAMES.items()}
        
        # Track training state for resuming
        self.start_epoch = 0
        self.best_val_f1 = 0.0
        self.optimizer_state = None
        self.scheduler_state = None

    def _load_bert_model(self):
        """Load BERT model and tokenizer"""
        print("Loading BERT model and tokenizer...")
        model = AutoModel.from_pretrained(self.bert_model_path)
        tokenizer = AutoTokenizer.from_pretrained(self.bert_model_path)
        
        self.bert_model = model
        self.bert_tokenizer = tokenizer
        self.siamese_model = SiameseBERT(
            self.bert_model, 
            num_classes=3, 
            dropout_rate=0.3,
            pooling_strategy='mean'
        ).to(self.device)

    def load_checkpoint(self, checkpoint_path: str):
        """Load a previously saved checkpoint to resume training"""
        if not os.path.exists(checkpoint_path):
            print(f"Checkpoint not found at {checkpoint_path}")
            return False
        
        print(f"Loading checkpoint from {checkpoint_path}...")
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        # Load model state
        self.siamese_model.load_state_dict(checkpoint['model_state_dict'])
        self.bert_model.load_state_dict(checkpoint['bert_model_state_dict'])
        
        # Load training history if available
        if 'training_history' in checkpoint:
            self.training_history = checkpoint['training_history']
            print(f"Loaded training history with {len(self.training_history['train_loss'])} epochs")
        
        # Load training state
        if 'epoch' in checkpoint:
            self.start_epoch = checkpoint['epoch'] + 1
            print(f"Resuming from epoch {self.start_epoch}")
        
        if 'best_val_f1' in checkpoint:
            self.best_val_f1 = checkpoint['best_val_f1']
            print(f"Best validation F1 so far: {self.best_val_f1:.4f}")
        
        # Store optimizer and scheduler states to load later
        if 'optimizer_state_dict' in checkpoint:
            self.optimizer_state = checkpoint['optimizer_state_dict']
            print("Optimizer state loaded")
        
        if 'scheduler_state_dict' in checkpoint:
            self.scheduler_state = checkpoint['scheduler_state_dict']
            print("Scheduler state loaded")
        
        print("Checkpoint loaded successfully!")
        return True

    def compute_class_weights(self, dataset):
        """Compute class weights for handling imbalanced data"""
        labels = [dataset[i]['labels'].item() for i in range(len(dataset))]
        class_counts = Counter(labels)
        total = len(labels)
        
        weights = {cls: total / (len(class_counts) * count) 
                  for cls, count in class_counts.items()}
        
        weight_tensor = torch.tensor([weights[i] for i in range(len(weights))], 
                                     dtype=torch.float32).to(self.device)
        
        print(f"\nClass weights: {weights}")
        return weight_tensor

    def create_weighted_sampler(self, dataset):
        """Create weighted sampler for balanced batches"""
        labels = [dataset[i]['labels'].item() for i in range(len(dataset))]
        class_counts = Counter(labels)
        
        sample_weights = [1.0 / class_counts[label] for label in labels]
        
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True
        )
        
        return sampler

    def save_complete_model(self, model_dir: str, epoch: int = None, 
                           optimizer=None, scheduler=None, val_f1: float = None):
        """
        Save the complete model including:
        - Model weights (.pth)
        - BERT tokenizer files
        - Model configuration
        - Training metadata
        - Class mappings
        """
        # Create directory structure
        os.makedirs(model_dir, exist_ok=True)
        
        print(f"\nSaving complete model to: {model_dir}/")
        
        # 1. Save model weights
        checkpoint_data = {
            'model_state_dict': self.siamese_model.state_dict(),
            'bert_model_state_dict': self.bert_model.state_dict(),
            'training_history': self.training_history,
            'class_names': self.CLASS_NAMES,
            'class_to_idx': self.CLASS_TO_IDX,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add training state if available
        if epoch is not None:
            checkpoint_data['epoch'] = epoch
        if optimizer is not None:
            checkpoint_data['optimizer_state_dict'] = optimizer.state_dict()
        if scheduler is not None:
            checkpoint_data['scheduler_state_dict'] = scheduler.state_dict()
        if val_f1 is not None:
            checkpoint_data['best_val_f1'] = val_f1
        
        model_path = os.path.join(model_dir, 'siamese_model.pth')
        torch.save(checkpoint_data, model_path)
        #print(f"Model weights saved: {model_path}")
        
        # 2. Save tokenizer files
        tokenizer_dir = os.path.join(model_dir, 'tokenizer')
        os.makedirs(tokenizer_dir, exist_ok=True)
        self.bert_tokenizer.save_pretrained(tokenizer_dir)
        #print(f"Tokenizer saved: {tokenizer_dir}/")
        
        # 3. Save BERT model configuration
        bert_config_dir = os.path.join(model_dir, 'bert_config')
        os.makedirs(bert_config_dir, exist_ok=True)
        self.bert_model.save_pretrained(bert_config_dir)
        #print(f"BERT config saved: {bert_config_dir}/")
        
        # 4. Save model configuration
        model_config = {
            'architecture': 'SiameseBERT',
            'num_classes': 3,
            'dropout_rate': 0.3,
            'pooling_strategy': 'mean',
            'bert_model_name': 'mpnet-base-v2',
            'bert_hidden_size': self.bert_model.config.hidden_size,
            'class_names': self.CLASS_NAMES,
            'class_to_idx': self.CLASS_TO_IDX,
            'device': str(self.device),
            'pytorch_version': torch.__version__,
            'created_at': datetime.now().isoformat()
        }
        
        config_path = os.path.join(model_dir, 'model_config.json')
        with open(config_path, 'w') as f:
            json.dump(model_config, f, indent=4)
        #print(f"Model config saved: {config_path}")
        
        # 5. Save training metadata
        training_metadata = {
            'total_epochs': len(self.training_history['train_loss']),
            'best_val_f1': self.best_val_f1,
            'final_train_loss': self.training_history['train_loss'][-1] if self.training_history['train_loss'] else None,
            'final_val_loss': self.training_history['val_loss'][-1] if self.training_history['val_loss'] else None,
            'final_train_accuracy': self.training_history['train_accuracy'][-1] if self.training_history['train_accuracy'] else None,
            'final_val_accuracy': self.training_history['val_accuracy'][-1] if self.training_history['val_accuracy'] else None,
            'training_history': self.training_history,
            'last_updated': datetime.now().isoformat()
        }
        
        metadata_path = os.path.join(model_dir, 'training_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(training_metadata, f, indent=4)
        print(f"Training metadata saved: {metadata_path}")
        
        # 6. Create a README file with usage instructions
        readme_content = f"""# Siamese BERT Model - Requirements Classification

## Model Information
- Architecture: SiameseBERT
- Base Model: mpnet-base-v2
- Task: Multi-class classification (Duplicate/Conflict/Neutral)
- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Best Validation F1: {self.best_val_f1:.4f}

## Model Files
- `siamese_model.pth`: Complete model checkpoint with weights
- `tokenizer/`: BERT tokenizer files
- `bert_config/`: BERT model configuration
- `model_config.json`: Model architecture configuration
- `training_metadata.json`: Training history and metrics
- `README.md`: This file

## Classes
{json.dumps(self.CLASS_NAMES, indent=2)}

## Usage Example

```python
import torch
from transformers import AutoTokenizer
from model import SiameseBERT

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained('./trainedModel/tokenizer')

# Load model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
checkpoint = torch.load('./trainedModel/siamese_model.pth', map_location=device)

# Initialize model (you'll need to load BERT first)
from transformers import AutoModel
bert_model = AutoModel.from_pretrained('./trainedModel/bert_config')
model = SiameseBERT(bert_model, num_classes=3, dropout_rate=0.3, pooling_strategy='mean')
model.load_state_dict(checkpoint['model_state_dict'])
model.to(device)
model.eval()

# Make predictions
req1 = "Your first requirement text"
req2 = "Your second requirement text"

inputs1 = tokenizer(req1, return_tensors='pt', padding=True, truncation=True, max_length=128)
inputs2 = tokenizer(req2, return_tensors='pt', padding=True, truncation=True, max_length=128)

with torch.no_grad():
    outputs = model(
        inputs1['input_ids'].to(device),
        inputs1['attention_mask'].to(device),
        inputs2['input_ids'].to(device),
        inputs2['attention_mask'].to(device)
    )
    prediction = torch.argmax(outputs, dim=1).item()
    
class_names = checkpoint['class_names']
print(f"Prediction: {{class_names[prediction]}}")
```

## Training Information
- Total Epochs: {len(self.training_history['train_loss'])}
- Best Validation F1: {self.best_val_f1:.4f}
- Final Training Loss: {self.training_history['train_loss'][-1] if self.training_history['train_loss'] else 'N/A'}
- Final Validation Loss: {self.training_history['val_loss'][-1] if self.training_history['val_loss'] else 'N/A'}

## Requirements
- PyTorch >= 1.9.0
- Transformers >= 4.0.0
- numpy
- scikit-learn

For more information, refer to the training code and documentation.
"""
        
        readme_path = os.path.join(model_dir, 'README.md')
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        print(f"README saved: {readme_path}")
        
        print(f"\nComplete model package saved successfully!")
        print(f"Total files in {model_dir}:")
        for root, dirs, files in os.walk(model_dir):
            level = root.replace(model_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{sub_indent}{file}")

    def train(self, 
              training_file: str,
              epochs: int = 15,
              batch_size: int = 16,
              learning_rate: float = 2e-5,
              validation_split: float = 0.2,
              model_save_path: str = "trainedModel/siamese_model.pth",
              checkpoint_path: str = None,
              resume_training: bool = False,
              use_class_weights: bool = True,
              use_balanced_sampling: bool = True,
              gradient_accumulation_steps: int = 1,
              warmup_steps: int = 500,
              early_stopping_patience: int = 5,
              save_checkpoint_every: int = 5):
        """
        Train with support for resuming from checkpoint
        
        Args:
            resume_training: If True, load checkpoint_path and continue training
            checkpoint_path: Path to checkpoint file (defaults to model_save_path)
            save_checkpoint_every: Save checkpoint every N epochs
        """
        
        print("=" * 60)
        print("SIAMESE BERT TRAINING")
        print("=" * 60)
        
        os.makedirs("trainedModel", exist_ok=True)
        
        # Set checkpoint path
        if checkpoint_path is None:
            checkpoint_path = model_save_path
        
        # Resume from checkpoint if requested
        if resume_training:
            loaded = self.load_checkpoint(checkpoint_path)
            if not loaded:
                print("Failed to load checkpoint. Starting fresh training...")
                self.start_epoch = 0
                self.best_val_f1 = 0.0
        else:
            print("Starting fresh training...")
        
        # Load dataset
        try:
            dataset = RequirementPairsDataset(training_file, self.bert_tokenizer)
            print(f"\nLoaded dataset with {len(dataset)} samples")
            print("\nLabel distribution:")
            print(dataset.get_label_distribution())
        except Exception as e:
            print(f"Error loading training data: {str(e)}")
            return False
        
        # Split dataset
        val_size = int(len(dataset) * validation_split)
        train_size = len(dataset) - val_size
        
        # Use same random seed for reproducible splits when resuming
        torch.manual_seed(42)
        train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
        
        # Compute class weights if enabled
        class_weights = None
        if use_class_weights:
            class_weights = self.compute_class_weights(train_dataset)
        
        # Create data loaders
        if use_balanced_sampling:
            train_sampler = self.create_weighted_sampler(train_dataset)
            train_loader = DataLoader(train_dataset, batch_size=batch_size, sampler=train_sampler,drop_last=True)
        else:
            train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,drop_last=True)
        
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        print(f"\nTraining samples: {len(train_dataset)}")
        print(f"Validation samples: {len(val_dataset)}")
        
        # Initialize optimizer with layer-wise learning rate decay
        param_groups = [
            {'params': self.bert_model.parameters(), 'lr': learning_rate * 0.1},
            {'params': self.siamese_model.classifier.parameters(), 'lr': learning_rate},
            {'params': self.siamese_model.fc1.parameters(), 'lr': learning_rate},
            {'params': self.siamese_model.fc2.parameters(), 'lr': learning_rate},
            {'params': self.siamese_model.fc3.parameters(), 'lr': learning_rate}
        ]
        
        optimizer = optim.AdamW(param_groups, weight_decay=0.01)
        
        # Load optimizer state if resuming
        if self.optimizer_state is not None:
            optimizer.load_state_dict(self.optimizer_state)
            print("Optimizer state restored")
        
        # Learning rate scheduler with warmup
        total_steps = len(train_loader) * epochs // gradient_accumulation_steps
        scheduler = get_linear_schedule_with_warmup(
            optimizer, 
            num_warmup_steps=warmup_steps,
            num_training_steps=total_steps
        )
        
        # Load scheduler state if resuming
        if self.scheduler_state is not None:
            scheduler.load_state_dict(self.scheduler_state)
            print("✓ Scheduler state restored")
        
        # Loss function with class weights
        if class_weights is not None:
            criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)
        else:
            criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        
        print(f"\nStarting training from epoch {self.start_epoch + 1} to {epochs}")
        print("-" * 60)
        
        patience_counter = 0
        
        for epoch in range(self.start_epoch, epochs):
            # Training phase
            self.siamese_model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            all_train_preds = []
            all_train_labels = []
            
            optimizer.zero_grad()
            
            for batch_idx, batch in enumerate(train_loader):
                input_ids1 = batch['input_ids1'].to(self.device)
                attention_mask1 = batch['attention_mask1'].to(self.device)
                input_ids2 = batch['input_ids2'].to(self.device)
                attention_mask2 = batch['attention_mask2'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = self.siamese_model(input_ids1, attention_mask1, input_ids2, attention_mask2)
                loss = criterion(outputs, labels)
                
                # Gradient accumulation
                loss = loss / gradient_accumulation_steps
                loss.backward()
                
                if (batch_idx + 1) % gradient_accumulation_steps == 0:
                    torch.nn.utils.clip_grad_norm_(self.siamese_model.parameters(), max_norm=1.0)
                    optimizer.step()
                    scheduler.step()
                    optimizer.zero_grad()
                
                train_loss += loss.item() * gradient_accumulation_steps
                _, predicted = torch.max(outputs.data, 1)
                train_total += labels.size(0)
                train_correct += (predicted == labels).sum().item()
                
                all_train_preds.extend(predicted.cpu().numpy())
                all_train_labels.extend(labels.cpu().numpy())
                
                if batch_idx % 10 == 0:
                    current_lr = scheduler.get_last_lr()[0]
                    print(f"Epoch {epoch+1}, Batch {batch_idx}, Loss: {loss.item() * gradient_accumulation_steps:.4f}, LR: {current_lr:.2e}")
            
            # Calculate training metrics
            train_accuracy = 100.0 * train_correct / train_total
            train_f1 = f1_score(all_train_labels, all_train_preds, average='weighted')
            avg_train_loss = train_loss / len(train_loader)
            
            # Validation phase
            val_loss, val_accuracy, val_f1, val_preds, val_labels = self.validate(val_loader, criterion)
            
            # Store history
            self.training_history['train_loss'].append(avg_train_loss)
            self.training_history['train_accuracy'].append(train_accuracy)
            self.training_history['train_f1'].append(train_f1)
            self.training_history['val_loss'].append(val_loss)
            self.training_history['val_accuracy'].append(val_accuracy)
            self.training_history['val_f1'].append(val_f1)
            
            # Print progress
            print(f"\nEpoch {epoch+1}/{epochs}:")
            print(f"  Train Loss: {avg_train_loss:.4f}, Train Acc: {train_accuracy:.2f}%, Train F1: {train_f1:.4f}")
            print(f"  Val Loss: {val_loss:.4f}, Val Acc: {val_accuracy:.2f}%, Val F1: {val_f1:.4f}")
            print(f"  Learning Rate: {scheduler.get_last_lr()[0]:.2e}")
            print("-" * 60)
            
            # Save checkpoint periodically
            if (epoch + 1) % save_checkpoint_every == 0:
                checkpoint_dir = f"trainedModel/checkpoint_epoch_{epoch+1}"
                self.save_complete_model(checkpoint_dir, epoch, optimizer, scheduler, val_f1)
                print(f"Checkpoint saved: {checkpoint_dir}/")
            
            # Early stopping based on F1 score
            if val_f1 > self.best_val_f1:
                self.best_val_f1 = val_f1
                patience_counter = 0
                # Save complete model package
                self.save_complete_model("trainedModel", epoch, optimizer, scheduler, val_f1)
                print(f"New best model saved! Val F1: {val_f1:.4f}")
            else:
                patience_counter += 1
                print(f"No improvement. Patience: {patience_counter}/{early_stopping_patience}")
                
                if patience_counter >= early_stopping_patience:
                    print(f"\n⚠ Early stopping triggered after epoch {epoch+1}")
                    break
        
        print("\n" + "=" * 60)
        print("TRAINING COMPLETED!")
        print(f"Best validation F1 score: {self.best_val_f1:.4f}")
        print(f"Total epochs trained: {len(self.training_history['train_loss'])}")
        print("=" * 60)
        
        self.plot_training_history()
        self.test_model(val_loader, "Validation Set")
        
        # Save final complete model
        print("\n" + "=" * 60)
        print("SAVING FINAL MODEL PACKAGE")
        print("=" * 60)
        self.save_complete_model("trainedModel", len(self.training_history['train_loss']) - 1, 
                                optimizer, scheduler, self.best_val_f1)
        
        return True

    def validate(self, val_loader, criterion):
        """Validate the model"""
        self.siamese_model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for batch in val_loader:
                input_ids1 = batch['input_ids1'].to(self.device)
                attention_mask1 = batch['attention_mask1'].to(self.device)
                input_ids2 = batch['input_ids2'].to(self.device)
                attention_mask2 = batch['attention_mask2'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = self.siamese_model(input_ids1, attention_mask1, input_ids2, attention_mask2)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
                
                all_preds.extend(predicted.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        val_accuracy = 100.0 * val_correct / val_total
        val_f1 = f1_score(all_labels, all_preds, average='weighted')
        avg_val_loss = val_loss / len(val_loader)
        
        return avg_val_loss, val_accuracy, val_f1, all_preds, all_labels

    def test_model(self, test_loader, dataset_name="Test Set"):
        """Test the model and generate comprehensive evaluation metrics"""
        self.siamese_model.eval()
        
        all_predictions = []
        all_labels = []
        all_probabilities = []
        
        with torch.no_grad():
            for batch in test_loader:
                input_ids1 = batch['input_ids1'].to(self.device)
                attention_mask1 = batch['attention_mask1'].to(self.device)
                input_ids2 = batch['input_ids2'].to(self.device)
                attention_mask2 = batch['attention_mask2'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = self.siamese_model(input_ids1, attention_mask1, input_ids2, attention_mask2)
                probabilities = torch.softmax(outputs, dim=1)
                _, predicted = torch.max(outputs.data, 1)
                
                all_predictions.extend(predicted.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                all_probabilities.extend(probabilities.cpu().numpy())
        
        all_predictions = np.array(all_predictions)
        all_labels = np.array(all_labels)
        
        print(f"\n{dataset_name} Classification Report:")
        print("=" * 60)
        print(classification_report(all_labels, all_predictions, 
                                   target_names=list(self.CLASS_NAMES.values())))
        
        self.plot_confusion_matrix(all_labels, all_predictions, dataset_name)
        
        accuracy = 100.0 * (all_predictions == all_labels).sum() / len(all_labels)
        f1 = f1_score(all_labels, all_predictions, average='weighted')
        print(f"\nOverall Accuracy: {accuracy:.2f}%")
        print(f"Weighted F1 Score: {f1:.4f}")
        
        return accuracy

    def plot_confusion_matrix(self, y_true, y_pred, dataset_name):
        """Plot confusion matrix"""
        cm = confusion_matrix(y_true, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=list(self.CLASS_NAMES.values()),
                   yticklabels=list(self.CLASS_NAMES.values()))
        plt.title(f'Confusion Matrix - {dataset_name}')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()
        plt.savefig(f'trainedModel/confusion_matrix_{dataset_name.replace(" ", "_").lower()}.png', 
                   bbox_inches='tight', dpi=200)
        plt.close()

    def save_checkpoint(self, checkpoint_path: str, epoch: int, optimizer, scheduler, val_f1: float):
        """Save a checkpoint (for backward compatibility)"""
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.siamese_model.state_dict(),
            'bert_model_state_dict': self.bert_model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'training_history': self.training_history,
            'best_val_f1': self.best_val_f1,
            'class_names': self.CLASS_NAMES,
            'class_to_idx': self.CLASS_TO_IDX,
            'timestamp': datetime.now().isoformat()
        }, checkpoint_path)

    def save_model(self, model_path: str):
        """Save just the model (backward compatibility)"""
        torch.save({
            'model_state_dict': self.siamese_model.state_dict(),
            'bert_model_state_dict': self.bert_model.state_dict(),
            'training_history': self.training_history,
            'class_names': self.CLASS_NAMES,
            'class_to_idx': self.CLASS_TO_IDX,
            'timestamp': datetime.now().isoformat()
        }, model_path)

    def plot_training_history(self):
        """Plot training history"""
        if not self.training_history['train_loss']:
            return
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        epochs = range(1, len(self.training_history['train_loss']) + 1)
        
        # Plot loss
        axes[0].plot(epochs, self.training_history['train_loss'], 'b-', label='Training Loss', linewidth=2)
        axes[0].plot(epochs, self.training_history['val_loss'], 'r-', label='Validation Loss', linewidth=2)
        axes[0].set_title('Training and Validation Loss', fontsize=12, fontweight='bold')
        axes[0].set_xlabel('Epochs')
        axes[0].set_ylabel('Loss')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot accuracy
        axes[1].plot(epochs, self.training_history['train_accuracy'], 'b-', label='Training Accuracy', linewidth=2)
        axes[1].plot(epochs, self.training_history['val_accuracy'], 'r-', label='Validation Accuracy', linewidth=2)
        axes[1].set_title('Training and Validation Accuracy', fontsize=12, fontweight='bold')
        axes[1].set_xlabel('Epochs')
        axes[1].set_ylabel('Accuracy (%)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Plot F1 score
        axes[2].plot(epochs, self.training_history['train_f1'], 'b-', label='Training F1', linewidth=2)
        axes[2].plot(epochs, self.training_history['val_f1'], 'r-', label='Validation F1', linewidth=2)
        axes[2].set_title('Training and Validation F1 Score', fontsize=12, fontweight='bold')
        axes[2].set_xlabel('Epochs')
        axes[2].set_ylabel('F1 Score')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('trainedModel/training_history.png', bbox_inches='tight', dpi=200)
        plt.close()
        print("Training history plot saved to: trainedModel/training_history.png")

def main():
    training_file = 'DATASET.json'
    model_save_path = 'trainedModel/siamese_model.pth'
    
    # Training configuration
    epochs = 20
    batch_size = 16
    learning_rate = 2e-5
    validation_split = 0.2
    gradient_accumulation_steps = 2
    warmup_steps = 500
    early_stopping_patience = 3
    save_checkpoint_every = 5
    
    # RESUME TRAINING SETTINGS
    # Set resume_training=True to continue from a checkpoint
    # Set checkpoint_path to the specific checkpoint file you want to resume from
    resume_training = False  # Change to True to resume training
    checkpoint_path = 'trainedModel/siamese_model.pth'  # or 'trainedModel/checkpoint_epoch_10/siamese_model.pth'

    if not os.path.exists(training_file):
        print(f"Training file not found: {training_file}")
        return

    print("\n" + "=" * 60)
    print("INITIALIZING SIAMESE BERT TRAINER")
    print("=" * 60)
    
    trainer = SiameseTrainer(bert_model_path="./model/mpnet-base-v2")

    success = trainer.train(
        training_file=training_file,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        validation_split=validation_split,
        model_save_path=model_save_path,
        checkpoint_path=checkpoint_path,
        resume_training=resume_training,
        use_class_weights=True,
        use_balanced_sampling=True,
        gradient_accumulation_steps=gradient_accumulation_steps,
        warmup_steps=warmup_steps,
        early_stopping_patience=early_stopping_patience,
        save_checkpoint_every=save_checkpoint_every
    )

    if success:
        print(f"\nTraining completed successfully!")
        print(f"Complete model package saved to: trainedModel/")
        print(f"Training plots saved to: trainedModel/")
        print("\nModel package includes:")
        print("  - siamese_model.pth (model weights)")
        print("  - tokenizer/ (BERT tokenizer files)")
        print("  - bert_config/ (BERT configuration)")
        print("  - model_config.json (model architecture)")
        print("  - training_metadata.json (training history)")
        print("  - README.md (usage instructions)")
    else:
        print("\nTraining failed!")

if __name__ == "__main__":
    main()
