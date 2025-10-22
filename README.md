# Internal Linking Toolkit — README

A 3-step toolkit to (1) crawl your site and collect article metadata, (2) compute content-based internal link recommendations, and (3) visualize them as an interactive network.

## Requirements
- Python 3.9+
- `requests`, `beautifulsoup4`, `pandas`, `numpy`, `scikit-learn`, `sentence-transformers`, `networkx`, `pyvis`

---

## Files
- `crawling.py` — pulls URLs from your sitemap and extracts per-article metadata into CSV. :contentReference[oaicite:0]{index=0}  
- `recommendations.py` — builds sentence-transformer embeddings, computes cosine similarity, and writes top link suggestions. :contentReference[oaicite:1]{index=1}  
- `visualize_word_network.py` — turns the CSV into an interactive HTML network (directed graph). :contentReference[oaicite:2]{index=2}

---

## Configure

### crawling.py
| Variable     | Default                                           | Purpose |
|--------------|---------------------------------------------------|---------|
| SITEMAP_URL  | https://florisera.com/post-sitemap.xml           | Source of article URLs. :contentReference[oaicite:3]{index=3} |
| CSV_FILE     | articles_metadata.csv                             | Output metadata store. :contentReference[oaicite:4]{index=4} |
| BATCH_SIZE   | 105                                               | Max pages processed per run. :contentReference[oaicite:5]{index=5} |

Extracted fields: `url`, `title`, `excerpt`, `meta_description`, `keywords`, `categories`, `processed`. :contentReference[oaicite:6]{index=6}

### recommendations.py
| Variable          | Default                 | Purpose |
|-------------------|-------------------------|---------|
| ARTICLES_CSV      | articles_metadata.csv   | Input articles (from crawler). :contentReference[oaicite:7]{index=7} |
| EMBEDDINGS_FILE   | embeddings.pkl          | Cache to avoid recompute. :contentReference[oaicite:8]{index=8} |
| RECOMMENDATIONS_CSV | internal_link_recommendations.csv | Output suggestions. :contentReference[oaicite:9]{index=9} |
| TOP_K             | 8                       | Suggestions per source article. :contentReference[oaicite:10]{index=10} |
| MODEL_NAME        | all-MiniLM-L6-v2        | SentenceTransformer model. :contentReference[oaicite:11]{index=11} |

Builds a deterministic dataset signature to validate the embedding cache. :contentReference[oaicite:12]{index=12}

### visualize_word_network.py
- Reads `internal_link_recommendations.csv`, keeps edges with `similarity_score ≥ 0.3`, and writes `word_network.html`. :contentReference[oaicite:13]{index=13}

---

## How it works (brief)
1. **Crawl**: Fetch sitemap → visit each URL → parse HTML → extract title, excerpt (Elementor JSON if present), meta description, tags, categories → append to CSV. :contentReference[oaicite:14]{index=14}  
2. **Recommend**: Combine title + excerpt + keywords → embed with `SentenceTransformer` → cosine similarity → top-K targets per source → write CSV with `similarity_score` and suggested `anchor_text` (target title). :contentReference[oaicite:15]{index=15}  
3. **Visualize**: Load CSV → create directed NetworkX graph → export interactive PyVis HTML. :contentReference[oaicite:16]{index=16}

---

## Run
1. Crawl: `python crawling.py` :contentReference[oaicite:17]{index=17}  
2. Recommend: `python recommendations.py` :contentReference[oaicite:18]{index=18}  
3. Visualize: `python visualize_word_network.py` (opens/creates `word_network.html`) :contentReference[oaicite:19]{index=19}

---

## Outputs
- `articles_metadata.csv` — article metadata ledger (append-only per run). :contentReference[oaicite:20]{index=20}  
- `internal_link_recommendations.csv` — columns: `source_url`, `target_url`, `similarity_score`, `anchor_text`. :contentReference[oaicite:21]{index=21}  
- `word_network.html` — interactive graph to explore suggested links. :contentReference[oaicite:22]{index=22}

---

## Tips
- Re-scan from scratch by deleting the CSVs/PKL cache.   
- Raise `BATCH_SIZE` or adjust `TOP_K` to tune throughput/granularity.   
- If you see too many edges, increase the visualization cutoff (e.g., `score >= 0.35`). :contentReference[oaicite:25]{index=25}

---

## License
MIT License (or your preferred). Include a `LICENSE` file in the repository.
