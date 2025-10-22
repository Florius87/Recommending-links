import pandas as pd
import numpy as np
import os
import pickle
import hashlib
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

ARTICLES_CSV = "articles_metadata.csv"
EMBEDDINGS_FILE = "embeddings.pkl"  # stores {"embeddings": np.ndarray, "signature": str, "model": str}
RECOMMENDATIONS_CSV = "internal_link_recommendations.csv"
TOP_K = 8
MAX_ARTICLES = None  # Limit for testing; set None to process all
MODEL_NAME = "all-MiniLM-L6-v2"


def ensure_unique_and_ordered(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure deterministic order and unique URLs."""
    if "url" not in df.columns:
        raise ValueError("Input CSV must contain a 'url' column.")
    # Drop rows without URL, then de-duplicate by URL
    df = df.dropna(subset=["url"]).drop_duplicates(subset=["url"]).copy()
    # Sort for stability so embeddings always align with rows
    df = df.sort_values("url").reset_index(drop=True)
    return df


def combine_text(row: pd.Series) -> str:
    """Combine title + excerpt + keywords into a single string."""
    parts = [
        str(row.get("title", "") or ""),
        str(row.get("excerpt", "") or ""),
        str(row.get("keywords", "") or ""),
    ]
    return ". ".join([p.strip() for p in parts if p.strip()])


def dataset_signature(urls: pd.Series, texts: pd.Series, model_name: str) -> str:
    """
    Build a short signature that changes whenever order/rows/texts/model changes.
    This prevents stale embedding caches from being reused.
    """
    hasher = hashlib.md5()
    hasher.update(model_name.encode("utf-8"))
    # Join with null separators to avoid accidental collisions
    for u, t in zip(urls.tolist(), texts.tolist()):
        hasher.update(b"\x00")
        hasher.update((u or "").encode("utf-8", errors="ignore"))
        hasher.update(b"\x00")
        hasher.update((t or "").encode("utf-8", errors="ignore"))
    return hasher.hexdigest()


def load_or_build_embeddings(texts: pd.Series, signature: str, model_name: str):
    """Load embeddings if signature matches; otherwise (re)compute and save."""
    need_rebuild = True
    if os.path.exists(EMBEDDINGS_FILE):
        try:
            with open(EMBEDDINGS_FILE, "rb") as f:
                payload = pickle.load(f)
            emb = payload.get("embeddings", None)
            sig = payload.get("signature", None)
            mdl = payload.get("model", None)
            # Validate shape and signature
            if (
                emb is not None
                and hasattr(emb, "shape")
                and emb.shape[0] == len(texts)
                and sig == signature
                and mdl == model_name
            ):
                need_rebuild = False
                return emb
        except Exception:
            # Any read/parse issue triggers a rebuild
            need_rebuild = True

    # Recompute
    print("Computing embeddings with sentence-transformers...")
    model = SentenceTransformer(model_name)
    emb = model.encode(texts.tolist(), show_progress_bar=True)

    # Persist with signature for future validation
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump(
            {"embeddings": emb, "signature": signature, "model": model_name},
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(f"Saved embeddings to {EMBEDDINGS_FILE}.")
    return emb


def main():
    print(f"Loading articles from {ARTICLES_CSV}...")
    df = pd.read_csv(ARTICLES_CSV)
    df = ensure_unique_and_ordered(df)

    if MAX_ARTICLES:
        df = df.head(MAX_ARTICLES)
        print(f"Limiting to first {MAX_ARTICLES} articles for testing.")

    # Build combined text column
    df["combined_text"] = df.apply(combine_text, axis=1)

    # Guard: need at least 2 articles to make recommendations
    if len(df) < 2:
        print("Not enough articles to compute recommendations (need at least 2).")
        pd.DataFrame(
            columns=["source_url", "target_url", "similarity_score", "anchor_text"]
        ).to_csv(RECOMMENDATIONS_CSV, index=False)
        return

    # Create a dataset signature tied to (urls, combined_text, model)
    sig = dataset_signature(df["url"], df["combined_text"], MODEL_NAME)

    # Load or compute embeddings
    print("Loading/creating embeddings...")
    embeddings = load_or_build_embeddings(df["combined_text"], sig, MODEL_NAME)

    # Similarity matrix
    print("Computing cosine similarity matrix...")
    similarity_matrix = cosine_similarity(embeddings)
    n = len(df)
    if similarity_matrix.shape != (n, n):
        # Last-resort rebuild if something is off
        print("Warning: similarity matrix shape mismatch. Recomputing embeddings fresh.")
        if os.path.exists(EMBEDDINGS_FILE):
            try:
                os.remove(EMBEDDINGS_FILE)
            except OSError:
                pass
        embeddings = load_or_build_embeddings(df["combined_text"], sig, MODEL_NAME)
        similarity_matrix = cosine_similarity(embeddings)

    # Build recommendations
    recommendations = []
    top_k = max(1, min(TOP_K, n - 1))  # never exceed n-1

    for idx, source_url in enumerate(df["url"]):
        sim_scores = similarity_matrix[idx].astype(float).copy()
        # Exclude self
        sim_scores[idx] = -1.0

        # Get top_k targets
        top_indices = np.argsort(sim_scores)[-top_k:][::-1]

        for target_idx in top_indices:
            recommendations.append(
                {
                    "source_url": source_url,
                    "target_url": df.at[target_idx, "url"],
                    "similarity_score": float(sim_scores[target_idx]),
                    "anchor_text": df.at[target_idx, "title"],
                }
            )

    rec_df = pd.DataFrame(recommendations)
    rec_df.to_csv(RECOMMENDATIONS_CSV, index=False)
    print(f"Recommendations saved to {RECOMMENDATIONS_CSV}")


if __name__ == "__main__":
    main()
