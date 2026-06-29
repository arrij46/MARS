import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Optional
import os
import json
from collections import defaultdict
import warnings
from backend.siameseModel.model import SiameseBERT
import itertools
from transformers import AutoModel, AutoTokenizer
import torch
import time

warnings.filterwarnings('ignore')

class DirectPairwiseSiameseAnalyzer:
    """
    Fully streamlined analyzer - generates all requirement pairs and classifies directly.
    NO graph construction, NO clustering - just embeddings → pairs → Siamese classification.
    """
    
    def __init__(self, 
                 model_dir: str = 'model',
                 dropout_rate: float = 0.3,
                 pooling_strategy: str = 'mean'):
        """
        Initialize the analyzer with custom trained model
        
        Args:
            model_dir: Directory containing trained model files
            dropout_rate: Dropout rate used during training
            pooling_strategy: Pooling strategy ('mean' or 'cls')
        """
        
        self.model_dir = model_dir
        self.dropout_rate = dropout_rate
        self.pooling_strategy = pooling_strategy
        
        # Set device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
        self.runtime_metrics = {}

        # Time model loading
        start_time = time.time()
        self._load_custom_model()
        self.runtime_metrics['model_loading_time'] = time.time() - start_time
        
        # Data storage
        self.requirements: List[str] = []
        self.requirement_numbers: List[int] = []
        self.embeddings: Optional[np.ndarray] = None
        self.similarity_matrix: Optional[np.ndarray] = None
        self.all_pairs: List[Tuple[str, str, int, int]] = []
        self.siamese_results: List[Dict] = []
        
        # Classification labels
        self.CLASS_NAMES = {
            0: "Duplicate",
            1: "Conflict", 
            2: "Neutral"
        }

    def _load_custom_model(self):
        """Load custom trained Siamese BERT model"""
        print(f"Loading custom model from {self.model_dir}...")
        
        try:
            # Load tokenizer
            tokenizer_path = os.path.join(self.model_dir, 'tokenizer')
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
            print(f"Tokenizer loaded from {tokenizer_path}")
            
            # Load BERT model configuration
            bert_config_path = os.path.join(self.model_dir, 'bert_config')
            bert_model = AutoModel.from_pretrained(bert_config_path)
            print(f"BERT model loaded from {bert_config_path}")
            
            # Load checkpoint
            checkpoint_path = os.path.join(self.model_dir, 'siamese_model.pth')
            checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
            print(f"Checkpoint loaded from {checkpoint_path}")
            
            # Initialize Siamese model
            self.siamese_model = SiameseBERT(
                bert_model, 
                num_classes=3, 
                dropout_rate=self.dropout_rate,
                pooling_strategy=self.pooling_strategy
            )
            
            # Load model weights
            self.siamese_model.load_state_dict(checkpoint['model_state_dict'])
            self.siamese_model.to(self.device)
            self.siamese_model.eval()
            print("Model weights loaded and set to evaluation mode")
            
            # Get class names from checkpoint
            self.CLASS_NAMES = checkpoint.get('class_names', {
                0: "Duplicate",
                1: "Conflict", 
                2: "Neutral"
            })
            print(f"Class names: {self.CLASS_NAMES}")
            print("Custom model loaded successfully!")
            
        except Exception as e:
            print(f"Error loading custom model: {str(e)}")
            raise

    def read_requirements(self, file_path: str) -> bool:
        """Read requirements from JSON file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data = data.get("requirements", [])

                # Case 1: List of {id, text}
                if isinstance(data, list) and all("id" in item and "text" in item for item in data):
                    self.requirements = [item["text"] for item in data]
                    self.requirement_numbers = [item["id"] for item in data]
                    print(f"Loaded {len(self.requirements)} requirements from list format.")
                    return True

                # Case 2: {"requirements": [...]}
                elif isinstance(data, dict) and "requirements" in data:
                    self.requirements = data["requirements"]
                    self.requirement_numbers = list(range(1, len(self.requirements) + 1))
                    print(f"Loaded {len(self.requirements)} requirements from dict format.")
                    return True

                else:
                    raise ValueError("Invalid JSON structure.")

        except Exception as e:
            print(f"Error reading file: {e}")
            self.requirements = []
            self.requirement_numbers = []
            return False
    
    def generate_embeddings(self) -> np.ndarray:
        """Generate embeddings using custom model (optional - for similarity reference)"""
        if not self.requirements:
            print("No requirements loaded. Please read requirements first.")
            return np.array([])
        
        print("Step 1: Generating embeddings using custom model...")
        embeddings_list = []
        
        # Generate embeddings in batches
        batch_size = 32
        for i in range(0, len(self.requirements), batch_size):
            batch = self.requirements[i:i + batch_size]
            
            # Tokenize
            inputs = self.tokenizer(
                batch,
                return_tensors='pt',
                padding=True,
                truncation=True,
                max_length=128
            )
            
            # Move to device
            input_ids = inputs['input_ids'].to(self.device)
            attention_mask = inputs['attention_mask'].to(self.device)
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.siamese_model.bert(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
                
                # Apply pooling strategy
                if self.pooling_strategy == 'mean':
                    last_hidden = outputs.last_hidden_state
                    mask = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
                    embeddings = torch.sum(last_hidden * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)
                else:  # 'cls'
                    embeddings = outputs.last_hidden_state[:, 0, :]
                
                embeddings_list.append(embeddings.cpu().numpy())
        
        self.embeddings = np.vstack(embeddings_list)
        print(f"Generated embeddings with shape: {self.embeddings.shape}")
        
        # Also compute similarity matrix for reference
        self.similarity_matrix = cosine_similarity(self.embeddings)
        print(f"Computed similarity matrix: {self.similarity_matrix.shape}")
        
        # Save embeddings to file
        embeddings_file = os.path.join('agents/cdn/embedding', 'embeddings.json')
        os.makedirs('agnets/cdn/embedding', exist_ok=True)
        embeddings_dict = {
            'embeddings': self.embeddings.tolist(),
            'shape': self.embeddings.shape,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(embeddings_file, 'w') as f:
            json.dump(embeddings_dict, f)
        print(f"Saved embeddings to: {embeddings_file}")

        return self.embeddings

    def generate_all_pairs(self) -> List[Tuple[str, str, int, int]]:
        """
        Generate ALL possible requirement pairs for analysis.
        No clustering - direct exhaustive pairwise comparison.
        """
        if not self.requirements:
            print("No requirements available. Read requirements first.")
            return []
        
        n = len(self.requirements)
        total_possible_pairs = n * (n - 1) // 2
        
        print(f"Step 2: Generating all possible requirement pairs...")
        print(f"  Total requirements: {n}")
        print(f"  Total pairs to analyze: {total_possible_pairs}")
        
        self.all_pairs = []
        for idx1, idx2 in itertools.combinations(range(n), 2):
            req1 = self.requirements[idx1]
            req2 = self.requirements[idx2]
            self.all_pairs.append((req1, req2, idx1, idx2))
        
        print(f"Generated {len(self.all_pairs)} pairs for Siamese analysis")
        return self.all_pairs
  
    def analyze_pairs_with_siamese(self) -> List[Dict]:
        """Analyze ALL requirement pairs using custom trained Siamese BERT"""
        if not self.all_pairs:
            print("No requirement pairs available. Generate pairs first.")
            return []
        
        print("Step 3: Analyzing ALL requirement pairs with custom Siamese BERT...")
        print(f"  Processing {len(self.all_pairs)} pairs...")
        
        self.siamese_results = []
        
        # Process pairs with progress indication
        batch_size = 100
        for i in range(0, len(self.all_pairs), batch_size):
            batch_pairs = self.all_pairs[i:i + batch_size]
            
            for req1, req2, idx1, idx2 in batch_pairs:
                result = self._classify_pair(req1, req2, idx1, idx2)
                self.siamese_results.append(result)
            
            # Progress update
            if (i + batch_size) % 500 == 0 or (i + batch_size) >= len(self.all_pairs):
                print(f"    Processed {min(i + batch_size, len(self.all_pairs))}/{len(self.all_pairs)} pairs...")
        
        print("Siamese analysis complete!")
        return self.siamese_results

    def _classify_pair(self, req1: str, req2: str, idx1: int, idx2: int) -> Dict:
        """Classify a single requirement pair"""
        # Tokenize
        enc1 = self.tokenizer(req1, return_tensors="pt", padding=True, 
                             truncation=True, max_length=128)
        enc2 = self.tokenizer(req2, return_tensors="pt", padding=True, 
                             truncation=True, max_length=128)
        
        # Move to device
        input_ids1 = enc1["input_ids"].to(self.device)
        attention_mask1 = enc1["attention_mask"].to(self.device)
        input_ids2 = enc2["input_ids"].to(self.device)
        attention_mask2 = enc2["attention_mask"].to(self.device)
        
        # Forward pass
        with torch.no_grad():
            logits = self.siamese_model(
                input_ids1, attention_mask1,
                input_ids2, attention_mask2
            )
        
        # Get predictions
        probabilities = torch.softmax(logits, dim=1)
        predicted_class_idx = int(torch.argmax(logits, dim=1).item())
        predicted_class_name = self.CLASS_NAMES.get(predicted_class_idx, "Unknown")
        confidence = probabilities[0][predicted_class_idx].item()
        
        return {
            'req1': req1,
            'req2': req2,
            'idx1': idx1,
            'idx2': idx2,
            'predicted_class': predicted_class_name,
            'predicted_class_idx': predicted_class_idx,
            'confidence': confidence,
            'all_probabilities': {
                self.CLASS_NAMES[i]: probabilities[0][i].item() 
                for i in self.CLASS_NAMES
            }
        }

    def display_siamese_results(self, show_all: bool = False, min_confidence: float = 0.7):
        """Display Siamese BERT classification results"""
        if not self.siamese_results:
            print("No Siamese results available.")
            return
        
        print(f"\n{'='*100}\nSIAMESE BERT CLASSIFICATION RESULTS\n{'='*100}")
        
        # Filter by confidence if needed
        results_to_show = self.siamese_results
        if not show_all:
            results_to_show = [r for r in results_to_show if r['confidence'] >= min_confidence]
        
        # Group by predicted class
        class_groups = defaultdict(list)
        for result in results_to_show:
            class_groups[result['predicted_class']].append(result)
        
        # Display each class
        for class_name in ['Duplicate', 'Conflict', 'Neutral']:
            class_results = class_groups.get(class_name, [])
            if class_results:
                print(f"\n{class_name.upper()} pairs ({len(class_results)}):")
                # Show top results sorted by confidence
                for result in sorted(class_results, key=lambda x: x['confidence'], reverse=True)[:50]:
                    num1 = self.requirement_numbers[result['idx1']]
                    num2 = self.requirement_numbers[result['idx2']]
                    print(f"  [{result['confidence']:.3f}] Req{num1} Req{num2}")
        
        # Summary statistics
        print(f"\n{'='*100}")
        print("SUMMARY STATISTICS:")
        for class_name in ['Duplicate', 'Conflict', 'Neutral']:
            count = len(class_groups.get(class_name, []))
            print(f"  {class_name}: {count} pairs")
        print(f"  Total pairs analyzed: {len(self.siamese_results)}")
        print(f"  Pairs shown (confidence >= {min_confidence}): {len(results_to_show)}")

    def save_results(self, output_file: str):
        """Save all results to text file"""
        if not self.siamese_results:
            print("No results to save.")
            return
        
        try:
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write("DIRECT PAIRWISE SIAMESE BERT ANALYSIS\n")
                file.write("=" * 80 + "\n\n")
                
                file.write("REQUIREMENTS LIST\n")
                file.write("-" * 40 + "\n")
                for idx, req in enumerate(self.requirements):
                    num = self.requirement_numbers[idx]
                    file.write(f"{num}. {req}\n")
                
                file.write(f"\n\nSIAMESE BERT CLASSIFICATION RESULTS\n")
                file.write("-" * 40 + "\n")
                file.write(f"Total pairs analyzed: {len(self.siamese_results)}\n\n")
                
                # Group by class
                class_groups = defaultdict(list)
                for result in self.siamese_results:
                    class_groups[result['predicted_class']].append(result)
                
                for class_name in ['Duplicate', 'Conflict', 'Neutral']:
                    class_results = class_groups.get(class_name, [])
                    if class_results:
                        file.write(f"\n{class_name.upper()} pairs ({len(class_results)}):\n")
                        file.write("-" * 40 + "\n")
                        for result in sorted(class_results, key=lambda x: x['confidence'], reverse=True):
                            num1 = self.requirement_numbers[result['idx1']]
                            num2 = self.requirement_numbers[result['idx2']]
                            file.write(f"[{result['confidence']:.3f}] Req{num1} Req{num2}\n")
                            file.write(f"  • {result['req1']}\n")
                            file.write(f"  • {result['req2']}\n\n")
            
            print(f"Results saved to: {output_file}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")

    def save_results_json(self, output_file: str):
        """Save all analysis results into structured JSON"""
        if not self.siamese_results:
            print("No results to save in JSON format.")
            return

        try:
            # Group results by class
            class_groups = defaultdict(list)
            for result in self.siamese_results:
                class_groups[result['predicted_class']].append({
                    "req1_number": self.requirement_numbers[result["idx1"]],
                    "req2_number": self.requirement_numbers[result["idx2"]],
                    "req1_text": result["req1"],
                    "req2_text": result["req2"],
                    "predicted_class": result["predicted_class"],
                    "confidence": result["confidence"],
                    "all_probabilities": result["all_probabilities"]
                })
            
            data = {
                "metadata": {
                    "total_requirements": len(self.requirements),
                    "total_pairs_analyzed": len(self.siamese_results),
                    "analysis_method": "direct_pairwise"
                },
                "requirements": [
                    {
                        "id": self.requirement_numbers[i],
                        "text": self.requirements[i]
                    }
                    for i in range(len(self.requirements))
                ],
                "classification_results": {
                    "duplicate": class_groups.get("Duplicate", []),
                    "conflict": class_groups.get("Conflict", []),
                    "neutral": class_groups.get("Neutral", [])
                },
                "statistics": {
                    "duplicate_count": len(class_groups.get("Duplicate", [])),
                    "conflict_count": len(class_groups.get("Conflict", [])),
                    "neutral_count": len(class_groups.get("Neutral", []))
                }
            }

            json_path = os.path.splitext(output_file)[0] + ".json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            print(f"JSON results saved to: {json_path}")
        except Exception as e:
            print(f"Error saving JSON results: {str(e)}")

    def run_complete_analysis(self, 
                             requirements_file: str,
                             output_file: str = "./results/nocluster_time_analysis_results.txt"):
        """Run the complete streamlined analysis pipeline"""
        
        print("\n" + "="*80)
        print("STARTING DIRECT PAIRWISE SIAMESE ANALYSIS PIPELINE")
        print("="*80 + "\n")
        timings = self.runtime_metrics

        # Step 1: Read requirements
        start = time.time()
        if not self.read_requirements(requirements_file):
            print("Failed to read requirements. Exiting.")
            return
        timings['read_requirements_time'] = time.time() - start

        # Step 2: Generate embeddings (optional, for reference)
        start = time.time()
        if len(self.generate_embeddings()) == 0:
            print("Failed to generate embeddings. Exiting.")
            return
        timings['generate_embeddings_time'] = time.time() - start
        
        # Step 3: Generate ALL pairs (no clustering)
        start = time.time()
        pairs = self.generate_all_pairs()
        if not pairs:
            print("Failed to generate pairs.")
            return
        timings['generate_pairs_time'] = time.time() - start
        
        # Step 4: Analyze ALL pairs with Siamese BERT
        start = time.time()
        siamese_results = self.analyze_pairs_with_siamese()
        if not siamese_results:
            print("Failed to analyze pairs with Siamese BERT.")
            return
        timings['siamese_analysis_time'] = time.time() - start
        
        # Display and save results
        self.display_siamese_results(show_all=False, min_confidence=0.7)
        self.save_results(output_file)
        self.save_results_json(output_file)
        
        print(f"\n{'='*80}\nANALYSIS COMPLETED SUCCESSFULLY\n{'='*80}")
        print(f"Method: Direct pairwise analysis (no graph, no clustering)")
        print(f"Total pairs analyzed: {len(siamese_results)}")
        print(f"Results saved to: {output_file}")

        # Save timing info at the end
        os.makedirs("./results", exist_ok=True)
        runtime_file = "./results/nocluster_time_analysis_results.txt"
        with open(runtime_file, "w", encoding="utf-8") as f:
            f.write("RUNTIME ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n")
            for key, val in timings.items():
                f.write(f"{key}: {val:.4f} seconds\n")
            f.write("=" * 50 + "\n")
            total_time = sum(timings.values())
            f.write(f"Total execution time: {total_time:.4f} seconds\n")
        print(f"Runtime analysis saved to: {runtime_file}")


# Global analyzer instance
analyzer_instance = None

def handle_command(command_str):
    """Handle commands received from Node.js"""
    global analyzer_instance
    try:
        command = json.loads(command_str)
        if command['command'] == 'analyze':
            if analyzer_instance:
                analyzer_instance.run_complete_analysis(
                    requirements_file=command['data']['requirements_file'],
                    output_file="./results/nocluster_results.txt"
                )
            else:
                print("Error: Analyzer not initialized")
    except Exception as e:
        print(f"Error processing command: {str(e)}")

def main():
    import sys
    global analyzer_instance
    
    # Check if running in initialization mode
    if '--initialize-only' in sys.argv:
        print("Initializing DirectPairwiseSiameseAnalyzer in pre-load mode...\n")
        analyzer_instance = DirectPairwiseSiameseAnalyzer(
            model_dir='model',
            dropout_rate=0.3,
            pooling_strategy='mean'
        )
        print("Analyzer initialized and ready for use")
        
        # Enter command listening mode
        while True:
            try:
                command = input().strip()
                if command:
                    handle_command(command)
                    sys.stdout.flush()  # Ensure output is sent immediately
            except EOFError:
                break  # Exit if pipe is closed
            except Exception as e:
                print(f"Error: {str(e)}")
                sys.stdout.flush()
        return
    
    print("Initializing Direct Pairwise Siamese Analyzer for analysis...\n")
    
    os.makedirs('./results', exist_ok=True)
    
    requirements_file = "./data/data.json"
    output_file = "./results/nocluster_results.txt"

    if not os.path.exists(requirements_file):
        print(f"Requirements file '{requirements_file}' not found.")
        return

    # Use existing analyzer instance if available
    if analyzer_instance is None:
        analyzer_instance = DirectPairwiseSiameseAnalyzer(
            model_dir='model',
            dropout_rate=0.3,
            pooling_strategy='mean'
        )

    # Run complete pairwise analysis
    analyzer_instance.run_complete_analysis(
        requirements_file=requirements_file,
        output_file=output_file
    )


if __name__ == "__main__":
    main()