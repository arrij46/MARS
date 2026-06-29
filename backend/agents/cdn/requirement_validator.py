"""
requirement_validator.py

Hybrid validation system combining rule-based logic with ML predictions.
Includes RequirementValidator and HybridDecisionEngine classes.
"""

import re
from typing import Dict, Any, List, Tuple, Set


class RequirementValidator:
    """Rule-based validator for requirement pairs"""
    
    # Knowledge bases
    SYN_MAP = {
        "true": "on", "false": "off", 
        "enabled": "on", "disabled": "off",
        "enable": "on", "disable": "off",
        "activated": "on", "deactivated": "off", 
        "activate": "on", "deactivate": "off",
        "active": "on", "inactive": "off",
        "engage": "on", "disengage": "off",
        "illuminate": "on", "light up": "on",
        "start": "on", "stop": "off",
        "milliseconds": "ms", "seconds": "s", "minutes": "min",
        "km/h": "kph",
        "auto": "vehicle", "car": "vehicle",
        "pedal": "brake",
        "system": "", "module": ""
    }
    
    OPPOSITE_STATES = {
        "on": "off", "off": "on",
        "lock": "unlock", "unlock": "lock",
        "open": "close", "close": "open"
    }
    
    STOPWORDS = {
        "the", "a", "an", "must", "shall", "should", "will", "be", "is", "are", 
        "to", "of", "in", "when", "if", "for", "by", "set", "value", "than", 
        "less", "greater", "above", "below", "automatically"
    }
    
    def __init__(self):
        pass
    
    def normalize_token(self, token: str) -> str:
        """Normalize token using synonym map"""
        t = token.lower()
        return self.SYN_MAP.get(t, t)
    
    def get_tokens(self, text: str) -> List[str]:
        """Extract and normalize tokens from text"""
        raw_tokens = re.findall(r"[a-z0-9]+", text.lower())
        return [self.normalize_token(t) for t in raw_tokens if t not in self.STOPWORDS]
    
    def parse_number_and_unit(self, text: str) -> List[Tuple[float, str]]:
        """Extract numbers and their units from text"""
        matches = re.findall(r"(-?\d+(?:\.\d+)?)\s*([a-z%°/]+)?", text.lower())
        results = []
        for val_str, unit_str in matches:
            try:
                val = float(val_str)
                unit = unit_str.strip() if unit_str else ""
                
                # Normalize units
                if unit in ["ms", "msec"]: 
                    val /= 1000.0
                    unit = "s"
                elif unit in ["s", "sec", "seconds"]: 
                    unit = "s"
                elif unit in ["km/h", "kph"]: 
                    val /= 3.6
                    unit = "m/s"
                    
                results.append((val, unit))
            except ValueError: 
                continue
        return results
    
    def extract_entities(self, tokens: List[str]) -> Set[str]:
        """
        Extract significant nouns/entities from tokens.
        Fixes issue with 'Vehicle locks door' vs 'Door lock engages'
        by capturing all relevant entities.
        """
        exclude = set(self.SYN_MAP.values()).union(
            set(self.OPPOSITE_STATES.keys())
        ).union(self.STOPWORDS)
        
        entities = set()
        for t in tokens:
            if not t.isdigit() and t not in exclude and len(t) > 2:
                entities.add(t)
        return entities
    
    def extract_state(self, text: str, tokens: List[str]) -> str:
        """
        Detect binary states (on/off, lock/unlock).
        Returns the most relevant state found.
        """
        found_states = []
        for t in tokens:
            if t in ["on", "off"]:
                found_states.append(t)
            elif t in self.OPPOSITE_STATES:
                found_states.append(t)
        
        # Return last state found (usually the target state)
        return found_states[-1] if found_states else None
    
    def validate_pair(self, req1_text: str, req2_text: str) -> Tuple[str, str]:
        """
        Validate a requirement pair using rule-based logic.
        
        Args:
            req1_text: First requirement text
            req2_text: Second requirement text
            
        Returns:
            Tuple of (label, reason) where label is one of:
            - 'duplicate': Requirements are essentially the same
            - 'conflict': Requirements contradict each other
            - 'soft_conflict': Requirements have subtle differences
            - 'neutral': Requirements are unrelated or unclear
        """
        # Parse both requirements
        tokens1 = self.get_tokens(req1_text)
        tokens2 = self.get_tokens(req2_text)
        
        entities1 = self.extract_entities(tokens1)
        entities2 = self.extract_entities(tokens2)
        
        state1 = self.extract_state(req1_text, tokens1)
        state2 = self.extract_state(req2_text, tokens2)
        
        numbers1 = self.parse_number_and_unit(req1_text)
        numbers2 = self.parse_number_and_unit(req2_text)
        
        # 1. Entity Intersection Check
        # If no shared entities, requirements are likely unrelated
        intersection = entities1.intersection(entities2)
        if not intersection:
            return "neutral", f"No shared context (Entities: {entities1} vs {entities2})"
        
        # 2. Numeric Check (High Priority)
        if numbers1 and numbers2:
            n1, u1 = numbers1[0]
            n2, u2 = numbers2[0]
            
            # Check unit compatibility
            if u1 != u2:
                return "soft_conflict", f"Unit mismatch: {u1} vs {u2}"
            
            # Check numeric values
            diff = abs(n1 - n2)
            if diff == 0:
                return "duplicate", f"Identical values ({n1} {u1}) and shared context {intersection}"
            elif diff / max(abs(n1), 0.001) < 0.2:  # Less than 20% difference
                return "soft_conflict", f"Values close but different: {n1} vs {n2}"
            else:
                return "conflict", f"Numeric contradiction: {n1} vs {n2}"
        
        # 3. State Logic (Positive & Negative)
        if state1 and state2:
            # Direct conflict (on vs off, lock vs unlock)
            if self.OPPOSITE_STATES.get(state1) == state2:
                return "conflict", f"Direct contradiction: {state1} vs {state2}"
            
            # State agreement (both say 'on', both say 'lock')
            if state1 == state2:
                return "duplicate", f"Same state action ('{state1}') on shared entities {intersection}"
        
        # 4. Vocabulary Overlap (Jaccard Similarity)
        u_len = len(tokens1) + len(tokens2)
        if u_len > 0:
            shared_tokens = set(tokens1).intersection(set(tokens2))
            overlap_score = 2 * len(shared_tokens) / u_len
            
            if overlap_score > 0.65:
                return "duplicate", f"High vocabulary overlap ({overlap_score:.2f}) on shared context"
        
        # 5. Multiple Shared Entities (Strong Context Match)
        if len(intersection) >= 2:
            return "duplicate", f"Multiple shared entities {intersection} implies same requirement intent"
        
        # Default: Requirements share context but no clear logic triggered
        return "neutral", "Shared entities found, but no clear duplication or conflict logic triggered"


class HybridDecisionEngine:
    """
    Combines ML predictions with rule-based validation to produce final labels.
    
    Decision Logic:
    1. Both say "duplicate" → duplicate
    2. Both say "conflict" (including soft_conflict from validator) → conflict
    3. They disagree → neutral
    """
    
    @staticmethod
    def make_final_decision(ml_label: str, validator_label: str) -> Tuple[str, str]:
        """
        Apply hybrid decision logic to combine ML and validator predictions.
        
        Args:
            ml_label: Prediction from ML model ('duplicate', 'conflict', or 'neutral')
            validator_label: Prediction from rule validator ('duplicate', 'conflict', 
                           'soft_conflict', or 'neutral')
        
        Returns:
            Tuple of (final_label, reason) explaining the decision
        """
        ml = ml_label.lower()
        val = validator_label.lower()
        
        # Rule 1: Both agree on duplicate
        if ml == "duplicate" and val == "duplicate":
            return "duplicate", "Both ML and validator agree: DUPLICATE"
        
        # Rule 2: Both agree on conflict
        # Note: validator's 'soft_conflict' counts as agreement with ML 'conflict'
        if ml == "conflict" and val in ["conflict", "soft_conflict"]:
            return "conflict", "Both ML and validator agree: CONFLICT"
        
        # Rule 3: All disagreements result in neutral
        # This includes:
        # - ml: conflict, validator: duplicate
        # - ml: duplicate, validator: conflict
        # - ml: conflict, validator: neutral
        # - ml: duplicate, validator: neutral
        # - validator: soft_conflict but ml says duplicate
        # - validator: duplicate but ml says conflict
        return "neutral", f"ML and validator disagree (ML: {ml}, Validator: {val}) → NEUTRAL"
    
    @staticmethod
    def validate_and_correct_results(siamese_results: dict, validator: RequirementValidator) -> dict:
        """
        Apply validation to all ML predictions and produce corrected output.
        
        Args:
            siamese_results: Dictionary with cluster IDs as keys, each containing list of pairs
            validator: Instance of RequirementValidator
        
        Returns:
            Same structure as input but with corrected labels and validation info
        """
        print(f"[Validator] Starting validation process...")
        corrected_results = {}
        total_validated = 0
        corrections_made = 0
        
        for cluster_id, pairs in siamese_results.items():
            corrected_pairs = []
            
            for pair in pairs:
                req1_text = pair.get("req1","")
                req2_text = pair.get("req2","")
                ml_label = pair.get("predicted_class", "neutral")
                
                # Run validator
                validator_label, validator_reason = validator.validate_pair(req1_text, req2_text)
                
                # Make final decision
                final_label, decision_reason = HybridDecisionEngine.make_final_decision(
                    ml_label, validator_label
                )
                
                # Track statistics
                total_validated += 1
                if final_label != ml_label:
                    corrections_made += 1
                
                # Build corrected pair result (same format as original)
                corrected_pair = {
                    "idx1": pair.get("idx1"),
                    "idx2": pair.get("idx2"),
                    "req1": req1_text,
                    "req2": req2_text,
                    "predicted_class": final_label,  # CORRECTED LABEL
                    "confidence": pair.get("confidence", 0.0),
                    "all_probabilities": pair.get("all_probabilities", {}),
                    "validation_info": {
                        "original_ml_label": ml_label,
                        "validator_label": validator_label,
                        "validator_reason": validator_reason,
                        "final_label": final_label,
                        "decision_reason": decision_reason,
                        "was_corrected": final_label != ml_label
                    }
                }
                
                corrected_pairs.append(corrected_pair)
            
            corrected_results[cluster_id] = corrected_pairs
        
        print(f"[Validator] Validation complete: {total_validated} pairs validated, {corrections_made} corrections made")
        return corrected_results