import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Optional
import os
import json
from collections import defaultdict
import warnings
from siameseModel.model import SiameseBERT
import itertools
from transformers import AutoModel, AutoTokenizer
import torch
from sklearn.cluster import KMeans
import time

warnings.filterwarnings('ignore')

class DirectClusteringSiameseAnalyzer:
    def __init__(self, 
                 model_dir: str = 'model',
                 dropout_rate: float = 0.3,
                 pooling_strategy: str = 'mean'):
        
        self.model_dir = model_dir
        self.dropout_rate = dropout_rate
        self.pooling_strategy = pooling_strategy
        
        # Set device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
       
        # Time model loading
        self.runtime_metrics = {}
        start_time = time.time()
        self._load_custom_model()
        self.runtime_metrics['model_loading_time'] = time.time() - start_time
        
        # Data storage
        self.requirements: List[str] = []
        self.requirement_numbers: List[int] = []
        self.embeddings: Optional[np.ndarray] = None
        self.similarity_matrix: Optional[np.ndarray] = None
        self.clusters: Optional[Dict[int, int]] = None
        self.cluster_pairs: Dict[int, List[Tuple[str, str, int, int]]] = {}
        self.siamese_results: Dict[int, List[Dict]] = {}
        
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
            checkpoint = torch.load(checkpoint_path, map_location=self.device,  weights_only=False)
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
        """Generate embeddings using custom model"""
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
        os.makedirs('agents/cdn/embedding', exist_ok=True)
        embeddings_dict = {
            'embeddings': self.embeddings.tolist(),
            'shape': self.embeddings.shape,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(embeddings_file, 'w') as f:
            json.dump(embeddings_dict, f)
        print(f"Saved embeddings to: {embeddings_file}")
        
        return self.embeddings

    def _determine_optimal_clusters(self, n_requirements: int) -> int:
        """
        Dynamically determine optimal number of clusters based on dataset size.
        
        Rules:
        - Small datasets (< 10): 2-3 clusters
        - Medium datasets (10-50): sqrt(n) clusters
        - Large datasets (> 50): sqrt(n) with cap at 15
        """
        if n_requirements < 10:
            return max(2, n_requirements // 3)
        elif n_requirements <= 50:
            return max(3, int(np.sqrt(n_requirements)))
        else:
            return min(15, max(5, int(np.sqrt(n_requirements))))

    def cluster_embeddings(self, n_clusters: Optional[int] = None) -> Dict[int, int]:
        """Cluster embeddings directly using KMeans"""
        if self.embeddings is None:
            print("No embeddings available. Generate embeddings first.")
            return {}
        
        n_requirements = len(self.requirements)
        
        # Determine optimal clusters dynamically
        if n_clusters is None:
            n_clusters = self._determine_optimal_clusters(n_requirements)
            print(f"Step 2: Auto-determined optimal clusters: {n_clusters} (from {n_requirements} requirements)")
        else:
            print(f"Step 2: Using specified cluster count: {n_clusters}")
        
        # Ensure valid cluster count
        n_clusters = min(n_clusters, n_requirements)
        
        print(f"Clustering {n_requirements} requirements into {n_clusters} clusters using KMeans...")
        
        # Apply KMeans directly on embeddings
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        labels = kmeans.fit_predict(self.embeddings)
        
        # Store cluster assignments
        self.clusters = {i: int(labels[i]) for i in range(n_requirements)}
        
        # Print cluster distribution
        cluster_sizes = defaultdict(int)
        for cluster_id in self.clusters.values():
            cluster_sizes[cluster_id] += 1
        
        print(f"Clustering complete!")
        print(f"  Cluster distribution: {dict(sorted(cluster_sizes.items()))}")
        
        return self.clusters

    def generate_cluster_pairs(self) -> Dict[int, List[Tuple[str, str, int, int]]]:
        """Generate all possible pairs within each cluster"""
        
        if not self.clusters: # self.cluster = requirement indices -> cluster IDs
            print("No clusters available. Run clustering first.")
            return {}
        
        print("Step 3: Generating requirement pairs within each cluster...")
        
        cluster_groups = defaultdict(list)
        for req_idx, cluster_id in self.clusters.items():
            cluster_groups[cluster_id].append(req_idx) # dictionary of cluster_id -> list of requirement indices  1: [0,1],[0,2]
        
        self.cluster_pairs = {}
        total_pairs = 0
        
        for cluster_id, req_indices in cluster_groups.items():
            pairs = []
            # unique pair of indices in that cluster, without repetition or reversed duplicates
            for req_idx1, req_idx2 in itertools.combinations(req_indices, 2):
                req1 = self.requirements[req_idx1]
                req2 = self.requirements[req_idx2]
                pairs.append((req1, req2, req_idx1, req_idx2))
            
            self.cluster_pairs[cluster_id] = pairs
            total_pairs += len(pairs)
            print(f"  Cluster {cluster_id}: {len(req_indices)} requirements  {len(pairs)} pairs")
        
        print(f"Total pairs generated: {total_pairs}")
        return self.cluster_pairs
  
    def analyze_pairs_with_siamese(self) -> Dict[int, List[Dict]]:
        """Analyze requirement pairs using custom trained Siamese BERT"""
        if not self.cluster_pairs:
            print("No requirement pairs available. Generate pairs first.")
            return {}
        
        print("Step 4: Analyzing requirement pairs with custom Siamese BERT...")
        
        self.siamese_results = {}
        
        for cluster_id, pairs in self.cluster_pairs.items():
            print(f"  Analyzing cluster {cluster_id} with {len(pairs)} pairs...")
            cluster_results = []
            
            for req1, req2, idx1, idx2 in pairs:
                result = self._classify_pair(req1, req2, idx1, idx2)
                cluster_results.append(result)
            
            self.siamese_results[cluster_id] = cluster_results
        
        print("Siamese analysis complete!")
        return self.siamese_results

    def _classify_pair(self, req1: str, req2: str, idx1: int, idx2: int) -> Dict:
        """Classify a single requirement pair using pre-computed embeddings"""
        if self.embeddings is None:
            raise ValueError("No embeddings available. Generate embeddings first.")
            
        # Get the pre-computed embeddings for both requirements
        embedding1 = torch.tensor(self.embeddings[idx1]).unsqueeze(0).to(self.device)
        embedding2 = torch.tensor(self.embeddings[idx2]).unsqueeze(0).to(self.device)
        
        # Forward pass through the classification layers only
        with torch.no_grad():
            logits = self.siamese_model.classify_embeddings(embedding1, embedding2)
        
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

    def display_siamese_results(self, show_all: bool = False, min_confidence: float = 0.5):
        """Display Siamese BERT classification results"""
        if not self.siamese_results:
            print("No Siamese results available.")
            return
        
        print(f"\n{'='*100}\nSIAMESE BERT CLASSIFICATION RESULTS\n{'='*100}")
        
        for cluster_id, results in self.siamese_results.items():
            print(f"\n--- Cluster {cluster_id} ---")
            
            if not show_all:
                results = [r for r in results if r['confidence'] >= min_confidence]
            
            class_groups = defaultdict(list)
            for result in results:
                class_groups[result['predicted_class']].append(result)
            
            for class_name, class_results in class_groups.items():
                if class_results:
                    print(f"\n  {class_name.upper()} pairs ({len(class_results)}):")
                    for result in sorted(class_results, key=lambda x: x['confidence'], reverse=True):
                        num1 = self.requirement_numbers[result['idx1']]
                        num2 = self.requirement_numbers[result['idx2']]
                        print(f"    [{result['confidence']:.3f}] Req{num1}  Req{num2}")

    def save_results(self, output_file: str):
        """Save all results to text file"""
        if not self.clusters or not self.siamese_results:
            print("No results to save.")
            return
        
        try:
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write("DIRECT EMBEDDING-TO-CLUSTERING SIAMESE BERT ANALYSIS\n")
                file.write("=" * 80 + "\n\n")
                
                file.write("CLUSTER INFORMATION\n")
                file.write("-" * 40 + "\n")
                cluster_groups = defaultdict(list)
                for req_idx, cluster_id in self.clusters.items():
                    cluster_groups[cluster_id].append(req_idx)
                
                for cluster_id, req_indices in sorted(cluster_groups.items()):
                    file.write(f"\nCluster {cluster_id} ({len(req_indices)} requirements):\n")
                    for idx in sorted(req_indices):
                        num = self.requirement_numbers[idx]
                        file.write(f"  {num}. {self.requirements[idx]}\n")
                
                file.write(f"\n\nSIAMESE BERT CLASSIFICATION RESULTS\n")
                file.write("-" * 40 + "\n")

                for cluster_id, results in self.siamese_results.items():
                    file.write(f"\nCluster {cluster_id} Analysis:\n")
                    
                    class_groups = defaultdict(list)
                    for result in results:
                        class_groups[result['predicted_class']].append(result)
                    
                    for class_name, class_results in class_groups.items():
                        if class_results:
                            file.write(f"\n  {class_name.upper()} pairs ({len(class_results)}):\n")
                            for result in sorted(class_results, key=lambda x: x['confidence'], reverse=True):
                                num1 = self.requirement_numbers[result['idx1']]
                                num2 = self.requirement_numbers[result['idx2']]
                                file.write(f"    [{result['confidence']:.3f}] Req{num1}  Req{num2}\n")
                                file.write(f"      • {result['req1']}\n")
                                file.write(f"      • {result['req2']}\n\n")
            
            print(f"Results saved to: {output_file}")
        except Exception as e:
            print(f"Error saving results: {str(e)}")

    def save_results_json(self, output_file: str):
        """Save all analysis results into structured JSON"""
        if not self.clusters or not self.siamese_results:
            print("No results to save in JSON format.")
            return

        try:
            data = {
                "metadata": {
                    "total_requirements": len(self.requirements),
                    "total_clusters": len(set(self.clusters.values())),
                    "clustering_method": "kmeans_direct"
                },
                "clusters": {},
                "siamese_results": {}
            }

            cluster_groups = defaultdict(list)
            for req_idx, cluster_id in self.clusters.items():
                cluster_groups[cluster_id].append({
                    "req_number": self.requirement_numbers[req_idx],
                    "requirement": self.requirements[req_idx]
                })
            data["clusters"] = {str(k): v for k, v in cluster_groups.items()}

            for cluster_id, results in self.siamese_results.items():
                cluster_data = []
                for result in results:
                    cluster_data.append({
                        "req1_number": self.requirement_numbers[result["idx1"]],
                        "req2_number": self.requirement_numbers[result["idx2"]],
                        "req1_text": result["req1"],
                        "req2_text": result["req2"],
                        "predicted_class": result["predicted_class"],
                        "confidence": result["confidence"],
                        "all_probabilities": result["all_probabilities"]
                    })
                data["siamese_results"][str(cluster_id)] = cluster_data

            json_path = os.path.splitext(output_file)[0] + ".json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            print(f"JSON results saved to: {json_path}")
        except Exception as e:
            print(f"Error saving JSON results: {str(e)}")

    def run_complete_analysis(self, 
                             requirements_file: str,
                             output_file: str = "./results/cluster_time_analysis_results.txt",
                             n_clusters: Optional[int] = None):
        """Run the complete streamlined analysis pipeline"""
        
        print("\n" + "="*80)
        print("STARTING DIRECT EMBEDDING-TO-CLUSTERING ANALYSIS PIPELINE")
        print("="*80 + "\n")
        timings = self.runtime_metrics

        # Step 1: Read requirements
        start = time.time()
        if not self.read_requirements(requirements_file):
            print("Failed to read requirements. Exiting.")
            return
        timings['read_requirements_time'] = time.time() - start

        
        # Step 2: Generate embeddings
        start = time.time()
        if len(self.generate_embeddings()) == 0:
            print("Failed to generate embeddings. Exiting.")
            return
        timings['generate_embeddings_time'] = time.time() - start
        
        # Step 3: Cluster embeddings directly (NO GRAPH)
        start = time.time()
        clusters = self.cluster_embeddings(n_clusters=n_clusters)
        if not clusters:
            print("Failed to cluster requirements.")
            return
        timings['clustering_time'] = time.time() - start
        
        # Step 4: Generate pairs
        start = time.time()
        pairs = self.generate_cluster_pairs()
        if not pairs:
            print("Failed to generate pairs.")
            return
        timings['generate_pairs_time'] = time.time() - start
        
        # Step 5: Analyze with Siamese BERT
        start = time.time()
        siamese_results = self.analyze_pairs_with_siamese()
        if not siamese_results:
            print("Failed to analyze pairs with Siamese BERT.")
            return
        timings['siamese_analysis_time'] = time.time() - start
        
        # Display and save results
        self.display_siamese_results(show_all=False, min_confidence=0.6)
        self.save_results(output_file)
        self.save_results_json(output_file)
        
        print(f"\n{'='*80}\nANALYSIS COMPLETED SUCCESSFULLY\n{'='*80}")
        print(f"Clusters: {len(set(clusters.values()))}")
        print(f"Results saved to: {output_file}")
        # Save timing info at the end
        os.makedirs("./results", exist_ok=True)
        runtime_file = "./results/cluster_time_analysis_results.txt"
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
                    output_file="./results/cluster_results.txt",
                    n_clusters=None
                )
            else:
                print("Error: Analyzer not initialized")
    except Exception as e:
        print(f"Error processing command: {str(e)}")

def test_siamese_model(test_requirements_file: str = None, model_dir: str = 'model'):
    """Test mode: Run full pipeline with sample or provided requirements"""
    global analyzer_instance
    
    print("\n" + "="*80)
    print("RUNNING SIAMESE MODEL TEST")
    print("="*80 + "\n")
    
    try:
        # Initialize analyzer
        analyzer_instance = DirectClusteringSiameseAnalyzer(
            model_dir=model_dir,
            dropout_rate=0.3,
            pooling_strategy='mean'
        )
        
        # Determine requirements file
        if test_requirements_file is None:
            test_requirements_file = "./data/data.json"
        
        if not os.path.exists(test_requirements_file):
            print(f"Error: Requirements file '{test_requirements_file}' not found.")
            print(f"Please provide a valid requirements file or use: python CD-ClusterSiameseAnalyzer.py --test <file_path>")
            return False
        
        # Run complete analysis pipeline
        os.makedirs('./results', exist_ok=True)
        output_file = "./results/test_cluster_results.txt"
        
        analyzer_instance.run_complete_analysis(
            requirements_file=test_requirements_file,
            output_file=output_file,
            n_clusters=None  # Auto-determine optimal clusters
        )
        
        print("\n" + "="*80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")
        return True
        
    except Exception as e:
        print(f"\n[TEST ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    import sys
    global analyzer_instance
    
    # Check if running in test mode
    if '--test' in sys.argv:
        # Check if a test file is provided
        test_file = None
        if len(sys.argv) > 2 and sys.argv[1] == '--test':
            test_file = sys.argv[2]
        test_siamese_model(test_requirements_file=test_file)
        return
    
    # Check if running in initialization mode
    if '--initialize-only' in sys.argv:
        print("Initializing DirectClusteringSiameseAnalyzer in pre-load mode...\n")
        analyzer_instance = DirectClusteringSiameseAnalyzer(
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
    
    print("Initializing Direct Clustering Analyzer for analysis...\n")
    
    os.makedirs('./results', exist_ok=True)
    
    requirements_file = "./data/data.json"
    output_file = "./results/cluster_results.txt"

    if not os.path.exists(requirements_file):
        print(f"Requirements file '{requirements_file}' not found.")
        return

    # Use existing analyzer instance if available
    if analyzer_instance is None:
        analyzer_instance = DirectClusteringSiameseAnalyzer(
            model_dir='model',
            dropout_rate=0.3,
            pooling_strategy='mean'
        )

    # Run analysis with automatic cluster determination
    analyzer_instance.run_complete_analysis(
        requirements_file=requirements_file,
        output_file=output_file,
        n_clusters=None  # Auto-determine based on dataset size
    )


if __name__ == "__main__":
    main()