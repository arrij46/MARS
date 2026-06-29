"""
Configuration module for MARS User Story Generation Pipeline.

This module contains all configuration settings including API keys,
model parameters, and validation settings.
"""
import os
from typing import Optional, List

# ============================================================================
# OPENROUTER API CONFIGURATION - DUAL API SUPPORT
# ============================================================================

# Primary OpenRouter API Key
OPENROUTER_API_KEY_PRIMARY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
# For backward compatibility, also check OPENAI_API_KEY
if not OPENROUTER_API_KEY_PRIMARY:
    OPENROUTER_API_KEY_PRIMARY = os.getenv("OPENAI_API_KEY")

# Secondary OpenRouter API Key (fallback)
OPENROUTER_API_KEY_SECONDARY: Optional[str] = os.getenv("OPENROUTER_API_KEY_SECONDARY")

# Legacy support - map primary key to OPENROUTER_API_KEY for backward compatibility
OPENROUTER_API_KEY = OPENROUTER_API_KEY_PRIMARY

# Build list of available OpenRouter API keys (in priority order)
OPENROUTER_API_KEYS: List[str] = []
if OPENROUTER_API_KEY_PRIMARY:
    OPENROUTER_API_KEYS.append(OPENROUTER_API_KEY_PRIMARY)
if OPENROUTER_API_KEY_SECONDARY:
    OPENROUTER_API_KEYS.append(OPENROUTER_API_KEY_SECONDARY)

# Model configuration
# Default to a reliable model for user stories (structured JSON output required)
# Free options that work well: meta-llama/llama-3.1-8b-instruct:free, qwen/qwen-2-7b-instruct:free
# Paid options (better quality): openai/gpt-4o-mini, openai/gpt-3.5-turbo, google/gemini-flash-1.5
# IMPORTANT: The model MUST support reliable JSON output
GPT_MODEL: str = os.getenv("GPT_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

# OpenRouter endpoint
OPENROUTER_URL: str = "https://openrouter.ai/api/v1"

# Optional OpenRouter headers
OPENROUTER_HTTP_REFERER: Optional[str] = os.getenv("OPENROUTER_HTTP_REFERER")
OPENROUTER_X_TITLE: Optional[str] = os.getenv("OPENROUTER_X_TITLE")

# ============================================================================
# OLLAMA LOCAL MODEL CONFIGURATION
# ============================================================================

# Enable Ollama as final fallback when all OpenRouter APIs fail
ENABLE_OLLAMA_FALLBACK = os.getenv("ENABLE_OLLAMA_FALLBACK", "true").lower() == "true"

# Force use of Ollama instead of OpenRouter (for testing or cost savings)
FORCE_OLLAMA = os.getenv("FORCE_OLLAMA", "false").lower() == "true"

# Ollama server URL
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Ollama model to use (e.g., llama3, llama3:70b, mistral, codellama)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen/qwen2.5:7b")

# Timeout for Ollama API calls (seconds)
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))

# ============================================================================
# BATCH CONFIGURATION - TOKEN-AWARE BATCHING
# ============================================================================

# Rule: (prompt_tokens + max_tokens) < budget for cost efficiency
# Target: ~500-700 prompt tokens per batch
MAX_PROMPT_TOKENS_PER_BATCH: int = 650  # Maximum prompt tokens per batch

# Response token limits (max_tokens in API call)
MAX_RESPONSE_TOKENS: int = 800  # Default/NFR response tokens
FR_MAX_RESPONSE_TOKENS: int = 1200  # FR response tokens (increased for more user stories)

# Batch size limits
MIN_BATCH_SIZE: int = 1  # Minimum requirements per batch (token-aware, not count-aware)
MAX_BATCH_SIZE: int = 30  # Maximum requirements per batch (safety limit for NFR)
FR_MAX_BATCH_SIZE: int = 12  # Maximum requirements per FR batch (10-12 range)
FR_MIN_BATCH_SIZE: int = 10  # Preferred minimum for FR batches (optional, for efficiency)

# ============================================================================
# VALIDATION CONFIGURATION
# ============================================================================

STRICT_VALIDATION: bool = os.getenv("STRICT_VALIDATION", "true").lower() == "true"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
ENABLE_LOGGING: bool = os.getenv("ENABLE_LOGGING", "true").lower() == "true"

# ============================================================================
# RETRY CONFIGURATION
# ============================================================================

MAX_RETRIES: int = 3
RETRY_DELAY: float = 1.0  # seconds

# ============================================================================
# GRACEFUL FALLBACK CONFIGURATION
# ============================================================================

ENABLE_GRACEFUL_FALLBACK: bool = os.getenv("ENABLE_GRACEFUL_FALLBACK", "true").lower() == "true"
# If graceful fallback is enabled, failed batches are deferred instead of crashing

# ============================================================================
# API FALLBACK STRATEGY
# ============================================================================

# Fallback strategy determines the order in which APIs are tried
# Strategy: Primary OpenRouter → Secondary OpenRouter → Ollama (if enabled)
def get_fallback_strategy() -> List[str]:
    """
    Get the list of available API clients in fallback order.
    
    Returns:
        List of API client types: ['openrouter_primary', 'openrouter_secondary', 'ollama']
    """
    strategy = []
    
    # If FORCE_OLLAMA is set, skip all OpenRouter APIs
    if FORCE_OLLAMA:
        if ENABLE_OLLAMA_FALLBACK:
            strategy.append('ollama')
        return strategy
    
    # Add OpenRouter APIs in order
    if OPENROUTER_API_KEY_PRIMARY:
        strategy.append('openrouter_primary')
    if OPENROUTER_API_KEY_SECONDARY:
        strategy.append('openrouter_secondary')
    
    # Add Ollama as final fallback if enabled
    if ENABLE_OLLAMA_FALLBACK:
        strategy.append('ollama')
    
    return strategy


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_config():
    """
    Validate configuration settings.
    
    Raises:
        ValueError: If configuration is invalid
    """
    # Check if at least one API is configured
    if FORCE_OLLAMA:
        if not ENABLE_OLLAMA_FALLBACK:
            raise ValueError(
                "FORCE_OLLAMA is enabled but ENABLE_OLLAMA_FALLBACK is disabled. "
                "Please set ENABLE_OLLAMA_FALLBACK=true"
            )
    else:
        if not OPENROUTER_API_KEYS:
            raise ValueError(
                "No OpenRouter API keys configured. "
                "Please set OPENROUTER_API_KEY and/or OPENROUTER_API_KEY_SECONDARY"
            )
    
    # Validate batch sizes
    if MIN_BATCH_SIZE > MAX_BATCH_SIZE:
        raise ValueError(f"MIN_BATCH_SIZE ({MIN_BATCH_SIZE}) cannot be greater than MAX_BATCH_SIZE ({MAX_BATCH_SIZE})")
    
    if FR_MIN_BATCH_SIZE > FR_MAX_BATCH_SIZE:
        raise ValueError(f"FR_MIN_BATCH_SIZE ({FR_MIN_BATCH_SIZE}) cannot be greater than FR_MAX_BATCH_SIZE ({FR_MAX_BATCH_SIZE})")


# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================

def display_config():
    """Display current configuration (for debugging)."""
    print("=" * 80)
    print("CONFIGURATION SETTINGS")
    print("=" * 80)
    
    # API Configuration
    print("\n[API Configuration]")
    strategy = get_fallback_strategy()
    print(f"  Fallback Strategy: {' → '.join(strategy)}")
    print(f"  Primary OpenRouter API: {'✓ Configured' if OPENROUTER_API_KEY_PRIMARY else '✗ Not configured'}")
    print(f"  Secondary OpenRouter API: {'✓ Configured' if OPENROUTER_API_KEY_SECONDARY else '✗ Not configured'}")
    print(f"  Ollama Fallback: {'✓ Enabled' if ENABLE_OLLAMA_FALLBACK else '✗ Disabled'}")
    print(f"  Force Ollama: {'✓ Yes' if FORCE_OLLAMA else '✗ No'}")
    
    # Model Configuration
    print("\n[Model Configuration]")
    print(f"  OpenRouter Model: {GPT_MODEL}")
    if ENABLE_OLLAMA_FALLBACK or FORCE_OLLAMA:
        print(f"  Ollama Model: {OLLAMA_MODEL}")
        print(f"  Ollama URL: {OLLAMA_BASE_URL}")
    
    # Batch Configuration
    print("\n[Batch Configuration]")
    print(f"  Max Prompt Tokens/Batch: {MAX_PROMPT_TOKENS_PER_BATCH}")
    print(f"  NFR Batch Size: {MIN_BATCH_SIZE}-{MAX_BATCH_SIZE}")
    print(f"  FR Batch Size: {FR_MIN_BATCH_SIZE}-{FR_MAX_BATCH_SIZE}")
    print(f"  NFR Response Tokens: {MAX_RESPONSE_TOKENS}")
    print(f"  FR Response Tokens: {FR_MAX_RESPONSE_TOKENS}")
    
    # Other Settings
    print("\n[Other Settings]")
    print(f"  Strict Validation: {STRICT_VALIDATION}")
    print(f"  Graceful Fallback: {ENABLE_GRACEFUL_FALLBACK}")
    print(f"  Log Level: {LOG_LEVEL}")
    print(f"  Max Retries: {MAX_RETRIES}")
    
    print("=" * 80)


# Auto-validate on import (optional - comment out if not desired)
# validate_config()