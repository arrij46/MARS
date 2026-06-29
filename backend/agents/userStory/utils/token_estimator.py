"""
Token estimation utilities.
"""
import tiktoken

class TokenEstimator:
    """Estimate token counts for text."""
    
    def __init__(self, model: str = "gpt-4"):
        try:
            self.encoder = tiktoken.encoding_for_model(model)
        except:
            self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate number of tokens in text."""
        if not text:
            return 0
        return len(self.encoder.encode(text))