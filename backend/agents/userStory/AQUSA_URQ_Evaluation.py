import json
import re
import os
from collections import Counter, defaultdict
from typing import Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


ROLE_PATTERN = r"As a[n]?\s+([^,]+)"
MEANS_PATTERNS = [
    r"I want to",
    r"I am able to",
    r"I'm able to",
    r"I can",
    r"I need to"
]
END_PATTERN = r"so that\s+(.*)"

CONJUNCTIONS = [" and ", " & ", " + ", " or ", "/", "\\", ">", "<"]

SPECIAL_PUNCT = r"[\-\;\?\*]"
BRACKET_PATTERN = r"\(.*?\)|\[.*?\]|\{.*?\}"

CREATE_VERBS = ["create", "add", "register"]
DEPENDENT_VERBS = ["delete", "update", "edit", "view", "read"]

VAGUE_WORDS = ["very", "quickly", "fast", "etc", "some", "many"]


def parse_story(text: str):
    role = None
    means = None
    ends = None
    format_indicator = None

    role_match = re.search(ROLE_PATTERN, text, re.IGNORECASE)
    if role_match:
        role = role_match.group(1).strip()

    lower_text = text.lower()

    for pattern in MEANS_PATTERNS:
        if pattern.lower() in lower_text:
            format_indicator = pattern
            parts = re.split(pattern, text, flags=re.IGNORECASE)
            if len(parts) > 1:
                means_part = parts[1]
                means = re.split("so that", means_part, flags=re.IGNORECASE)[0].strip()
            break

    end_match = re.search(END_PATTERN, text, re.IGNORECASE)
    if end_match:
        ends = end_match.group(1).strip()

    return role, means, ends, format_indicator


def check_well_formed(role, means):
    return role is not None and means is not None


def check_atomic(means):
    if not means:
        return False
    lower_means = means.lower()
    for conj in CONJUNCTIONS:
        if conj in lower_means:
            return False
    return True


def check_minimal(text):
    if re.search(SPECIAL_PUNCT, text):
        return False
    if re.search(BRACKET_PATTERN, text):
        return False
    return True


def check_full_sentence(text):
    return text.strip().endswith(".")


def check_estimatable(means):
    if not means:
        return False
    word_count = len(means.split())
    return word_count < 25


def urq_complete(role, means, ends):
    return role is not None and means is not None and ends is not None


def urq_simple(means):
    if not means:
        return False
    if len(means.split()) > 30:
        return False
    lower_means = means.lower()
    for conj in CONJUNCTIONS:
        if conj in lower_means:
            return False
    return True


def urq_accurate(text):
    lower_text = text.lower()
    for w in VAGUE_WORDS:
        if w in lower_text:
            return False
    return True


def urq_consistent():
    return True


def urq_semantic_uniqueness(texts, threshold=0.85):
    if len(texts) <= 1:
        return set()

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)
    similarity_matrix = cosine_similarity(tfidf_matrix)

    duplicates = set()

    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if similarity_matrix[i][j] > threshold:
                duplicates.add(i)
                duplicates.add(j)

    return duplicates


def check_uniformity(formats):
    most_common = Counter(formats).most_common(1)
    if not most_common:
        return {}
    standard = most_common[0][0]
    result = {}
    for idx, fmt in enumerate(formats):
        result[idx] = (fmt == standard)
    return result


def check_exact_duplicates(texts):
    duplicates = set()
    seen = {}
    for idx, t in enumerate(texts):
        if t in seen:
            duplicates.add(idx)
            duplicates.add(seen[t])
        else:
            seen[t] = idx
    return duplicates


def check_basic_completeness(stories_parsed):
    verbs_objects = defaultdict(set)

    for idx, (role, means, ends, fmt) in enumerate(stories_parsed):
        if means:
            words = means.lower().split()
            for v in CREATE_VERBS:
                if v in words:
                    obj = words[-1]
                    verbs_objects[obj].add("create")

    incomplete = set()

    for idx, (role, means, ends, fmt) in enumerate(stories_parsed):
        if means:
            words = means.lower().split()
            for v in DEPENDENT_VERBS:
                if v in words:
                    obj = words[-1]
                    if "create" not in verbs_objects[obj]:
                        incomplete.add(idx)

    return incomplete


def final_verdict(story):

    aqusa_checks = [
        story["well_formed"],
        story["atomic"],
        story["minimal"],
        story["uniform"],
        story["unique"],
        story["estimatable"],
        story["complete_dependency"]
    ]

    urq_checks = [
        story["urq_complete"],
        story["urq_simple"],
        story["urq_accurate"],
        story["urq_consistent"],
        story["urq_unique_semantic"]
    ]

    aqusa_true = sum(aqusa_checks)
    urq_true = sum(urq_checks)

    aqusa_false = len(aqusa_checks) - aqusa_true
    urq_false = len(urq_checks) - urq_true

    total_false = aqusa_false + urq_false

    if aqusa_true == 7 and urq_true == 5:
        return "HIGH_QUALITY"

    if aqusa_true >= 4 and urq_true >= 3:
        return "MODERATE_QUALITY"

    if total_false >= 6:
        return "LOW_QUALITY"

    return "LOW_QUALITY"


def evaluate_user_stories(input_json: Dict):

    stories = input_json["user_stories"]
    texts = [s["text"] for s in stories]

    parsed = []
    formats = []
    results = []

    for s in stories:
        role, means, ends, fmt = parse_story(s["text"])
        parsed.append((role, means, ends, fmt))
        formats.append(fmt)

        story_eval = {
            "requirement_id": s["requirement_id"],
            "user_story_id": s["user_story_id"],

            "well_formed": check_well_formed(role, means),
            "atomic": check_atomic(means),
            "minimal": check_minimal(s["text"]),
            "full_sentence": check_full_sentence(s["text"]),
            "estimatable": check_estimatable(means),

            "urq_complete": urq_complete(role, means, ends),
            "urq_simple": urq_simple(means),
            "urq_accurate": urq_accurate(s["text"]),
            "urq_consistent": urq_consistent()
        }

        results.append(story_eval)

    uniform_results = check_uniformity(formats)
    duplicate_indices = check_exact_duplicates(texts)
    incomplete_indices = check_basic_completeness(parsed)
    semantic_duplicates = urq_semantic_uniqueness(texts)

    for idx in range(len(results)):
        results[idx]["uniform"] = uniform_results.get(idx, True)
        results[idx]["unique"] = idx not in duplicate_indices
        results[idx]["complete_dependency"] = idx not in incomplete_indices
        results[idx]["urq_unique_semantic"] = idx not in semantic_duplicates

    for idx in range(len(results)):
        results[idx]["final_verdict"] = final_verdict(results[idx])

    total = len(results)

    summary = {
        "total_stories": total,

        "well_formed_rate": sum(r["well_formed"] for r in results) / total,
        "atomic_rate": sum(r["atomic"] for r in results) / total,
        "minimal_rate": sum(r["minimal"] for r in results) / total,
        "uniform_rate": sum(r["uniform"] for r in results) / total,
        "unique_rate": sum(r["unique"] for r in results) / total,
        "estimatable_rate": sum(r["estimatable"] for r in results) / total,
        "completeness_rate": sum(r["complete_dependency"] for r in results) / total,

        "urq_complete_rate": sum(r["urq_complete"] for r in results) / total,
        "urq_simple_rate": sum(r["urq_simple"] for r in results) / total,
        "urq_accuracy_rate": sum(r["urq_accurate"] for r in results) / total,
        "urq_semantic_uniqueness_rate": sum(r["urq_unique_semantic"] for r in results) / total
    }

    return {
        "story_level_results": results,
        "summary_metrics": summary
    }


# -----------------------------
# Usage
# -----------------------------

if __name__ == "__main__":

    with open("results/user_stories_conv-c9900fc6-f1b1-4b1a-818d-c16f3252eade.json", "r") as f:
        data = json.load(f)

    evaluation = evaluate_user_stories(data)

    print(json.dumps(evaluation, indent=4))

    # 🔹 Generate random 4 digit id
    random_id = random.randint(1000, 9999)

    filename = f"evaluation_results_convid_{random_id}.json"

    save_path = os.path.join("results", filename)

    with open(save_path, "w") as outfile:
        json.dump(evaluation, outfile, indent=4)

    print(f"\nEvaluation saved to: {save_path}")