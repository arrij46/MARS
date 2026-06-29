"""
atomic.py — NLP-based requirement atomizer.

Splits compound requirements into atomic statements.
Uses regex-first strategies (reliable for modal requirement patterns),
with spaCy as a supplementary pass for dependency-based splits.
Does NOT call any LLM. Grammar correction is handled separately.
"""

import re
import spacy
import nltk
from nltk.tokenize import sent_tokenize

nltk.download("punkt",     quiet=True)
nltk.download("punkt_tab", quiet=True)
nlp = spacy.load("en_core_web_sm")

# Modals used in requirement statements
_MODALS = r"(?:shall|should|must|will|can|may|would|could)"


# ---------------------------------------------------------------------------
# Prefix extraction & fragment reconstruction
# ---------------------------------------------------------------------------

def _extract_prefix(clause: str) -> str:
    """
    Return 'subject + modal [+ be]' prefix from a requirement clause.
      "The system should be easy to use"  ->  "The system should be"
      "The system shall allow users"      ->  "The system shall"
    Returns "" when no modal prefix is found.
    """
    m = re.match(
        rf"^((?:the|a|an)\s+[\w\s]{{1,30}}?\s+{_MODALS}(?:\s+not)?(?:\s+be)?)\b",
        clause,
        re.IGNORECASE,
    )
    return m.group(1).strip() if m else ""


def _needs_prefix(fragment: str) -> bool:
    """True if the fragment is an orphaned predicate lacking a subject."""
    return not re.match(
        r"^(?:the|a|an|it|they|he|she|this|that|its)\b",
        fragment.strip(),
        re.IGNORECASE,
    )


def _reattach(fragments: list, original: str) -> list:
    """Prepend subject+modal to any orphaned predicate fragments."""
    prefix = _extract_prefix(original)
    if not prefix:
        return fragments
    return [
        f"{prefix} {f}" if _needs_prefix(f) else f
        for f in fragments
    ]


# ---------------------------------------------------------------------------
# Regex splitting (primary)
# ---------------------------------------------------------------------------

_ADJ_SUFFIX = r"[a-z]+(?:ible|able|ive|ent|ant|ful|less|ous|ic)\b"

_REQ_VERBS = (
    r"be\b|been\b|being\b|"
    r"register|handle|support|provide|allow|protect|scale|store|log|send|"
    r"display|use|validate|process|generate|ensure|maintain|enforce|encrypt|"
    r"monitor|notify|track|manage|accept|reject|limit|prevent|detect|respond|"
    r"return|redirect|authenticate|authorize|include|contain|require|enable|"
    r"disable|show|hide|create|update|delete|read|write|export|import|upload|"
    r"download|search|filter|sort|paginate|cache|queue|schedule|trigger|emit"
)

_REQ_ADJS = (
    r"able|easy|hard|likely|possible|required|designed|intended|"
    r"available|accessible|secure|scalable|responsive|reliable|"
    r"accurate|consistent|compatible|extensible|maintainable|"
    r"auditable|recoverable|high.performance|"
    r"user.friendly|intuitive|performant|robust|stable|modular|"
    r"pretty|fast|slow|simple|complex|flexible|portable|testable"
)

_PREDICATE_LOOKAHEAD = rf"(?:not\s+)?(?:{_REQ_VERBS}|{_REQ_ADJS}|{_ADJ_SUFFIX})"

_PREDICATE_AND = re.compile(
    rf"\s+and\s+(?={_PREDICATE_LOOKAHEAD})",
    re.IGNORECASE,
)


# atomic.py — updated sections only

# ---------------------------------------------------------------------------
# UPDATED: Regex splitting (primary)
# ---------------------------------------------------------------------------

# Matches: "and [optional subject phrase] modal"
# e.g. "and the system shall", "and it must", "and users should"
_REPEATED_SUBJECT_MODAL = re.compile(
    rf"\s+and\s+(?=(?:the|a|an|it|they|this|that)?(?:\s+[\w]+){{0,4}}\s*{_MODALS}\b)",
    re.IGNORECASE,
)

def _regex_split(clause: str) -> list:
    """
    Three-pass regex split:
      1. Repeated modal (with optional subject): "shall X and the system shall Y"
      2. Predicate 'and':  "shall be easy and responsive and secure"
      3. Comma list:       "shall X, Y, and Z"
    """
    # Pass 1 — repeated modal (now catches "and the system shall", "and it must", etc.)
    parts = _REPEATED_SUBJECT_MODAL.split(clause)
    if len(parts) > 1:
        parts = [p.strip() for p in parts if p.strip()]
        # Each part after the first may be missing its subject — reattach only if needed
        result = [parts[0]]
        for part in parts[1:]:
            # If this part already starts with a subject, keep it as-is
            if re.match(r"^(?:the|a|an|it|they|this|that)\b", part, re.IGNORECASE):
                result.append(part)
            else:
                # Orphaned predicate — reattach prefix from original
                prefix = _extract_prefix(clause)
                result.append(f"{prefix} {part}" if prefix else part)
        return result

    # Pass 2 — predicate "and"  (unchanged)
    positions = [m.start() for m in _PREDICATE_AND.finditer(clause)]
    if positions:
        parts = []
        prev = 0
        for pos in positions:
            parts.append(clause[prev:pos].strip().rstrip(",;"))
            connector = re.match(r"\s+and\s+", clause[pos:], re.IGNORECASE)
            prev = pos + len(connector.group())
        parts.append(clause[prev:].strip())
        parts = [p for p in parts if p.strip()]
        if len(parts) > 1:
            return parts

    # Pass 3 — comma/semicolon list  (unchanged)
    if re.search(r",\s*(?:and|or)\s*", clause, re.IGNORECASE):
        normalised = re.sub(r",\s*(and|or)\s*", " __AND__ ", clause, flags=re.IGNORECASE)
        parts = normalised.split(" __AND__ ")
        parts = [p.strip().rstrip(",;") for p in parts if p.strip()]
        if len(parts) > 1:
            return parts

    return [clause]
# ---------------------------------------------------------------------------
# spaCy splitting (supplementary)
# ---------------------------------------------------------------------------

def _spacy_split(clause: str) -> list:
    """Dependency-based split for non-standard structures."""
    doc = nlp(clause)
    split_indices = set()

    for token in doc:
        if token.dep_ != "conj":
            continue
        head = token.head
        visited = set()
        while head.i not in visited:
            visited.add(head.i)
            if head.pos_ in {"VERB", "AUX"}:
                break
            if head.i == head.head.i:
                break
            head = head.head

        if head.pos_ not in {"VERB", "AUX"}:
            continue

        cc = (
            next((t for t in token.lefts if t.dep_ == "cc"), None)
            or next((t for t in doc if t.dep_ == "cc" and t.head.i == token.i), None)
        )
        if cc:
            split_indices.add(cc.idx)

    if not split_indices:
        return [clause]

    parts = []
    prev = 0
    for char_idx in sorted(split_indices):
        parts.append(clause[prev:char_idx].strip().rstrip(",;"))
        prev = char_idx
    tail = clause[prev:].strip()
    tail = re.sub(r"^(?:and|or)\s+", "", tail, flags=re.IGNORECASE)
    parts.append(tail)
    return [p for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Combined split with recursion
# ---------------------------------------------------------------------------

def _split_once(clause: str) -> list:
    """One round: regex first, spaCy fallback."""
    parts = _regex_split(clause)
    if len(parts) > 1:
        return _reattach(parts, clause)
    parts = _spacy_split(clause)
    if len(parts) > 1:
        return _reattach(parts, clause)
    return [clause]


def _split_on_conjunctions(clause: str) -> list:
    """Recursively split until no further splits are found."""
    parts = _split_once(clause)
    if len(parts) == 1:
        return parts
    result = []
    for part in parts:
        result.extend(_split_on_conjunctions(part))
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class AtomicStatementGenerator:
    """
    Splits requirements into atomic statements using regex + NLP (no LLM).
    Grammar correction is handled separately by LLMReasoner.fix_grammar().
    """

    def make_atomic(self, requirement) -> list:
        if isinstance(requirement, list):
            combined = " ".join(r for r in requirement if isinstance(r, str))
        elif isinstance(requirement, str):
            combined = requirement
        else:
            raise TypeError(f"Expected str or list[str], got {type(requirement)}")

        sentences = sent_tokenize(combined)
        atomic = []
        for sent in sentences:
            for clause in _split_on_conjunctions(sent):
                if clause.strip():
                    atomic.append(clause.strip())
        return atomic

    def process_requirements(self, requirements: list) -> list:
        results = []
        for req in requirements:
            req_id   = req.get("req_id") or req.get("id")
            text     = req.get("text", "").strip()
            atomized = self.make_atomic(text)
            results.append({
                "original_id":       str(req_id),
                "original_text":     text,
                "was_compound":      len(atomized) > 1,
                "atomic_statements": atomized,
            })
        return results
# """
# atomic.py — NLP-based requirement atomizer.

# Splits compound requirements into atomic statements using spaCy + NLTK.
# Does NOT call any LLM. Grammar correction is handled separately.
# """

# import re
# import spacy
# import nltk
# from nltk.tokenize import sent_tokenize

# nltk.download("punkt", quiet=True)
# nltk.download("punkt_tab", quiet=True)
# nlp = spacy.load("en_core_web_sm")


# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# def _split_once(clause: str) -> list[str]:
#     """
#     Attempt one round of splitting on a single clause.
#     Returns a list with >1 item if a split was found, else [clause].
#     """
#     clause = clause.strip()
#     doc = nlp(clause)

#     # ------------------------------------------------------------------
#     # Strategy 1 — spaCy dependency parse: conjoined predicates.
#     # Broadened to catch ADJ/NOUN conjuncts (e.g. "accessible") whose
#     # head chain leads back to a VERB/AUX modal.
#     # ------------------------------------------------------------------
#     split_indices = []
#     for token in doc:
#         if token.dep_ == "conj":
#             # Walk up the head chain to find a verbal/modal anchor
#             head = token.head
#             visited = set()
#             while head.i not in visited:
#                 visited.add(head.i)
#                 if head.pos_ in {"VERB", "AUX"}:
#                     break
#                 if head == head.head:
#                     break
#                 head = head.head

#             if head.pos_ in {"VERB", "AUX"}:
#                 # "cc" sitting as a left child of this conj token
#                 cc = next((t for t in token.lefts if t.dep_ == "cc"), None)
#                 # fallback: "cc" whose head is this conj token
#                 if cc is None:
#                     cc = next(
#                         (t for t in doc if t.dep_ == "cc" and t.head.i == token.i),
#                         None,
#                     )
#                 if cc:
#                     split_indices.append(cc.idx)

#     if split_indices:
#         parts = []
#         prev = 0
#         for idx in sorted(set(split_indices)):
#             parts.append(clause[prev:idx].strip().rstrip(",;"))
#             prev = idx
#         tail = clause[prev:].strip()
#         tail = re.sub(r"^(and|or)\s+", "", tail, flags=re.IGNORECASE)
#         parts.append(tail)
#         parts = [p for p in parts if p]
#         if len(parts) > 1:
#             return parts

#     # ------------------------------------------------------------------
#     # Strategy 2 — explicit "shall/should/must … and shall/should/must …"
#     # Catches cases where spaCy misparses the dependency tree.
#     # ------------------------------------------------------------------
#     modal_split = re.split(
#         r"\s+and\s+(?=(?:shall|should|must|will|can|may)\b)",
#         clause,
#         flags=re.IGNORECASE,
#     )
#     if len(modal_split) > 1:
#         return [p.strip() for p in modal_split if p.strip()]

#     # ------------------------------------------------------------------
#     # Strategy 3 — comma/semicolon list when there are multiple verbs
#     # ------------------------------------------------------------------
#     verbs = [t for t in doc if t.pos_ in {"VERB", "AUX"} and t.dep_ != "aux"]
#     if len(verbs) > 1:
#         pattern = r"\s*(?:,\s*(?:and|or)\s*|;\s*(?:and|or)\s*|,\s*|;\s*)"
#         parts = re.split(pattern, clause)
#         parts = [p.strip() for p in parts if p.strip()]
#         if len(parts) > 1:
#             return parts

#     # ------------------------------------------------------------------
#     # Strategy 4 — comma-separated enumeration with Oxford "and/or"
#     # e.g. "…reset password, update profile, and upload avatar"
#     # ------------------------------------------------------------------
#     if re.search(r",\s*(?:and|or)\s*", clause, re.IGNORECASE):
#         normalised = re.sub(r",\s*(and|or)\s*", r" \1 ", clause, flags=re.IGNORECASE)
#         parts = re.split(r"\s+(?:and|or)\s+", normalised, flags=re.IGNORECASE)
#         parts = [p.strip().rstrip(",;") for p in parts if p.strip()]
#         if len(parts) > 1:
#             return parts

#     return [clause]


# def _split_on_conjunctions(clause: str) -> list[str]:
#     """
#     Recursively split a clause until no further splits are found.
#     Ensures nested compound statements are fully decomposed.
#     """
#     parts = _split_once(clause)
#     if len(parts) == 1:
#         return parts

#     result = []
#     for part in parts:
#         result.extend(_split_on_conjunctions(part))
#     return result


# def _prefix_for(clause: str, original: str) -> str:
#     """
#     If the original requirement starts with a subject+modal ("The system shall …"),
#     prepend it to clauses that lost the subject during splitting.
#     """
#     # Detect a standard subject prefix, e.g. "The system shall"
#     match = re.match(
#         r"^((?:the\s+\w+(?:\s+\w+)?\s+shall|the\s+\w+(?:\s+\w+)?\s+must|the\s+\w+(?:\s+\w+)?\s+should))\b",
#         original,
#         re.IGNORECASE,
#     )
#     if not match:
#         return clause

#     prefix = match.group(1)
#     # Only prepend if clause doesn't already start with a subject-like phrase
#     if not re.match(r"^(the\s+\w+|system|user|it\b)", clause, re.IGNORECASE):
#         return f"{prefix} {clause}"
#     return clause


# # ---------------------------------------------------------------------------
# # Public API
# # ---------------------------------------------------------------------------

# class AtomicStatementGenerator:
#     """
#     Splits requirements into atomic statements using pure NLP (no LLM).
#     Grammar correction is intentionally out of scope here.
#     """

#     def make_atomic(self, requirement: str | list) -> list[str]:
#         """
#         Takes one requirement (string) OR a list of requirement strings.
#         Returns a flat list of atomic clauses (raw, may need grammar fix).
#         """
#         if isinstance(requirement, list):
#             combined = " ".join(r for r in requirement if isinstance(r, str))
#         elif isinstance(requirement, str):
#             combined = requirement
#         else:
#             raise TypeError(f"Expected str or list[str], got {type(requirement)}")

#         sentences = sent_tokenize(combined)
#         atomic: list[str] = []

#         for sent in sentences:
#             clauses = _split_on_conjunctions(sent)
#             for clause in clauses:
#                 fixed = _prefix_for(clause, sent)
#                 atomic.append(fixed.strip())

#         return [a for a in atomic if a]


#     def process_requirements(self, requirements: list[dict]) -> list[dict]:
#         """
#         Takes a list of requirement dicts with 'id'/'req_id' and 'text'.
#         Returns a list of result dicts matching the AtomizationResponse schema
#         (without grammar correction — call LLMReasoner.fix_grammar() next).

#         Each result dict:
#             {
#                 "original_id":        str | int,
#                 "original_text":      str,
#                 "was_compound":       bool,
#                 "atomic_statements":  list[str],   # raw, pre-grammar-fix
#             }
#         """
#         results = []
#         for req in requirements:
#             req_id   = req.get("req_id") or req.get("id")
#             text     = req.get("text", "").strip()
#             atomized = self.make_atomic(text)

#             results.append({
#                 "original_id":       str(req_id),
#                 "original_text":     text,
#                 "was_compound":      len(atomized) > 1,
#                 "atomic_statements": atomized,
#             })

#         return results


# import spacy
# import nltk

# from nltk.tokenize import sent_tokenize

# # Initialize NLP models
# nlp = spacy.load("en_core_web_sm")

# class AtomicStatementGenerator:
#     def make_atomic(self, requirements_text):
#         """
#         Takes one requirement (string) OR a list of requirements,
#         and breaks them into atomic statements.
#         """

#         # ---------------------------
#         # 1. Normalize input
#         # ---------------------------

#         # Case A — input is already a list of strings
#         if isinstance(requirements_text, list):
#             combined_text = " ".join(
#                 r for r in requirements_text if isinstance(r, str)
#             )
#         # Case B — input is a single string
#         elif isinstance(requirements_text, str):
#             combined_text = requirements_text
#         else:
#             raise TypeError(
#                 f"make_atomic() expected str or list[str], got {type(requirements_text)}"
#             )

#         # ---------------------------
#         # 2. Sentence tokenization
#         # ---------------------------
#         sentences = sent_tokenize(combined_text)

#         atomic_requirements = []

#         # ---------------------------
#         # 3. Process each sentence
#         # ---------------------------
#         for sent in sentences:
#             doc = nlp(sent)

#             verbs = [token for token in doc if token.pos_ == "VERB"]
#             conj_tokens = [token for token in doc if token.dep_ == "cc"]  # and/or

#             # ---------------------------
#             # 4. Split compound sentences
#             # ---------------------------
#             if len(verbs) > 1 and conj_tokens:
#                 split_clauses = (
#                     sent.replace(" and ", ". ")
#                         .replace(" or ", ". ")
#                         .split(". ")
#                 )
#             else:
#                 split_clauses = [sent]

#             # ---------------------------
#             # 5. Grammar correction + atomicity
#             # ---------------------------
#             for clause in split_clauses:
#             #     matches = tool.check(clause)
#             #     corrected = language_tool_python.utils.correct(clause, matches)
#                 atomic_requirements.append(clause.strip())

#         return atomic_requirements

# # import re
# # import json

# # ALLOWED_TYPES = ["Functional", "Non-Functional"]
# # ALLOWED_SUBTYPES = ["Functional", "Security", "Performance", "Usability", "Reliability"]

# # def extract_corrected_json(llm_output: str) -> dict:
# #     """
# #     Extracts the corrected JSON from LLM output, ignoring the input JSON if both are present.
# #     Cleans minor JSON syntax errors and enforces allowed type/subtype rules.
# #     """
# #     # 1. Extract all JSON blocks
# #     json_blocks = re.findall(r'\{.*\}', llm_output, flags=re.DOTALL)
# #     corrected = None
    
# #     for block in reversed(json_blocks):  # check last blocks first
# #         try:
# #             data = json.loads(block)
# #             if "requirements" in data:
# #                 corrected = data
# #                 break
# #         except json.JSONDecodeError:
# #             # Fix minor issues
# #             cleaned = block.replace("\n", "").replace("\t", "")
# #             cleaned = re.sub(r'\}\s*\{', '},{', cleaned)
# #             cleaned = re.sub(r',(\s*[\]\}])', r'\1', cleaned)
# #             try:
# #                 data = json.loads(cleaned)
# #                 if "requirements" in data:
# #                     corrected = data
# #                     break
# #             except:
# #                 continue
    
# #     if corrected is None:
# #         return {"requirements": []}

# #     # 2. Clean duplicates and sort by ID
# #     seen_ids = set()
# #     unique_reqs = []
# #     for req in corrected.get("requirements", []):
# #         if req['id'] not in seen_ids:
# #             seen_ids.add(req['id'])
# #             # 3. Ensure type/subtype are valid
# #             if req['type'] not in ALLOWED_TYPES:
# #                 req['type'] = "Functional"  # fallback default
# #             if req['type'] == "Functional":
# #                 req['subtype'] = "Functional"
# #             elif req['subtype'] not in ALLOWED_SUBTYPES:
# #                 req['subtype'] = "Functional"  # fallback for NFR
# #             unique_reqs.append(req)

# #     return {"requirements": sorted(unique_reqs, key=lambda x: x['id'])}


# # if __name__== "__main__":
# #     print("here")
# #     reasoner = LLMReasoner()
# #     reqs = ["There should be balls, cups and drinks at the party", "Tomorrow you need to clean the desk, take a shower, wask th dishes and write a story"]
# #     req2 = {
        
# #   "requirements": [
# #     {
# #       "id": 1,
# #       "type": "Non-Functional",
# #       "subtype": "Security",
# #       "text": "The system shall allow users to upload files for analysis."
# #     },
# #     {
# #       "id": 2,
# #       "type": "Functional",
# #       "subtype": "Functional",
# #       "text": "The system shall allow administrators to upload files for analysis."
# #     },
# #     {
# #       "id": 3,
# #       "type": "Functional",
# #       "subtype": "Functional",
# #       "text": "The system shall allow managers to upload files for analysis."
# #     },
# #      {
# #       "id": 4,
# #       "type": "Non-Functional",
# #       "subtype": "Performance",
# #       "text": "The system should have an easy ui to navigate."
# #     },
# #     {
# #       "id": 5,
# #       "type": "Non-Functional",
# #       "subtype": "Security",
# #       "text": "All user passwords must be encrypted at rest and in transit."
# #     },
# #     {
# #       "id": 6,
# #       "type": "Non-Functional",
# #       "subtype": "Usability",
# #       "text": "The application should provide tooltips and inline help for all forms."
# #     },
# #     {
# #       "id": 7,
# #       "type": "Non-Functional",
# #       "subtype": "Performance",
# #       "text": "The system should respond to any user query within 2 seconds under standard load."
# #     },
# #     {
# #       "id": 8,
# #       "type": "Functional",
# #       "subtype": "Non-Functional",
# #       "text": "Administrators can reset user passwords and manage roles."
# #     },
# #     {
# #       "id": 9,
# #       "type": "Functional",
# #       "subtype": "Non-Functional",
# #       "text": "Administrators can reset user passwords and manage roles."
# #     },
# #     {
# #       "id": 10,
# #       "type": "Functional",
# #       "subtype": "Non-Functional",
# #       "text": "Administrators can reset user passwords and manage roles."
# #     }
# #     ]
# #     }
# #     classs = AtomicStatementGenerator()
# #     # atomic = classs.make_atomic(reqs)
# #     # print("Atomic", atomic)
# #     results =reasoner.query(reqs)
# #     print(results, "\n\n\n")
# #     results = extract_corrected_json(results)
# #     print(results)

# # #     # results = results + "33333333333333333333333333333"
# # #     # test = """Some random explanation text from the LLM above

# # # # {
# # # #   "requirements": [
# # # #     {"id": 1, "type": "Functional", "subtype": "Functional", "text": "The system shall allow users to upload files for analysis."}
# # # #     {"id": 2 "type": "Functional" "subtype": "Functional", "text": "The system shall allow administrators to upload files for analysis."}
# # # #     {"id": 3, "type": "Functional", "subtype": "Functional", "text": "The system shall allow managers to upload files for analysis."},
# # # #     {"id": 4, "type": "Non-Functional", "subtype": "Performance", "text": "The application should respond within 2 seconds under load."}
# # # #     {"id": 5, "type": "Non-Functional", "subtype": "Security", "text": "Data must be encrypted during transmission."}
# # # #     {"id": 6, "type": "Non-Functional", "subtype": "Usability", "text": "The UI should be intuitive and easy to navigate."},
# # # #   ]
# # # # }

# # # # Some extra notes from LLM below
# # # # ")"""
    
# # # #     res = robust_fix_llm_output(test)

# # #     # print("Results: ", res)