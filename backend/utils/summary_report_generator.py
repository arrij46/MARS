import json
from pathlib import Path
from collections import defaultdict

# ── PLACEHOLDER FILE NAMES ─────────────────────────────
INPUT_FILE      = "./agents/cdn/data/cdn_initial_input_"
ATOMIC_FILE     = "./agents/refinement/results/atomic_refinement_"
CLASSIFIED_FILE = "./agents/refinement/results/classified_refinement_"
SIAMESE_FILE    = "./agents/cdn/results/cdn_results_"
USER_STORY_FILE    = "./agents/userStory/results/evaluation_"
OUTPUT_FILE     = "./results/final_summary_report_" 
# ──────────────────────────────────────────────────────

class SummaryReport:
    def load(self, path):
        if path is None:
            return None
        p = Path(path)
        if not p.exists():
            print(f"  [warn] file not found: {path}")
            return None
        with open(p) as f:
            return json.load(f)

    def extract_reqs(self, data):
        if data is None:
            return []
        return data.get("requirements", [])

    def build_summary(self, report_id):
        # ── Load files ───────────────────────────────────────
        raw_input   = self.load(f'{INPUT_FILE}{report_id}.json')
        raw_atomic  = self.load(f'{ATOMIC_FILE}{report_id}.json')
        raw_classed = self.load(f'{CLASSIFIED_FILE}{report_id}.json')
        raw_siamese = self.load(f'{SIAMESE_FILE}{report_id}.json')
        user_story = self.load(f'{USER_STORY_FILE}{report_id}.json')

        original_reqs   = self.extract_reqs(raw_input)
        atomic_reqs     = self.extract_reqs(raw_atomic)
        classified_reqs = self.extract_reqs(raw_classed)
        user_story_info = user_story.get("summary_metrics", [])

        # ── Original requirements ───────────────────────────
        original_section = {
            "count": len(original_reqs),
            "requirements": [{"id": r["id"], "text": r["text"]} for r in original_reqs]
        }

        # ── Atomic requirements ─────────────────────────────
        atomic_section = {"count": len(atomic_reqs)}

        # ── Classification (FR / NFR) ───────────────────────
        type_map = defaultdict(lambda: defaultdict(list))
        for r in classified_reqs:
            t  = r.get("type", "Unknown")
            st = r.get("subtype", "Unknown")
            type_map[t][st].append({"id": r["id"], "text": r["text"]})

        types_section = {}
        for t, subtypes in type_map.items():
            subtype_data = {}
            total = 0
            for st, reqs in subtypes.items():
                subtype_data[st] = {"count": len(reqs), "requirements": reqs}
                total += len(reqs)
            types_section[t] = {"count": total, "subtypes": subtype_data}

        classification_section = {
            "total_classified": len(classified_reqs),
            "types": types_section
        }

        # ── Duplicates & Conflicts ──────────────────────────
        pairs_section = {
            "duplicate_pairs": {"count": 0, "pairs": []},
            "conflict_pairs":  {"count": 0, "pairs": []},
            "neutral_pairs":   {"count": 0}
        }

        if raw_siamese:
            siamese_data = raw_siamese.get("siamese_results", raw_siamese)
            all_pairs = []
            if isinstance(siamese_data, dict):
                for v in siamese_data.values():
                    if isinstance(v, list):
                        all_pairs.extend(v)
            elif isinstance(siamese_data, list):
                all_pairs = siamese_data

            duplicates, conflicts, neutrals = [], [], []

            for p in all_pairs:
                label = (p.get("final_label") or p.get("predicted_class") or "").lower()
                entry = {"req1": p.get("req1"), "req2": p.get("req2"), "confidence": round(p.get("confidence", 0), 4)}
                if label == "duplicate":
                    duplicates.append(entry)
                elif label == "conflict":
                    conflicts.append(entry)
                else:
                    neutrals.append(entry)

            pairs_section = {
                "duplicate_pairs": {"count": len(duplicates), "pairs": duplicates},
                "conflict_pairs":  {"count": len(conflicts),  "pairs": conflicts},
                "neutral_pairs":   {"count": len(neutrals)}
            }

        # ── Metadata from siamese file if available ─────────
        meta = {}
        if raw_siamese:
            m = raw_siamese.get("metadata", {})
            meta = {
                "conv_id": m.get("conv_id"),
            }

        # ── Assemble final report ───────────────────────────
        report = {
            "report_type": "requirements_pipeline_summary",
            "metadata": meta,
            "summary": {
                "total_original":    original_section["count"],
                "total_atomic":      atomic_section["count"],
                "total_classified":  classification_section["total_classified"],
                "total_functional":  classification_section["types"].get("Functional", {}).get("count", 0),
                "total_non_functional": classification_section["types"].get("Non-Functional", {}).get("count", 0),
                "total_duplicate_pairs": pairs_section["duplicate_pairs"]["count"],
                "total_conflict_pairs":  pairs_section["conflict_pairs"]["count"],
                "total_neutral_pairs":   pairs_section["neutral_pairs"]["count"],
                "total_user_stories": user_story_info["total_stories"]
            },
            "original_requirements": original_section,
            "atomic_requirements":   atomic_section,
            "classification":        classification_section,
            "pairs":                 pairs_section,
            "user_story_metadata": user_story_info
        }
        path = f'{OUTPUT_FILE}{report_id}.json'
        out = Path(path)
        with open(out, "w") as f:
            json.dump(report, f, indent=2)

        return report




def main():
    print("Building summary report...")
    classs = SummaryReport()
    report = classs.build_summary('elicit-1774373552549')

    print(f"Done")
    print(f"  Original reqs  : {report['summary']['total_original']}")
    print(f"  Atomic reqs    : {report['summary']['total_atomic']}")
    print(f"  Functional     : {report['summary']['total_functional']}")
    print(f"  Non-Functional : {report['summary']['total_non_functional']}")
    print(f"  Duplicates     : {report['summary']['total_duplicate_pairs']}")
    print(f"  Conflicts      : {report['summary']['total_conflict_pairs']}")

if __name__ == "__main__":
    main()