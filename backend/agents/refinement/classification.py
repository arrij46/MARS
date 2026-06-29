import json
from joblib import load
import __main__
from pathlib import Path
# Import all classes needed for unpickling the models
from agents.refinement.classification_helpers.train_two_stage_RE_custom import (  
    map_re_label,
    TextCleaner,
    MetaFeatures,
    MetaFeaturesTransformer,
    SentenceTransformerFeatures,
    SPACY_AVAILABLE,
    SENTENCE_TRANSFORMER_AVAILABLE
)
# load to main to avoid import errors during joblib load
__main__.TextCleaner = TextCleaner
__main__.MetaFeatures = MetaFeatures
__main__.MetaFeaturesTransformer = MetaFeaturesTransformer
__main__.SentenceTransformerFeatures = SentenceTransformerFeatures
__main__.map_re_label = map_re_label


import re

# Keywords that strongly signal Non-Functional requirements, regardless of "shall/should/must"
_NFR_PATTERNS = [
    # Performance
    (re.compile(r"\b(respond|response time|fast|quickly|speed|latency|throughput)\b", re.I), "performance"),
    # Reliability / Availability
    (re.compile(r"\b(available|availability|uptime|up and running|most of the time|7 out of|downtime|reliable)\b", re.I), "reliability"),
    # Usability / Aesthetics
    (re.compile(r"\b(visually appealing|user.friendly|easy to (use|navigate)|intuitive|aesthetic)\b", re.I), "usability"),
    # Security
    (re.compile(r"\b(securely|encrypted|GDPR|compliance|authentication|authorization|password|secure storage)\b", re.I), "security"),
    # Maintainability
    (re.compile(r"\b(maintainable|maintainability|modular|extensible|scalable)\b", re.I), "maintainability"),
    # Portability / Compatibility
    (re.compile(r"\b(cross.platform|mobile|browser|web browser|portable|compatible)\b", re.I), "portability"),
    # Operational
    (re.compile(r"\b(MongoDB|deployed|hosted|infrastructure|server|database|accessible in)\b", re.I), "operational"),
]

def fix_misclassifications(requirements: list[dict]) -> list[dict]:
    """
    Post-processing pass to correct Functional requirements that are actually Non-Functional,
    based on keyword patterns. Does not touch anything already correctly labeled Non-Functional.
    """
    fixed = []
    for req in requirements:
        if req["type"] == "Functional":
            text = req.get("text", "")
            matched_subtype = None
            for pattern, subtype in _NFR_PATTERNS:
                if pattern.search(text):
                    matched_subtype = subtype
                    break  # first match wins

            if matched_subtype:
                fixed.append({
                    **req,
                    "type": "Non-Functional",
                    "subtype": matched_subtype,
                })
                continue

        fixed.append(req)
    return fixed


def classify_requirements(input_path: str, output_path: str):
    """
    Classifies a JSON of requirements into Functional / Non-Functional and NFR subtypes.

    Args:
        input_path (str): Path to input JSON file containing requirements.
        output_path (str): Path to save classified JSON file.

    Returns:
        dict: Classified requirements in JSON format.
    """

    # Resolve model paths relative to this file (stable regardless of cwd)
    _here = Path(__file__).resolve().parent
    models_dir = _here / "classification_helpers" / "models"
    fr_path = models_dir / "re_fr_classifier.joblib"
    nfr_path = models_dir / "re_nfr_subclassifier.joblib"

    fr_model = None
    nfr_model = None
    if fr_path.exists() and nfr_path.exists():
        fr_model = load(str(fr_path))
        nfr_model = load(str(nfr_path))

    # Load JSON
    with open(input_path, "r") as f:
        data = json.load(f)

    if "requirements" not in data:
        raise ValueError("JSON must contain 'requirements'")

    requirements = data["requirements"]
    texts = [req.get("text", "") for req in requirements]

    # If models are missing, fall back to a simple demo-stable heuristic classifier
    if fr_model is None or nfr_model is None:
        stage1 = []
        final_labels = []
        for t in texts:
            t_l = (t or "").lower()
            # very small heuristic: treat "shall/ must/ should" as Functional
            if any(k in t_l for k in [" shall ", " must ", " should "]):
                stage1.append("FR")
                final_labels.append("Functional")
            else:
                stage1.append("NFR")
                final_labels.append("Non-Functional")
    else:
        # Stage 1 prediction
        stage1 = fr_model.predict(texts)

        # Stage 2 prediction
        final_labels = []
        for t, s1 in zip(texts, stage1):
            if s1 == "FR":
                final_labels.append("Functional")
            else:
                final_labels.append(nfr_model.predict([t])[0])

    # Construct output JSON
    output = {"requirements": []}
    for req, s1_label, final_label in zip(requirements, stage1, final_labels):
        output["requirements"].append({
            "id": req["id"],
            "type": "Functional" if s1_label == "FR" else "Non-Functional",
            "subtype": final_label,
            "text": req["text"]
        })

    output["requirements"] = fix_misclassifications(output["requirements"])

    # Save JSON
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved classified requirements to: {output_path}")
    return output

