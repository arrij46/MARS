"""
test_llm_reasoner.py
"""
import re
import os
import json
from dotenv import load_dotenv
from groq import Groq
from typing import List, Dict, Optional

load_dotenv()

PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"

# API KEY MANAGEMENT
def _get_api_keys() -> List[str]:
    keys = []
    for name in ["GROQ_API_KEY_DOCUMENT_ACCOUNT1", "GROQ_API_KEY_DOCUMENT_ACCOUNT2", "GROQ_API_KEY_REFINEMENT_ACCOUNT3"]:
        key = os.getenv(name)
        if key:
            keys.append(key)
    if not keys:
        raise RuntimeError("No Groq API keys found in .env")
    print(f"[llm] Loaded {len(keys)} API key(s)")
    return keys


def _call_llm(prompt: str, model: str, api_keys: List[str]) -> Optional[dict]:
    for i, key in enumerate(api_keys):
        try:
            print(f"[llm] Trying key {i+1}/{len(api_keys)} with model: {model}")
            client = Groq(api_key=key)
            response = client.chat.completions.create(
                model=model,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an SRS generator. Output only valid JSON, no markdown, no explanation."},
                    {"role": "user", "content": prompt}
                ]
            )
            raw = response.choices[0].message.content.strip()
            return json.loads(raw)
        except Exception as e:
            error_str = str(e)
            print(f"[WARN] Key {i+1} model {model} failed: {error_str}")
            # If token limit hit, no point trying other keys with same model
            if "413" in error_str and "tokens" in error_str:
                print(f"[llm] Token limit hit on {model}, skipping remaining keys")
                return None
            continue
    return None

# TEMPLATE DETECTION HELPERS
def _is_features_section(section: dict) -> bool:
    heading_lower = section.get("heading", "").lower()
    sec_id = section.get("id", "")
    subs = section.get("sub", [])
    return (
        "system features" in heading_lower or
        "ieee830-features" in sec_id or
        ("feature" in heading_lower and not subs)
    )

def _is_functions_subsection(sub_heading: str) -> bool:
    heading_lower = sub_heading.lower()
    first_word = sub_heading.strip().split()[0] if sub_heading.strip() else ""
    return "function" in heading_lower and first_word[0].isdigit()

# SECTION STRUCTURE BUILDER
def _build_section_structure_from_template(template: dict) -> str:
    lines = []
    for section in template.get("sections", []):
        if section.get("skip_llm"):
            continue  # exclude from prompt

        heading = section["heading"]
        subs = section.get("sub", [])

        if _is_features_section(section):
            lines.append(
                f"- {heading} "
                f"(generate one named subsection per feature cluster, each with: description, functional_overview, functional_requirements)"
            )
        elif not subs:
            lines.append(f"- {heading} (generate content as a string)")
        else:
            lines.append(f"- {heading}")
            for sub in subs:
                sub_heading = sub["heading"] if isinstance(sub, dict) else sub
                if _is_functions_subsection(sub_heading):
                    lines.append(
                        f"    - {sub_heading} "
                        f"(place functional requirements here, grouped by named feature)"
                    )
                elif _is_nfr_section({"heading": sub_heading}):
                    lines.append(
                        f"    - {sub_heading} "
                        f"(write a 3-5 sentence prose description paragraph, then list nonfunctional_requirements)"
                    )
                else:
                    lines.append(f"    - {sub_heading}")

    return "\n".join(lines)

# NFR SECTION DETECTION HELPERS
def _is_nfr_section(section: dict) -> bool:
    heading = section.get("heading", "").lower()
    nfr_keywords = [
        "nonfunctional", "non-functional", "performance", "security",
        "quality attribute", "reliability", "usability", "maintainability",
        "portability", "safety", "business rules", "other requirements"
    ]
    return any(kw in heading.replace(" ", "") or kw in heading for kw in nfr_keywords)

def _nfr_subsection_schema() -> dict:
    return {
        "description": "string — 3-5 sentence prose paragraph introducing this NFR subsection. Explain what these requirements govern and why they matter for this specific system. Do NOT list requirements here.",
        "nonfunctional_requirements": [
            {"id": "REQ-X", "text": "Exact NFR text verbatim, with all quality tags appended."}
        ]
    }

# JSON SCHEMA BUILDER
def _feature_block_schema() -> dict:
    return {
        "Descriptive_Feature_Name": {
            "description": "1 paragraph summary of what this feature group covers.",
            "functional_overview": [
                "High-level capability statement (NOT the requirement text)",
                "Another high-level capability"
            ],
            "functional_requirements": [
                {"id": "REQ-1", "text": "Exact requirement text — verbatim, no changes."},
                {"id": "REQ-2", "text": "Exact requirement text — verbatim, no changes."}
            ]
        }
    }

def _build_json_schema_from_template(template: dict = None) -> str:
    schema_sections = {}

    for section in template.get("sections", []):
        if section.get("skip_llm"):
            continue  # not passed to LLM

        heading = section["heading"]
        subs = section.get("sub", [])
        sec_key = heading.replace(" ", "_").replace(":", "").replace("/", "_").replace(".", "_")

        if _is_features_section(section):
            schema_sections[sec_key] = _feature_block_schema()

        elif _is_nfr_section(section):
            # Top-level NFR section with subsections
            sub_dict = {}
            for sub in subs:
                sub_heading = sub["heading"] if isinstance(sub, dict) else sub
                sub_key = (
                    sub_heading.lower()
                    .replace(" ", "_").replace(".", "_")
                    .replace("(", "").replace(")", "")
                )
                sub_dict[sub_key] = _nfr_subsection_schema()
            schema_sections[sec_key] = sub_dict if sub_dict else _nfr_subsection_schema()

        elif not subs:
            schema_sections[sec_key] = "string — content for this section"

        else:
            sub_dict = {}
            for sub in subs:
                sub_heading = sub["heading"] if isinstance(sub, dict) else sub
                sub_key = (
                    sub_heading.lower()
                    .replace(" ", "_").replace(".", "_")
                    .replace("(", "").replace(")", "")
                )
                if _is_functions_subsection(sub_heading):
                    sub_dict[sub_key] = "string — prose paragraph (4-5 sentences) summarizing the system's overall capabilities at a business level. Do NOT include feature structures or requirement listings here."
                elif _is_nfr_section({"heading": sub_heading}):
                    sub_dict[sub_key] = _nfr_subsection_schema()
                else:
                    sub_dict[sub_key] = "string — content for this subsection"
            schema_sections[sec_key] = sub_dict

    return json.dumps({"title": "string", "sections": schema_sections}, indent=2)


# SKIPPED SECTION PLACEHOLDER BUILDER
def _build_skipped_sections(template: dict) -> dict:
    """
    Build placeholder content for sections marked skip_llm: True.
    Injected into final SRS after LLM generation.
    """
    skipped = {}
  
    for section in template.get("sections", []):
        if not section.get("skip_llm"):
            continue

        heading = section["heading"]
        sec_key = heading.replace(" ", "_").replace(".", "_").replace(":", "")
        subs = section.get("sub", [])

        if not subs:
            skipped[sec_key] = "Add content as per your need."
        else:
            sub_dict = {}
            for sub in subs:
                sub_heading = sub["heading"] if isinstance(sub, dict) else sub
                sub_key = (
                    sub_heading.lower()
                    .replace(" ", "_").replace(".", "_")
                    .replace("(", "").replace(")", "")
                )
                sub_dict[sub_key] = "Add content as per your need."
            skipped[sec_key] = sub_dict

    return skipped

def _mark_skip_llm_sections(template: dict) -> dict:
    """Mark sections that should not be passed to LLM based on heading keywords"""
    skip_keywords = ["verification", "structure only"]
    for section in template.get("sections", []):
        heading_lower = section.get("heading", "").lower()
        if any(kw in heading_lower for kw in skip_keywords):
            section["skip_llm"] = True
    return template

# PRIORITIZATION
def _build_prioritization_prompt(functional_req_clusters: List[List[str]], system_name: str) -> str:
    clusters_text = "\n".join(
        f"Cluster {i+1}:\n" + "\n".join(f"  - {req}" for req in cluster)
        for i, cluster in enumerate(functional_req_clusters)
    )
    return f"""
You are a senior software requirements engineer ordering feature clusters for an SRS document for: "{system_name}".

Your task is to reorder the clusters below into the correct logical document sequence.

ORDERING RULES — apply strictly in this priority order:

TIER 1 — Always first:
  - User registration, signup, account creation
  - Login, authentication, credentials, password reset
  - Multi-factor authentication, session management
  - User account management (create/update/delete users)
  - Role and permission setup

TIER 2 — Core domain features (what the system is actually built to do):
  - The primary business/domain workflows
  - Case recording, event management, investigation flows
  - Any feature that is the main purpose of the system

TIER 3 — Supporting features:
  - Search, filtering, sorting
  - Dashboards, visualization, reporting
  - Notifications, alerts, messaging
  - Data analysis and monitoring tools

TIER 4 — Data and content management:
  - Import/export functionality
  - Data linking, relationships, entity management
  - Document/file management
  - Audit logs, activity tracking

TIER 5 — Integrations and external systems:
  - Third-party API integrations
  - External system connections (labs, surveillance, HL7, FHIR)
  - Data exchange protocols

TIER 6 — Always last:
  - Security mechanisms, encryption, access control enforcement
  - Database internals, backups, recovery
  - Performance optimization, caching
  - System-level infrastructure concerns

CLUSTERS TO ORDER:
{clusters_text}

STRICT RULES:
- Assign each cluster to the most appropriate tier based on what its requirements are about.
- Return ALL clusters — do not drop any.
- Preserve every requirement string exactly as given — no edits, no merging, no splitting.
- Output ONLY valid JSON in this exact format:
{{
  "ordered_clusters": [
    ["requirement 1", "requirement 2"],
    ["requirement 3"]
  ]
}}
""".strip()

def _prioritize_clusters(functional_req_clusters: List[List[str]], system_name: str, api_keys: List[str]) -> List[List[str]]:
    if len(functional_req_clusters) <= 1:
        return functional_req_clusters

    prompt = _build_prioritization_prompt(functional_req_clusters, system_name)
    result = _call_llm(prompt, PRIMARY_MODEL, api_keys)
    if not result:
        result = _call_llm(prompt, FALLBACK_MODEL, api_keys)

    if not result or "ordered_clusters" not in result:
        print("[llm] Prioritization failed, using original order")
        return functional_req_clusters

    ordered = result["ordered_clusters"]
    original_flat = set(req for cluster in functional_req_clusters for req in cluster)
    ordered_flat = set(req for cluster in ordered for req in cluster)

    if original_flat != ordered_flat:
        print("[llm] Prioritization changed requirements — using original order")
        return functional_req_clusters

    print(f"[llm] Clusters prioritized: {len(ordered)} clusters reordered")
    return ordered


# ─────────────────────────────────────────────────────────────────────────────
# ATOMIC JSON LOADER
# Loads the atomic refinement JSON and builds two lookup maps:
#   req_id_map:   req_id (str) → full entry dict
#   text_to_id:   cleaned_text (str) → req_id (str)
# These are used as the single source of truth for IDs throughout SRS + RTM.
# ─────────────────────────────────────────────────────────────────────────────
def _load_atomic_index(conv_id: str) -> tuple[dict, dict]:
    """
    Returns:
        req_id_map  : { "REQ-31": { req_id, text, parent_req_id, ... }, ... }
        text_to_id  : { "The system shall allow users to log in.": "REQ-31", ... }
    """
    atomic_path = f"./agents/refinement/results/atomic_refinement_{conv_id}.json"
    if not os.path.exists(atomic_path):
        print(f"[atomic] No atomic file at {atomic_path} — ID coherence skipped")
        return {}, {}

    with open(atomic_path, "r", encoding="utf-8") as f:
        atomic_json = json.load(f)

    req_id_map: dict = {}
    text_to_id: dict = {}

    for entry in atomic_json.get("requirements", []):
        rid  = str(entry.get("req_id", "")).strip()
        text = entry.get("text", "").strip()
        # Strip any leading "N: " numeric prefix that build_prompt adds
        cleaned = re.sub(r'^\d+:\s*', '', text)
        if rid:
            req_id_map[rid] = entry
            if cleaned:
                text_to_id[cleaned] = rid

    print(f"[atomic] Loaded {len(req_id_map)} requirement IDs from atomic file")
    return req_id_map, text_to_id


# ─────────────────────────────────────────────────────────────────────────────
# ID COHERENCE PASS
# After the LLM generates the SRS JSON, walk every functional_requirement and
# nonfunctional_requirement entry and replace the LLM-assigned ID with the
# canonical ID from the atomic file (matched by requirement text).
# ─────────────────────────────────────────────────────────────────────────────
def _apply_atomic_ids(srs_json: dict, text_to_id: dict) -> dict:
    """
    Mutates srs_json in-place: replaces every req "id" field with the
    canonical ID from the atomic file, matched by requirement text.
    Unmatched requirements keep their LLM-assigned ID and a warning is printed.
    """
    if not text_to_id:
        print("[atomic] text_to_id map empty — skipping ID coherence pass")
        return srs_json

    replaced = 0
    unmatched = 0

    def _normalise(text: str) -> str:
        """Strip leading IDs so we can fuzzy-match."""
        # Remove leading "REQ-N: " prefix the LLM sometimes adds
        cleaned = re.sub(r'^REQ-\d+:\s*', '', text)
        return cleaned.strip()

    sections = srs_json.get("sections", {})
    for sec_val in sections.values():
        if not isinstance(sec_val, dict):
            continue
        for feat_val in sec_val.values():
            if not isinstance(feat_val, dict):
                continue

            # Functional requirements
            for req in feat_val.get("functional_requirements", []):
                norm = _normalise(req.get("text", ""))
                canonical_id = text_to_id.get(norm)
                if canonical_id:
                    req["id"] = canonical_id
                    replaced += 1
                else:
                    print(f"[atomic] No canonical ID for FR: {norm[:80]}...")
                    unmatched += 1

            # Non-functional requirements (nested under NFR subsections)
            for req in feat_val.get("nonfunctional_requirements", []):
                norm = _normalise(req.get("text", ""))
                canonical_id = text_to_id.get(norm)
                if canonical_id:
                    req["id"] = canonical_id
                    replaced += 1
                else:
                    print(f"[atomic] No canonical ID for NFR: {norm[:80]}...")
                    unmatched += 1

    print(f"[atomic] ID coherence pass complete — replaced: {replaced}, unmatched: {unmatched}")
    return srs_json


# ─────────────────────────────────────────────────────────────────────────────
# SECTION NUMBER MAP
# Build a deterministic section-number → key mapping from the template so
# _resolve_fr_label can return proper numbers (e.g. "4.1", "5.3") instead of
# falling back to "4" or "Unknown".
# ─────────────────────────────────────────────────────────────────────────────
def _build_section_number_map(template: dict) -> dict:
    """
    Returns { sec_key: "N.M" } for every section/subsection in the template.
    Top-level sections are numbered 1, 2, 3 … in order.
    Subsections are numbered N.1, N.2 …
    Sections marked skip_llm are still numbered (they appear in the doc).
    """
    number_map: dict = {}
    top_counter = 0

    for section in template.get("sections", []):
        top_counter += 1
        heading = section["heading"]
        sec_key = heading.replace(" ", "_").replace(":", "").replace("/", "_").replace(".", "_")
        number_map[sec_key] = str(top_counter)

        for sub_idx, sub in enumerate(section.get("sub", []), start=1):
            sub_heading = sub["heading"] if isinstance(sub, dict) else sub
            sub_key = (
                sub_heading.lower()
                .replace(" ", "_").replace(".", "_")
                .replace("(", "").replace(")", "")
            )
            number_map[sub_key] = f"{top_counter}.{sub_idx}"

    return number_map


# ftn for feature extraction and clustering incase reqs are missed in the doc
def _reconcile_missing_frs(srs_json: dict, functional_req_clusters: List[List[str]]) -> dict:
    """
    Compare FRs in final SRS against original clusters.
    Any requirement present in clusters but missing from the SRS is injected
    into the most appropriate feature block (matched by cluster index).
    """

    def _strip_prefix(req_str: str) -> str:
        return re.sub(r'^\d+:\s*', '', req_str.strip())

    def _extract_id(req_str: str) -> str:
        match = re.match(r'^(\d+):', req_str.strip())
        return f"REQ-{match.group(1)}" if match else None

    # ── 1. Collect all req texts + ids already present in SRS
    sections = srs_json.get("sections", {})
    present_texts: set[str] = set()
    present_ids:   set[str] = set()

    for sec_val in sections.values():
        if not isinstance(sec_val, dict):
            continue
        for feat_val in sec_val.values():
            if not isinstance(feat_val, dict):
                continue
            for req in feat_val.get("functional_requirements", []):
                present_texts.add(req.get("text", "").strip())
                present_ids.add(req.get("id", "").strip())

    # ── 2. Find missing reqs per cluster
    missing_by_cluster: dict[int, list[dict]] = {}

    for cluster_idx, cluster in enumerate(functional_req_clusters):
        for req_str in cluster:
            text      = _strip_prefix(req_str)
            req_id    = _extract_id(req_str)

            already_present = (
                text in present_texts or
                (req_id and req_id in present_ids)
            )
            if not already_present:
                missing_by_cluster.setdefault(cluster_idx, []).append({
                    "id":   req_id or f"REQ-MISSING-{cluster_idx}",
                    "text": text
                })
                print(f"[reconcile] Missing FR detected — cluster {cluster_idx + 1}: {req_id} | {text[:60]}...")

    if not missing_by_cluster:
        print("[reconcile] All FRs accounted for — no injection needed")
        return srs_json

    # ── 3. Build ordered list of (sec_key, feat_key, feat_val) for injection targeting
    feature_slots = []
    for sec_key, sec_val in sections.items():
        if not isinstance(sec_val, dict):
            continue
        for feat_key, feat_val in sec_val.items():
            if isinstance(feat_val, dict) and "functional_requirements" in feat_val:
                feature_slots.append((sec_key, feat_key, feat_val))

    # ── 4. Inject missing reqs into the feature slot closest to cluster index
    total_slots = len(feature_slots)

    for cluster_idx, missing_reqs in missing_by_cluster.items():
        if total_slots == 0:
            print(f"[reconcile] No feature slots found — cannot inject cluster {cluster_idx + 1}")
            continue

        slot_idx  = min(cluster_idx, total_slots - 1)
        sec_key, feat_key, feat_val = feature_slots[slot_idx]

        for req in missing_reqs:
            feat_val["functional_requirements"].append(req)
            print(f"[reconcile] Injected {req['id']} into '{feat_key}' (section '{sec_key}')")

    return srs_json


# ─────────────────────────────────────────────────────────────────────────────
# RTM BUILDER  (fix: uses atomic index + section_number_map for all lookups)
# ─────────────────────────────────────────────────────────────────────────────
def build_rtm(
    srs_json: dict,
    nfrs_clusters: dict,
    conv_id: str,
    section_number_map: dict | None = None,
) -> list:
    atomic_path = f"./agents/refinement/results/atomic_refinement_{conv_id}.json"
    atomic_json = {}
    if os.path.exists(atomic_path):
        with open(atomic_path, "r", encoding="utf-8") as f:
            atomic_json = json.load(f)
    else:
        print(f"[build_rtm] No atomic refinement file found at {atomic_path}, proceeding without lineage")

    # ── Build a fast lookup: req_id → (srs_section, feature) from the SRS JSON
    # This is derived AFTER the ID coherence pass, so IDs match the atomic file.
    fr_label_cache: dict[str, tuple[str, str]] = _build_fr_label_cache(
        srs_json, section_number_map or {}
    )

    # ── NFR subtype → section number (derived from section_number_map or defaults)
    nfr_section_map = _build_nfr_section_map(section_number_map)

    # ── Build NFR tag lookup: cleaned text → (subtype, srs_section)
    nfr_tag_lookup: dict[str, tuple[str, str]] = {}
    for subtype, reqs in nfrs_clusters.items():
        section = nfr_section_map.get(subtype.lower(), nfr_section_map.get("other", "5.5"))
        for req in reqs:
            cleaned = re.sub(r'^\d+:\s*', '', req.strip())
            nfr_tag_lookup[cleaned] = (subtype, section)

    # ── Single pass over all atomic entries
    rtm = []
    for entry in atomic_json.get("requirements", []):
        req_id      = str(entry.get("req_id", ""))
        text        = entry.get("text", "")
        parent_id   = entry.get("parent_req_id")
        parent_text = entry.get("parent_text")
        origin      = entry.get("origin", ["extracted"])

        cleaned_text = re.sub(r'^\d+:\s*', '', text.strip())

        if cleaned_text in nfr_tag_lookup:
            # ── NFR
            subtype, section = nfr_tag_lookup[cleaned_text]
            rtm.append({
                "id":            req_id,
                "text":          text,
                "origin":        origin,
                "parent_req_id": parent_id,
                "parent_text":   parent_text,
                "type":          "Non-Functional",
                "subtype":       subtype,
                "srs_section":   section,
                "feature":       subtype.capitalize(),
            })
        else:
            # ── FR: look up from the pre-built cache (keyed by req_id)
            srs_section, feature = fr_label_cache.get(req_id, ("", ""))

            # Fallback: also try parent_id
            if not srs_section and parent_id:
                srs_section, feature = fr_label_cache.get(parent_id, ("", ""))

            # Last resort: derive section number from the SRS features section
            if not srs_section:
                srs_section = _fallback_fr_section(section_number_map)
                feature = "Unresolved"
                print(f"[rtm] Could not resolve section for FR {req_id} — assigned to {srs_section}")

            rtm.append({
                "id":            req_id,
                "text":          text,
                "origin":        origin,
                "parent_req_id": parent_id,
                "parent_text":   parent_text,
                "type":          "Functional",
                "subtype":       "",
                "srs_section":   srs_section,
                "feature":       feature,
            })

    return rtm


def _build_fr_label_cache(srs_json: dict, section_number_map: dict) -> dict:
    """
    Walk all feature blocks in the SRS and build:
        { req_id: (srs_section_number, feature_display_name) }

    Section numbers are resolved via section_number_map (from template).
    If the section key isn't in the map, we fall back to the order-based
    counter used previously — but now we also try the parent sec_key with
    a dot-suffix so labels like "4.1", "4.2" etc. are produced correctly.
    """
    cache: dict = {}
    sections = srs_json.get("sections", {})

    # Find the features section key (the one that contains feature blocks)
    # We identify it by the presence of functional_requirements in its children
    for sec_key, sec_val in sections.items():
        if not isinstance(sec_val, dict):
            continue

        # Resolve top-level section number
        sec_num = section_number_map.get(sec_key, "")

        feature_index = 1
        for feat_key, feat_val in sec_val.items():
            if not (isinstance(feat_val, dict) and "functional_requirements" in feat_val):
                continue

            # Sub-section number: prefer explicit map entry, else derive
            sub_num = section_number_map.get(feat_key, "")
            if not sub_num:
                sub_num = f"{sec_num}.{feature_index}" if sec_num else str(feature_index)

            feature_name = feat_key.replace("_", " ").title()

            for req in feat_val.get("functional_requirements", []):
                rid = str(req.get("id", "")).strip()
                if rid:
                    cache[rid] = (sub_num, feature_name)

            feature_index += 1

    return cache


def _build_nfr_section_map(section_number_map: dict | None) -> dict:
    """
    Map NFR subtype keywords → section numbers.
    Tries to infer from section_number_map key names; falls back to defaults.
    """
    defaults = {
        "performance":     "5.1",
        "safety":          "5.2",
        "security":        "5.3",
        "usability":       "5.4",
        "reliability":     "5.4",
        "maintainability": "5.4",
        "portability":     "5.5",
        "operational":     "5.5",
        "other":           "5.5",
    }

    if not section_number_map:
        return defaults

    # Try to override defaults from actual section_number_map entries
    result = dict(defaults)
    for key, num in section_number_map.items():
        key_lower = key.lower()
        for subtype in defaults:
            if subtype in key_lower:
                result[subtype] = num
                break

    return result


def _fallback_fr_section(section_number_map: dict | None) -> str:
    """Return the number of the first Features-like section, or '4'."""
    if not section_number_map:
        return "4"
    for key, num in section_number_map.items():
        if "feature" in key.lower() or "function" in key.lower():
            return num
    return "4"


def _resolve_fr_label(srs_json: dict, req_id: str, parent_id: str) -> tuple[str, str]:
    """
    Legacy helper kept for compatibility.
    Prefer _build_fr_label_cache for bulk lookups.
    """
    sections = srs_json.get("sections", {})
    search_ids = [i for i in [req_id, parent_id] if i]

    for sec_key, sec_val in sections.items():
        if not isinstance(sec_val, dict):
            continue
        # Try to derive a section number from the key prefix (e.g. "4_System_Features" → "4")
        sec_num = sec_key.split("_")[0] if sec_key and sec_key[0].isdigit() else ""
        feature_index = 1
        for feat_key, feat_val in sec_val.items():
            if not (isinstance(feat_val, dict) and "functional_requirements" in feat_val):
                continue
            section_num  = f"{sec_num}.{feature_index}" if sec_num else f"4.{feature_index}"
            feature_name = feat_key.replace("_", " ").title()
            for req in feat_val["functional_requirements"]:
                if str(req["id"]) in search_ids:
                    return section_num, feature_name
            feature_index += 1

    return "4", "Unresolved"


# PROMPT BUILDER
def build_prompt(
    functional_req_clusters: List[List[str]],
    nfrs_clusters: Dict[str, List[str]],
    system_name: str,
    system_description: str,
    template: dict = None,
    text_to_id: dict = None,          # ← NEW: canonical ID map from atomic file
) -> str:

    # Filter out skip_llm sections before building prompt
    filtered_template = None
    if template:
        filtered_template = dict(template)
        filtered_template["sections"] = [
            s for s in template.get("sections", [])
            if not s.get("skip_llm")
        ]

    # ── Assign canonical IDs to each requirement from the atomic index.
    # If the atomic map is available, we use its IDs so the LLM uses the same
    # IDs that will appear in the RTM.  If not, fall back to sequential REQ-N.
    def _strip_numeric_prefix(req_str: str) -> str:
        return re.sub(r'^\d+:\s*', '', req_str.strip())

    def _extract_original_id(req_str: str) -> str:
        match = re.match(r'^(\d+):', req_str.strip())
        return f"REQ-{match.group(1)}" if match else None

    all_reqs = []
    for cluster in functional_req_clusters:
        all_reqs.extend(cluster)

    req_labels = []
    used_seq = 1
    for req in all_reqs:
        text_clean = _strip_numeric_prefix(req)
        # 1st priority: canonical ID from atomic index
        if text_to_id and text_clean in text_to_id:
            req_labels.append(text_to_id[text_clean])
        # 2nd priority: embedded numeric prefix in the cluster string
        else:
            original = _extract_original_id(req)
            if original:
                req_labels.append(original)
            else:
                req_labels.append(f"REQ-{used_seq}")
                used_seq += 1

    numbered_reqs = [
        f"{label}: {_strip_numeric_prefix(req)}"
        for label, req in zip(req_labels, all_reqs)
    ]

    # Assign back to clusters
    cluster_blocks = []
    start_idx = 0
    for cluster in functional_req_clusters:
        end_idx = start_idx + len(cluster)
        cluster_blocks.append("\n".join(numbered_reqs[start_idx:end_idx]))
        start_idx = end_idx

    # Format NFRs — also use canonical IDs where available
    nfr_blocks = []
    nfr_counter = 1
    for section, reqs in nfrs_clusters.items():
        if reqs:
            labeled = []
            for r in reqs:
                cleaned = re.sub(r'^\d+:\s*', '', r.strip())
                if text_to_id and cleaned in text_to_id:
                    nfr_id = text_to_id[cleaned]
                else:
                    nfr_id = f"REQ-{nfr_counter}"
                    nfr_counter += 1
                labeled.append(f"{nfr_id}: {cleaned}")
            req_list = "\n".join(f"- {r}" for r in labeled)
        else:
            req_list = "No specific requirements identified."
        nfr_blocks.append(f"{section}:\n{req_list}")

    section_structure = _build_section_structure_from_template(filtered_template)
    json_schema = _build_json_schema_from_template(filtered_template)

    # Detect where features go
    features_instruction = "Place grouped functional requirements in the System Features section."
    for section in filtered_template.get("sections", []):
        if _is_features_section(section):
            features_instruction = (
                f"Place grouped functional requirements in '{section['heading']}'. "
                f"Each cluster becomes one named feature subsection."
            )
            break
        for sub in section.get("sub", []):
            sub_heading = sub["heading"] if isinstance(sub, dict) else sub
            if _is_functions_subsection(sub_heading):
                features_instruction = (
                    f"Place grouped functional requirements inside '{sub_heading}' "
                    f"under '{section['heading']}'. "
                    f"Each cluster becomes one named feature entry."
                )
                break

    cluster_section = "\n\n".join(
        f"--- Cluster {i+1} ---\n{block}"
        for i, block in enumerate(cluster_blocks)
    )
    return f"""
    You are a senior software requirements engineer. Generate a formal SRS document as valid JSON.

    PROJECT: "{system_name}"
    DESCRIPTION: {system_description}

    FUNCTIONAL REQUIREMENTS (clustered — do not modify):
    {cluster_section}

    NON-FUNCTIONAL REQUIREMENTS:
    {chr(10).join(nfr_blocks)}

    WRITING RULES:
    - For writing content in the sections, refer to the project description and the provided requirements. Ground all content in that information.
    - Every section must contain atleast 3-5 meaningful sentences grounded in the actual system name, domain, and provided requirements. No one-liners.
    - Write as a senior engineer who understands this specific system — not generic boilerplate that could apply to any project.
    - Section 1.4 Project Scope (or equivalent section) must describe: (a) what the system does, (b) who uses it, (c) what it explicitly does NOT cover. Derive all three from the system description and requirements provided. Do not write about technologies used.
    - Section 2.7 Assumptions and Dependencies (or equivalent section) must list actual assumptions derivable from the requirements — e.g., if the system has authentication, assume an identity provider exists; if it has a campus map, assume map data is available. Do not write about "personnel and funding".
    - For any sentence that requires information not present in the input, append [INFERRED] so the document owner can verify it.
    - Section 2.2 Product Functions (or equivalent section) must be written as a single prose paragraph of 4-5 sentences summarizing the system's overall capabilities. Do NOT list requirements, do NOT use feature substructures, do NOT repeat content from the features section. This section answers "what does this system do?" at a business level, not a technical level.
    - Glossary must be a plain string, one "Term: Full sentence definition." per line separated by \\n, minimum 8 terms covering acronyms (SRS, API, HTTPS), user roles, domain terms, and system concepts from this document.
    - For every NFR subsection (performance, security, quality attributes, etc.), you MUST write a "description" field containing a 3-5 sentence prose paragraph that introduces that subsection. This paragraph must explain what requirements are covered, why they matter for this specific system, and any context relevant to the domain. Do NOT use a one-liner. Do NOT skip this field.

    RULES:
    1. Output ONLY valid JSON matching the OUTPUT SCHEMA. No markdown, no explanation.
    2. Use ONLY the information provided above. Do not add, infer, or invent any requirement, metric, standard, protocol, or constraint not present in the input.
    3. NFR sections must reflect the input text faithfully. If the input NFR is vague, the output must also be vague — do not expand "secure" into "AES-256" or "fast" into "≤2s".
    4. Each cluster becomes exactly ONE feature in the features section — same count, same grouping, no splitting or merging. DO NOT create clusters on your own — use the clusters as given, do not split or merge them. If a cluster contains a mix of high and low priority features, assign it to the tier that best fits its overall content. Do not move individual requirements between clusters.

    5. Every requirement string maps to exactly ONE entry in functional_requirements — verbatim, no splitting, no paraphrasing.
    6. Each REQ-ID appears in exactly one feature — no duplicates across features.
    7. Feature keys must be descriptive Title_Case_With_Underscores based on the cluster content.
    8. {features_instruction}
    9. Glossary must be a plain string with one "Term: Definition sentence." per line, separated by \\n. Minimum 8 terms covering acronyms, user roles, domain terms, and system concepts from this document.
    10. NFR ID Preservation:
        Every Non-Functional Requirement must appear as a structured object with:
        - "id": the original REQ-ID exactly as provided in the NON-FUNCTIONAL REQUIREMENTS input above (e.g. "REQ-1", "REQ-5")
        - "text": the verbatim requirement text.
        Do NOT embed NFRs as bare prose sentences inside section strings.
        The mapping of NFR subtypes to sections is:
        security     → 5_3_security_requirements (or equivalent key)
        performance  → 5_1_performance_requirements (or equivalent key)
        reliability  → 5_4_software_quality_attributes (or equivalent key)
        usability    → 5_4_software_quality_attributes (or equivalent key)
        operational  → 5_5_business_rules (or equivalent key)
        other        → other_requirements (or equivalent key, as structured array, same format)
        The assumed-metrics count sentence goes in the "description" field of whichever
        subsection introduces the last assumed metric, not as a standalone requirement.

    11. REQUIREMENT IDs — CRITICAL:
        The REQ-IDs provided in the FUNCTIONAL REQUIREMENTS and NON-FUNCTIONAL REQUIREMENTS
        input above are CANONICAL and must be used verbatim in the output JSON.
        Do NOT renumber, reassign, or invent new IDs. Every "id" field must exactly match
        the REQ-ID from the input (e.g. if the input says "REQ-31: ...", output "id": "REQ-31").

    REQUIRED STRUCTURE:
    {section_structure}

    OUTPUT SCHEMA:
    {json_schema}

    Generate the SRS JSON now.
    """.strip()

# SRS GENERATION MAIN FUNCTION
async def generate_srs(
    functional_req_clusters: List[List[str]],
    nfrs_clusters: Dict[str, List[str]],
    system_name: str,
    system_description: str,
    document_path: str,
    conv_id: str,
    template: dict = None
) -> dict:
    
    api_keys = _get_api_keys()

    if template:
        template = _mark_skip_llm_sections(template)

    # ── Load atomic index ONCE — used for ID coherence in prompt + post-pass + RTM
    req_id_map, text_to_id = _load_atomic_index(conv_id)

    # ── Build section number map from template (used by RTM label resolution)
    section_number_map = _build_section_number_map(template) if template else {}

    # Prioritize the requirement clusters
    print("[llm doc agent] Prioritizing requirement clusters...")
    functional_req_clusters = _prioritize_clusters(
        functional_req_clusters,
        system_name,
        api_keys
    )

    # Build the prompt with canonical IDs injected
    prompt = build_prompt(
        functional_req_clusters,
        nfrs_clusters,
        system_name,
        system_description,
        template,
        text_to_id=text_to_id,         # ← pass canonical ID map
    )

    srs_json = None
    print(f"[llm doc agent] Prompt built: {prompt}")
    # Step 1 — try all keys with primary model
    print(f"[llm doc agent] Attempting generation with primary model: {PRIMARY_MODEL}")
    srs_json = _call_llm(prompt, PRIMARY_MODEL, api_keys)

    # Step 2 — if all primary keys failed, try fallback model with all keys
    if not srs_json:
        print(f"[llm doc agent] Primary model failed on all keys. Trying fallback: {FALLBACK_MODEL}")
        srs_json = _call_llm(prompt, FALLBACK_MODEL, api_keys)

    # Step 3 — if everything failed, raise
    if not srs_json:
        raise RuntimeError(
            f"SRS generation failed. All {len(api_keys)} API keys failed on both "
            f"{PRIMARY_MODEL} and {FALLBACK_MODEL}."
        )

    # Ensure title is always set
    if "title" not in srs_json:
        srs_json["title"] = system_name

    # ── ID coherence pass: replace LLM-assigned IDs with canonical atomic IDs
    if text_to_id:
        print("[llm doc agent] Applying atomic ID coherence pass...")
        srs_json = _apply_atomic_ids(srs_json, text_to_id)

    # ── Deduplication: remove any REQ-IDs that appear in multiple features ──
    sections = srs_json.get("sections", {})
    seen_req_ids = set()
    for sec_key, sec_val in sections.items():
        if isinstance(sec_val, dict):
            for feat_key, feat_val in sec_val.items():
                if isinstance(feat_val, dict) and "functional_requirements" in feat_val:
                    deduped = []
                    for req in feat_val["functional_requirements"]:
                        rid = req.get("id")
                        if rid not in seen_req_ids:
                            seen_req_ids.add(rid)
                            deduped.append(req)
                        else:
                            print(f"[DEDUP] Removed duplicate {rid} from feature '{feat_key}'")
                    feat_val["functional_requirements"] = deduped

    # Reconcile any missing functional requirements
    srs_json = _reconcile_missing_frs(srs_json, functional_req_clusters)

    # Inject skipped sections (e.g. Verification for ISO 29148)
    if template:
        skipped = _build_skipped_sections(template)
        if skipped:
            print(f"[test] Injecting {len(skipped)} skipped section(s): {list(skipped.keys())}")
            srs_json["sections"].update(skipped)
    else:
        print("[test] No template provided, skipping injection of skipped sections")        

    # Build RTM appendix — now passes section_number_map for proper label resolution
    srs_json["Appendix_RTM"] = build_rtm(
        srs_json,
        nfrs_clusters,
        conv_id,
        section_number_map=section_number_map,
    )

    # Save to file
    os.makedirs(document_path, exist_ok=True)
    file_path = os.path.join(document_path, f"srs_{conv_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(srs_json, f, indent=2)
        print(f"[llm doc agent] SRS saved at: {file_path}")

    return srs_json
