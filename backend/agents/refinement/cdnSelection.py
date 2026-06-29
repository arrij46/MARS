"""
cdn_selector.py
Complete CDN Selection Module for resolving conflicts and duplicates
using TF-IDF and cosine similarity.
"""

import re
import string
import json
from typing import List, Dict, Set, Tuple
from collections import defaultdict

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet', quiet=True)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)


class CDNSelector:
    """
    A requirement refinement selector that resolves conflicts and duplicates
    using TF-IDF and cosine similarity against a project description.
    """
    
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.vectorizer = TfidfVectorizer()
        
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text by:
        1. Converting to lowercase
        2. Removing punctuation
        3. Tokenizing
        4. Removing stopwords
        5. Lemmatizing
        
        Args:
            text: Input text string
            
        Returns:
            Preprocessed text string
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords and lemmatize
        processed_tokens = [
            self.lemmatizer.lemmatize(token)
            for token in tokens
            if token not in self.stop_words and len(token) > 2
        ]
        
        return ' '.join(processed_tokens)
    
    def calculate_similarity(self, req_text: str, project_description: str) -> float:
        """
        Calculate cosine similarity between a requirement and project description
        using TF-IDF vectors.
        
        Args:
            req_text: Requirement text
            project_description: Project description text
            
        Returns:
            Similarity score between 0 and 1
        """
        # Preprocess both texts
        processed_req = self.preprocess_text(req_text)
        processed_desc = self.preprocess_text(project_description)
        
        # Handle empty strings after preprocessing
        if not processed_req or not processed_desc:
            return 0.0
        
        # Create TF-IDF vectors
        try:
            tfidf_matrix = self.vectorizer.fit_transform([processed_req, processed_desc])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            return 0.0
    
    def resolve_conflicts(
        self, 
        conflict_sets: List[List[Dict]], 
        project_description: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Resolve conflicts by selecting the requirement most similar to the
        project description from each conflict set.
        
        Args:
            conflict_sets: List of conflict groups, where each group is a list of requirements
            project_description: The project description text
            
        Returns:
            Tuple of (selected_requirements, rejected_requirements)
        """
        selected = []
        rejected = []
        
        print("\n" + "="*80)
        print("RESOLVING CONFLICTS")
        print("="*80)
        
        for idx, conflict_group in enumerate(conflict_sets, 1):
            print(f"\n--- Conflict Group {idx} ({len(conflict_group)} requirements) ---")
            
            best_req = None
            best_score = -1
            scores = []
            
            for req in conflict_group:
                req_text = req.get('text', req.get('description', ''))
                req_id = req.get('id', req.get('req_id', 'unknown'))
                
                similarity = self.calculate_similarity(req_text, project_description)
                scores.append((req, similarity, req_id))
                
                print(f"  Req ID: {req_id} | Similarity: {similarity:.4f}")
                
                if similarity > best_score:
                    best_score = similarity
                    best_req = req
            
            # Select winner
            if best_req:
                selected.append(best_req)
                best_id = best_req.get('id', best_req.get('req_id', 'unknown'))
                print(f"  ✓ SELECTED: Req ID {best_id} (Score: {best_score:.4f})")
                
                # Add rejected requirements
                for req, score, req_id in scores:
                    if req != best_req:
                        rejected.append(req)
                        print(f"  ✗ REJECTED: Req ID {req_id} (Score: {score:.4f})")
        
        print(f"\nConflict Resolution Summary: {len(selected)} selected, {len(rejected)} rejected")
        return selected, rejected
    
    def resolve_duplicates(
        self, 
        duplicate_sets: List[List[Dict]], 
        project_description: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Resolve duplicates by selecting the most representative requirement
        (highest similarity to project description) from each duplicate set.
        
        Args:
            duplicate_sets: List of duplicate groups, where each group is a list of requirements
            project_description: The project description text
            
        Returns:
            Tuple of (selected_requirements, rejected_requirements)
        """
        selected = []
        rejected = []
        
        print("\n" + "="*80)
        print("RESOLVING DUPLICATES")
        print("="*80)
        
        for idx, duplicate_group in enumerate(duplicate_sets, 1):
            print(f"\n--- Duplicate Group {idx} ({len(duplicate_group)} requirements) ---")
            
            best_req = None
            best_score = -1
            scores = []
            
            for req in duplicate_group:
                req_text = req.get('text', req.get('description', ''))
                req_id = req.get('id', req.get('req_id', 'unknown'))
                
                similarity = self.calculate_similarity(req_text, project_description)
                scores.append((req, similarity, req_id))
                
                print(f"  Req ID: {req_id} | Similarity: {similarity:.4f}")
                
                if similarity > best_score:
                    best_score = similarity
                    best_req = req
            
            # Select representative
            if best_req:
                selected.append(best_req)
                best_id = best_req.get('id', best_req.get('req_id', 'unknown'))
                print(f"  ✓ SELECTED: Req ID {best_id} (Score: {best_score:.4f})")
                
                # Add rejected duplicates
                for req, score, req_id in scores:
                    if req != best_req:
                        rejected.append(req)
                        print(f"  ✗ REJECTED: Req ID {req_id} (Score: {score:.4f})")
        
        print(f"\nDuplicate Resolution Summary: {len(selected)} selected, {len(rejected)} rejected")
        return selected, rejected
    
    def refine(
        self,
        requirements: List[Dict],
        conflicts: List[List[Dict]],
        duplicates: List[List[Dict]],
        project_description: str
    ) -> List[Dict]:
        """
        Refine requirements by resolving conflicts and duplicates.
        
        Args:
            requirements: Complete list of all requirements
            conflicts: List of conflict groups
            duplicates: List of duplicate groups
            project_description: Project description text
            
        Returns:
            Refined list of requirements
        """
        print("\n" + "="*80)
        print("REQUIREMENT REFINEMENT PROCESS")
        print("="*80)
        print(f"Total Requirements: {len(requirements)}")
        print(f"Conflict Groups: {len(conflicts)}")
        print(f"Duplicate Groups: {len(duplicates)}")
        
        # Resolve conflicts
        conflict_selected, conflict_rejected = self.resolve_conflicts(conflicts, project_description)
        
        # Resolve duplicates
        duplicate_selected, duplicate_rejected = self.resolve_duplicates(duplicates, project_description)
        
        # Build set of all requirement IDs involved in conflicts or duplicates
        involved_ids = set()
        for group in conflicts:
            for req in group:
                req_id = req.get('id', req.get('req_id'))
                if req_id:
                    involved_ids.add(req_id)
        
        for group in duplicates:
            for req in group:
                req_id = req.get('id', req.get('req_id'))
                if req_id:
                    involved_ids.add(req_id)
        
        # Collect requirements not involved in any conflict or duplicate
        untouched = []
        for req in requirements:
            req_id = req.get('id', req.get('req_id'))
            if req_id not in involved_ids:
                untouched.append(req)
        
        # Combine all selected requirements
        refined_requirements = conflict_selected + duplicate_selected + untouched
        
        print("\n" + "="*80)
        print("REFINEMENT SUMMARY")
        print("="*80)
        print(f"Selected from Conflicts: {len(conflict_selected)}")
        print(f"Selected from Duplicates: {len(duplicate_selected)}")
        print(f"Untouched Requirements: {len(untouched)}")
        print(f"Total Refined Requirements: {len(refined_requirements)}")
        print(f"Total Rejected: {len(conflict_rejected) + len(duplicate_rejected)}")
        print("="*80 + "\n")
        
        return refined_requirements


# Example usage and testing
if __name__ == "__main__":
    # Sample data
    project_description = """
    An e-commerce platform that allows users to browse products, add them to cart,
    and complete purchases securely. The system should support user authentication,
    product search, and order tracking.
    """
    
    requirements = [
        {"id": "REQ-001", "text": "The system shall allow users to search for products by name"},
        {"id": "REQ-002", "text": "Users must be able to add products to shopping cart"},
        {"id": "REQ-003", "text": "The system should support secure payment processing"},
        {"id": "REQ-004", "text": "Users shall be able to track their orders"},
        {"id": "REQ-005", "text": "The platform must authenticate users before purchase"},
        {"id": "REQ-006", "text": "System shall provide product search functionality"},
        {"id": "REQ-007", "text": "Users can view their order history"},
        {"id": "REQ-008", "text": "The application must handle user login securely"},
    ]
    
    # Conflicts: REQ-003 vs REQ-005 (both about security)
    conflicts = [
        [
            {"id": "REQ-003", "text": "The system should support secure payment processing"},
            {"id": "REQ-005", "text": "The platform must authenticate users before purchase"}
        ]
    ]
    
    # Duplicates: REQ-001 vs REQ-006 (both about product search)
    duplicates = [
        [
            {"id": "REQ-001", "text": "The system shall allow users to search for products by name"},
            {"id": "REQ-006", "text": "System shall provide product search functionality"}
        ]
    ]
    
    # Run refinement
    selector = CDNSelector()
    refined = selector.refine(requirements, conflicts, duplicates, project_description)
    
    print("\n📋 FINAL REFINED REQUIREMENTS:")
    for req in refined:
        print(f"  - {req['id']}: {req['text']}")