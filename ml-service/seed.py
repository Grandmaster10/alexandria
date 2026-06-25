from datasets import load_dataset
import json
import requests
import time
import random

NESTJS_URL      = "http://backend-api:3001/books"
RANDOM_STATE    = 42
MIN_DESC_LENGTH = 50

def load_dataset_rows():
    """Load the full dataset, deduplicate, and return all valid rows."""
    print("Downloading dataset from HuggingFace...")
    dataset = load_dataset(
        "svastikkka/BOOK-RECOMMENDER-DATASET",
        data_files="data/books_with_emotions.csv",
        split="train"
    )

    valid_rows = []
    seen_titles = set()
    
    for row in dataset:
        title = str(row.get('title', '')).strip().lower()
        desc = str(row.get('description', ''))
        if len(desc) >= MIN_DESC_LENGTH and title not in seen_titles:
            seen_titles.add(title)
            valid_rows.append(row)

    random.seed(RANDOM_STATE)
    random.shuffle(valid_rows)

    print(f"Valid rows: {len(valid_rows)} books (deduplicated, min {MIN_DESC_LENGTH} char desc)")
    return valid_rows


def seed_database(rows: list):
    """POST every book to the NestJS API."""
    total = len(rows)
    print(f"\nSeeding database with {total} books...\n")
    success_count = 0
    skip_count    = 0

    for row in rows:
        title       = str(row.get('title', '')).strip()
        author      = str(row.get('authors', '') or 'Unknown Author').strip()
        description = str(row.get('description', '')).strip()
        book_type   = str(row.get('categories', '') or 'Fiction').strip()

        if not author:   author    = 'Unknown Author'
        if not book_type: book_type = 'Fiction'

        payload = {
            "title":       title,
            "author":      author,
            "type":        book_type,
            "description": description,
        }

        try:
            res = requests.post(NESTJS_URL, json=payload, timeout=30)
            if res.status_code == 201:
                success_count += 1
                pct = success_count / total * 100
                print(f"  [{success_count:>4}/{total}  {pct:4.1f}%] ✓ {title[:60]}")
            else:
                skip_count += 1
                print(f"  [SKIP] {title[:50]}: {res.text[:60]}")
        except Exception as e:
            skip_count += 1
            print(f"  [ERR]  {title[:50]}: {e}")

        time.sleep(0.05)

    print(f"Seeding complete")
    print(f"Added  : {success_count}")
    print(f"Skipped: {skip_count}")

if __name__ == "__main__":
    rows = load_dataset_rows()
    seed_database(rows)