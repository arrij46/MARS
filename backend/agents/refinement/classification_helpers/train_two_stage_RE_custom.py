#!/usr/bin/env python3
"""
Two-stage FR -> NFR -> NFR-subclass classifier
Compatible with RE'17 QA dataset using short codes:
F, PE, LF, US, A, SE, FT, SC, etc.
"""

import sys
print("Python executable:", sys.executable)

import argparse
import os
import pandas as pd
import numpy as np
from joblib import dump

import warnings
warnings.filterwarnings("ignore")

# ML + NLP imports
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier, StackingClassifier

import nltk
# Download required NLTK resources if not available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet', quiet=True)

from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
STOPWORDS = set(stopwords.words("english"))

# SpaCy optional
try:
    import spacy
    SPACY_AVAILABLE = True
except (ImportError, OSError, RuntimeError):
    SPACY_AVAILABLE = False

# SentenceTransformer optional
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMER_AVAILABLE = True
except (ImportError, OSError, RuntimeError):
    SENTENCE_TRANSFORMER_AVAILABLE = False
    SentenceTransformer = None

# -------------------------------------------------------------------------
# 1. Label Mapping for RE'17 Short Codes
# -------------------------------------------------------------------------
def map_re_label(raw):
    raw = str(raw).strip().upper()

    if raw == "F":
        return "FR", "FR"

    mapping = {
        "PE": "performance",
        "LF": "usability",
        "US": "usability",
        "A":  "operational",
        "SE": "security",
        "FT": "reliability",
        "SC": "scalability",
        "MA": "maintainability",
        "PO": "portability",
        "RE": "reliability",
        "PR": "security",
    }

    if raw in mapping:
        return "NFR", mapping[raw]

    return "NFR", "other"

# -------------------------------------------------------------------------
# 2. Text Cleaner
# -------------------------------------------------------------------------
class TextCleaner:
    def __init__(self, use_spacy=True):
        self.use_spacy = use_spacy and SPACY_AVAILABLE
        if self.use_spacy:
            self.nlp = spacy.load("en_core_web_sm", disable=["parser","ner"])
        else:
            self.wnl = WordNetLemmatizer()

    def clean(self, text):
        text = str(text)
        if self.use_spacy:
            doc = self.nlp(text)
            return " ".join([t.lemma_.lower() for t in doc if t.is_alpha and not t.is_stop])
        toks = word_tokenize(text.lower())
        toks = [t for t in toks if t.isalpha() and t not in STOPWORDS]
        return " ".join([self.wnl.lemmatize(t) for t in toks])

# -------------------------------------------------------------------------
# 3. Meta Features
# -------------------------------------------------------------------------
class MetaFeatures:
    def __init__(self, use_spacy=True):
        self.use_spacy = use_spacy and SPACY_AVAILABLE
        if self.use_spacy:
            self.nlp = spacy.load("en_core_web_sm", disable=["parser","ner"])

    def extract(self, text):
        text = str(text)
        if self.use_spacy:
            doc = self.nlp(text)
            words = [t for t in doc if t.is_alpha]
            if not words:
                return [0]*6
            counts = {"NOUN":0, "VERB":0, "ADJ":0, "ADV":0}
            modal = 0
            for t in doc:
                if t.pos_ in counts:
                    counts[t.pos_] += 1
                if t.lemma_.lower() in ["shall","should","must","can","may","will","would","could"]:
                    modal += 1
            W = len(words)
            return [
                counts["NOUN"]/W,
                counts["VERB"]/W,
                counts["ADJ"]/W,
                counts["ADV"]/W,
                modal/W,
                W
            ]
        return [0]*6

# Picklable transformer for meta features
class MetaFeaturesTransformer:
    def __init__(self, use_spacy=True):
        self.meta = MetaFeatures(use_spacy)
    
    def transform(self, X):
        return np.vstack([self.meta.extract(t) for t in X])
    
    def fit(self, X, y=None):
        return self

# -------------------------------------------------------------------------
# 4. SentenceTransformer embeddings
# -------------------------------------------------------------------------
class SentenceTransformerFeatures:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts):
        return self.model.encode(texts, show_progress_bar=True)

# -------------------------------------------------------------------------
# 5. Build pipeline
# -------------------------------------------------------------------------
def build_pipeline(use_spacy=True, use_transformer=True, kbest=500):
    cleaner = TextCleaner(use_spacy)

    tfidf = TfidfVectorizer(
        ngram_range=(1,3),
        min_df=2,
        max_df=0.95,
        preprocessor=cleaner.clean
    )

    meta_transformer = MetaFeaturesTransformer(use_spacy)

    transformers = [
        ("tfidf", tfidf),
        ("meta", Pipeline([
            ("mf", meta_transformer),
            ("scale", StandardScaler())
        ]))
    ]

    if use_transformer and SENTENCE_TRANSFORMER_AVAILABLE:
        st = SentenceTransformerFeatures()
        transformers.append(("st", FunctionTransformer(st.encode, validate=False)))
    elif use_transformer and not SENTENCE_TRANSFORMER_AVAILABLE:
        print("Warning: SentenceTransformer not available, skipping transformer features")

    features = FeatureUnion(transformers)
    selector = SelectKBest(chi2, k=kbest)

    clf = StackingClassifier(
        estimators=[
            ("svc", LinearSVC(max_iter=30000)),
            ("rf", RandomForestClassifier(n_estimators=300))
        ],
        final_estimator=LinearSVC()
    )

    return Pipeline([
        ("features", features),
        ("selector", selector),
        ("clf", clf)
    ])

# -------------------------------------------------------------------------
# 6. Train Two-Stage Model
# -------------------------------------------------------------------------
def train_two_stage(df):
    print("Mapping RE'17 short-code labels...")

    df["stage1"], df["stage2"] = zip(*df["label"].apply(map_re_label))

    print("\n=== Training Stage 1: FR vs NFR ===")
    X = df["text"].astype(str).values
    y1 = df["stage1"].values
    fr_model = build_pipeline()
    fr_model.fit(X, y1)
    dump(fr_model, "models/re_fr_classifier.joblib")
    print("Saved: models/re_fr_classifier.joblib")

    print("\n=== Training Stage 2: NFR subclass ===")
    mask = df["stage1"] == "NFR"
    X2 = df.loc[mask, "text"].astype(str).values
    y2 = df.loc[mask, "stage2"].values
    nfr_model = build_pipeline()
    nfr_model.fit(X2, y2)
    dump(nfr_model, "models/re_nfr_subclassifier.joblib")
    print("Saved: models/re_nfr_subclassifier.joblib")

    print("\nTraining complete!")

# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True,
                        help="CSV with columns: id, text, label (short-code labels)")
    args = parser.parse_args()

    os.makedirs("models", exist_ok=True)
    df = pd.read_csv(args.input)

    if not {"text", "label"}.issubset(df.columns):
        raise ValueError("CSV must contain columns: text, label")

    train_two_stage(df)

if __name__ == "__main__":
    main()
