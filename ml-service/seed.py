from datasets import load_dataset
import json
import requests
import time

NESTJS_URL = "http://localhost:3001/books"

def seed_database():
    print("Downloading dataset")
    dataset = load_dataset("svastikkka/BOOK-RECOMMENDER-DATASET", data_files="data/books_with_emotions.csv", split="train")
    
    success_count = 0
    
    for row in dataset:
        title = row.get('title')
        author = row.get('authors')
        description = row.get('description')
        book_type = row.get('categories')

        if len(str(description)) < 50: 
            continue

        if not author: 
            author = "Unknown Author"
        if not book_type:
            book_type = "Fiction"

        payload = {
            "title": str(title),
            "author": str(author),
            "type": book_type,
            "description": description
        }
            
        try:
            res = requests.post(NESTJS_URL, json=payload)
            
            if res.status_code == 201:
                success_count += 1
                print(f"Added [{success_count}]: {title} ({book_type})")
            else:
                print(f"Failed to add {title}: {res.text}")
        except Exception as e:
            print(f"Server error on {title}: {e}")

        time.sleep(0.1) 

        if success_count >= 1500:
            print("Seeding successful")
            break

if __name__ == "__main__":
    seed_database()