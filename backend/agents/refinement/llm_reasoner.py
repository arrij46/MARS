"""
llm_reasoner.py — LLM wrapper.

Responsibilities:
  - fix_grammar()   : correct grammar on a flat list of raw atomic strings.
                      This is the ONLY LLM call needed in the atomisation pipeline.
  - query()         : legacy full-atomisation endpoint (kept for compatibility).
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List

load_dotenv()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AtomicResult(BaseModel):
    original_id: str
    original_text: str
    was_compound: bool
    atomic_statements: List[str]


class AtomizationResponse(BaseModel):
    results: List[AtomicResult]


class GrammarFixResponse(BaseModel):
    """
    Input  : list of {"index": int, "text": str}
    Output : same list with corrected text.
    """
    corrected: List[str]


# ---------------------------------------------------------------------------
# LLMReasoner
# ---------------------------------------------------------------------------

class LLMReasoner:
    def __init__(
        self,
        model_name: str = "llama-3.3-70b-versatile",
        temperature: float = 0,
        max_tokens: int = 4096,
    ):
        self.client     = Groq(api_key=os.getenv("GROQ_API_KEY_REFINEMENT_ACCOUNT3"))
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens  = max_tokens

    # ------------------------------------------------------------------
    # PRIMARY method: grammar correction only
    # ------------------------------------------------------------------

    def fix_grammar(self, statements: list[str]) -> list[str]:

        if not statements:
            return []

        # Index each statement so the LLM can't reorder or drop items
        indexed = [{"index": i, "text": s} for i, s in enumerate(statements)]

        system_prompt = """You are a technical writing assistant specialised in software requirements.

Your ONLY task: correct the grammar of each requirement string so it reads naturally and professionally.

Rules (STRICTLY follow all):
1. Return a JSON object with ONE key: "corrected" — a JSON array of strings.
2. The array MUST contain EXACTLY the same number of items as the input array, in the same order.
3. Each output string corresponds to the input item with the matching "index".
4. Fix grammar, capitalisation, and phrasing ONLY. Do NOT add, remove, or merge information.
5. Keep the subject and modal intact (e.g., "The system shall …" must stay as-is).
6. If a string is already grammatically correct, repeat it unchanged.
7. Each statement should make complete sense on its own as a standalone requirement in terms of grammar.
8. Output ONLY the JSON object — no markdown fences, no explanation."""

        user_msg = (
            "Fix the grammar of each requirement below. "
            "Return a JSON object {\"corrected\": [\"...\", \"...\", ...]} "
            "with EXACTLY the same number of strings as the input.\n\n"
            + json.dumps(indexed, indent=2)
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ]

        raw = self._call_api(messages)

        # Parse and validate length
        try:
            parsed = json.loads(raw)
            corrected: list[str] = parsed["corrected"]
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"[LLMReasoner] Grammar-fix parse error: {exc}. Returning originals.")
            return statements

        if len(corrected) != len(statements):
            print(
                f"[LLMReasoner] WARNING: grammar-fix returned {len(corrected)} items "
                f"but expected {len(statements)}. Padding with originals."
            )
            # Pad or truncate to guarantee same length
            corrected = corrected[: len(statements)]
            while len(corrected) < len(statements):
                corrected.append(statements[len(corrected)])

        return corrected

    # ------------------------------------------------------------------
    # LEGACY method: full atomisation via LLM (kept for compatibility)
    # ------------------------------------------------------------------

    def query(self, input_data: list) -> AtomizationResponse:
        """
        Legacy: send requirements to the LLM and ask it to atomise them.
        Prefer using atomic.py + fix_grammar() instead.
        """
        if not isinstance(input_data, list):
            raise ValueError("Input must be a list of requirement dicts.")

        system_prompt = """You are a requirements engineer. Break any compound requirements into atomic statements.

Return ONLY valid JSON:
{
  "results": [
    {
      "original_id": "REQ-5",
      "original_text": "...",
      "was_compound": true,
      "atomic_statements": ["...", "..."]
    }
  ]
}

Rules:
- Every input requirement MUST appear in results, even if not compound.
- If not compound, set was_compound=false and repeat the original text unchanged.
- Never drop, merge, or reorder requirements."""

        user_msg = (
            "Break the following requirements into atomic statements.\n\n"
            + json.dumps(input_data, indent=2)  
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ]

        raw = self._call_api(messages)
        return AtomizationResponse.model_validate_json(raw)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_api(self, messages: list, response_format: dict | None = None) -> str:
        kwargs = dict(
            messages=messages,
            temperature=self.temperature,
            max_completion_tokens=self.max_tokens,
            stream=False,
            top_p=0.9,
            response_format={"type": "json_object"},
        )

        def _try(model):
            return self.client.chat.completions.create(model=model, **kwargs)

        try:
            completion = _try(self.model_name)
        except Exception as exc:
            print(f"[LLMReasoner] Primary model failed ({exc}), falling back.")
            completion = _try("llama-3.1-8b-instant")

        return completion.choices[0].message.content

    def __call__(self, input_data):
        return self.query(input_data)