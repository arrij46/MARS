import json

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from collections import defaultdict


async def extract_features(requirements: list[str], output_file: str):

    # # 1. Load requirements from file
    # with open(input_file, "r") as f:
    #     requirements = [line.strip() for line in f if line.strip()]

    # 2. Load models
    nlp = spacy.load("en_core_web_sm")
    embedder = SentenceTransformer("all-mpnet-base-v2")

    # 3. Extract action-object pairs
    actions = []
    objects = []

    for req in requirements:
        doc = nlp(req)
        verb = None
        obj = None

        for token in doc:
            if token.pos_ == "VERB" and verb is None:
                verb = token.lemma_

        for token in doc:
            if token.dep_ in ("dobj", "pobj") and obj is None:
                obj = token.lemma_

        actions.append(verb or "")
        objects.append(obj or "")

    # 4. Create hybrid embeddings
    sent_emb = embedder.encode(requirements, normalize_embeddings=True)
    act_emb = embedder.encode(actions, normalize_embeddings=True)
    obj_emb = embedder.encode(objects, normalize_embeddings=True)

    embeddings = np.hstack([
        sent_emb * 0.4,
        act_emb * 0.3,
        obj_emb * 0.3
    ])

    # 5. Hierarchical clustering
    clustering = AgglomerativeClustering(
        metric="cosine",
        linkage="average",
        distance_threshold=0.6,
        n_clusters=None
    )

    labels = clustering.fit_predict(embeddings)

    # 6. Collect clusters
    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        clusters[label].append(i)

    # 7. Build final clusters
    final_clusters = []
    for feature_id, req_ids in clusters.items():
        current_cluster = [requirements[r] for r in req_ids]
        final_clusters.append(current_cluster)

    # 8. Save to output file
    with open(f'./agents/document/results/{output_file}', "w") as f:
        json.dump(final_clusters, f, indent=2)

    return final_clusters



if __name__ == "__main__":
    #****main
    reqs =  [
        "The system shall allow users to register and log in with secure credentials.",
        "The system shall support multi-factor authentication (MFA) for sensitive actions.",
        "The system shall allow users to reset their password via email or SMS.",
        "The system shall lock user accounts after three failed login attempts.",
        "The system shall allow users to add, edit, or remove smart devices.",
        "The system shall categorize devices by type and room.",
        "The system shall allow scheduling automated actions for devices.",
        "The system shall display real-time status of connected devices.",
        "The system shall monitor energy usage of all connected devices.",
        "The system shall provide visual dashboards for energy consumption trends.",
        "The system shall alert users when energy usage exceeds configured thresholds.",
        "The system shall detect unauthorized access attempts.",
        "The system shall notify users immediately of security events.",
        "The system shall allow users to arm and disarm security devices remotely.",
        "The system shall allow integration with voice assistants like Alexa and Google Home.",
        "The system shall allow sharing control of devices with family members with defined roles.",
        "The system shall support creating custom routines based on time or device events.",
        "The system shall allow users to enable or disable routines easily.",
        "The system shall provide pre-built automation templates for common scenarios.",
    ]
    clusters = extract_features(reqs)
    print("\n=== EXTRACTED FEATURES (CLUSTERS) ===\n")
    print(clusters)
