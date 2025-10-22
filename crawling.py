import requests
import csv
import os
from bs4 import BeautifulSoup
import json
import xml.etree.ElementTree as ET

# Configuration
SITEMAP_URL = "https://florisera.com/post-sitemap.xml"
CSV_FILE = "articles_metadata.csv"
BATCH_SIZE = 105  # Number of articles to process per run; adjust as needed

# CSV columns - add/remove as you want
CSV_COLUMNS = [
    "url",
    "title",
    "excerpt",
    "meta_description",
    "keywords",
    "categories",
    "processed",
]


def load_processed_urls():
    """Load already processed URLs from CSV"""
    if not os.path.isfile(CSV_FILE):
        return set()
    with open(CSV_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return set(row["url"] for row in reader if row.get("processed") == "1")

def save_article_metadata(article, processed=True):
    """Append or update article metadata to CSV"""
    file_exists = os.path.isfile(CSV_FILE)
    if not file_exists:
        # Write header if file does not exist
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()

    # Append new row
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        article["processed"] = "1" if processed else "0"
        writer.writerow(article)

def fetch_sitemap_urls():
    """Fetch sitemap and parse URLs"""
    resp = requests.get(SITEMAP_URL)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    # Namespace often present in sitemaps, define to parse
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [elem.text for elem in root.findall(".//ns:url/ns:loc", ns)]
    return urls

def extract_metadata_from_html(html, url):
    """Parse HTML and extract metadata including excerpt"""
    soup = BeautifulSoup(html, "html.parser")

    # Title from <title> or og:title meta tag
    title = (
        soup.title.string.strip()
        if soup.title and soup.title.string
        else (soup.find("meta", property="og:title") or {}).get("content", "")
    )

    # Meta description
    meta_description = (
        soup.find("meta", attrs={"name": "description"})
        or soup.find("meta", property="og:description")
    )
    meta_description = meta_description["content"].strip() if meta_description else ""

    # Keywords: Extract tags from tag cloud in footer as keywords (comma separated)
    tagcloud_div = soup.find("div", class_="vlt-single-post-tags__tagcloud")
    if tagcloud_div:
        keywords = [a.get_text(strip=True) for a in tagcloud_div.find_all("a")]
    else:
        keywords = []
    keywords_str = ", ".join(keywords)

    # Categories / articleSection (list) from JSON-LD
    categories = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                items = [data]
            elif isinstance(data, list):
                items = data
            else:
                items = []
            for item in items:
                if item.get("@type") == "Article":
                    cats = item.get("articleSection")
                    if isinstance(cats, list):
                        categories.extend(cats)
                    elif isinstance(cats, str):
                        categories.append(cats)
        except Exception:
            continue
    categories = ", ".join(set(categories))

    # Excerpt: try to extract from JS var post.excerpt inside <script> (Elementor data)
    excerpt = ""
    for script in soup.find_all("script"):
        if not script.string:
            continue
        if '"post":' in script.string and '"excerpt":' in script.string:
            try:
                start = script.string.find('"post":')
                snippet = script.string[start:]
                exc_start = snippet.find('"excerpt":"')
                if exc_start != -1:
                    exc_start += len('"excerpt":"')
                    exc_end = snippet.find('"', exc_start)
                    excerpt = snippet[exc_start:exc_end]
                    excerpt = excerpt.encode("utf-8").decode("unicode_escape")
                    break
            except Exception:
                continue

    if not excerpt:
        excerpt = meta_description

    return {
        "url": url,
        "title": title,
        "excerpt": excerpt,
        "meta_description": meta_description,
        "keywords": keywords_str,
        "categories": categories,
    }


def main():
    print("Loading processed URLs...")
    processed_urls = load_processed_urls()

    print("Fetching sitemap URLs...")
    urls = fetch_sitemap_urls()

    # Filter URLs to only new ones
    new_urls = [u for u in urls if u not in processed_urls]
    if not new_urls:
        print("No new URLs to process. Exiting.")
        return

    to_process = new_urls[:BATCH_SIZE]

    for url in to_process:
        print(f"Processing: {url}")
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            metadata = extract_metadata_from_html(resp.text, url)
            save_article_metadata(metadata)
            print(f"Saved metadata for {url}")
        except Exception as e:
            print(f"Failed to process {url}: {e}")

if __name__ == "__main__":
    main()
