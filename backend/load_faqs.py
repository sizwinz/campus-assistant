"""
Script to load seed FAQs into the Campus Assistant database via API.
Run this AFTER the backend server is running.

Usage:
    python load_faqs.py

Or specify a different API URL:
    python load_faqs.py --url http://localhost:8000
"""
import json
import requests
import argparse
import sys
from getpass import getpass
from requests.auth import HTTPBasicAuth

def load_faqs(api_url: str = "http://localhost:8000", auth: HTTPBasicAuth | None = None):
    """Load FAQs from seed_faqs.json into the database."""

    # Check if server is running
    try:
        health = requests.get(f"{api_url}/api/v1/admin/health", timeout=5)
        print(f"Server status: {health.json().get('status', 'unknown')}")
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to {api_url}")
        print("Make sure the backend server is running:")
        print("  cd backend && python -m uvicorn app.main:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"Warning: Health check failed: {e}")

    # Load FAQs from JSON file
    try:
        with open("seed_faqs.json", "r", encoding="utf-8") as f:
            faqs = json.load(f)
        print(f"Loaded {len(faqs)} FAQs from seed_faqs.json")
    except FileNotFoundError:
        print("ERROR: seed_faqs.json not found. Run create_seed_faqs.py first.")
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in seed_faqs.json: {e}")
        return False

    # Option 1: Bulk import (faster)
    print("\nAttempting bulk import...")
    try:
        response = requests.post(
            f"{api_url}/api/v1/faqs/bulk-import",
            json=faqs,
            auth=auth,
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            print(f"Bulk import successful!")
            print(f"  Created: {result.get('created', 0)}")
            print(f"  Errors: {len(result.get('errors', []))}")
            if result.get('errors'):
                for err in result['errors'][:5]:
                    print(f"    - Index {err['index']}: {err['error']}")
            return True
        else:
            print(f"Bulk import failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            print("\nFalling back to individual imports...")
    except Exception as e:
        print(f"Bulk import error: {e}")
        print("Falling back to individual imports...")

    # Option 2: Individual imports (slower but more robust)
    success_count = 0
    error_count = 0

    for i, faq in enumerate(faqs):
        try:
            response = requests.post(
                f"{api_url}/api/v1/faqs/",
                json=faq,
                auth=auth,
                timeout=30
            )
            if response.status_code == 200:
                success_count += 1
                print(f"  [{i+1}/{len(faqs)}] Added: {faq['question'][:50]}...")
            else:
                error_count += 1
                print(f"  [{i+1}/{len(faqs)}] FAILED: {faq['question'][:30]}... - {response.status_code}")
        except Exception as e:
            error_count += 1
            print(f"  [{i+1}/{len(faqs)}] ERROR: {faq['question'][:30]}... - {e}")

    print(f"\nImport complete!")
    print(f"  Success: {success_count}")
    print(f"  Errors: {error_count}")

    return error_count == 0


def verify_faqs(api_url: str = "http://localhost:8000"):
    """Verify FAQs were loaded correctly."""
    try:
        response = requests.get(f"{api_url}/api/v1/faqs/", timeout=10)
        if response.status_code == 200:
            faqs = response.json()
            print(f"\nVerification: {len(faqs)} FAQs in database")

            # Show categories
            categories = {}
            for faq in faqs:
                cat = faq.get('category', 'uncategorized')
                categories[cat] = categories.get(cat, 0) + 1

            print("Categories:")
            for cat, count in sorted(categories.items()):
                print(f"  - {cat}: {count}")

            return True
        else:
            print(f"Verification failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Verification error: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load seed FAQs into database")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing FAQs")
    parser.add_argument("--username", default="admin", help="Admin username")
    parser.add_argument("--password", help="Admin password; prompts when omitted")
    args = parser.parse_args()

    print("=" * 60)
    print("Campus Assistant - FAQ Loader")
    print("=" * 60)
    print(f"API URL: {args.url}")
    print()

    if args.verify_only:
        verify_faqs(args.url)
    else:
        password = args.password or getpass("Admin password: ")
        auth = HTTPBasicAuth(args.username, password)
        if load_faqs(args.url, auth):
            verify_faqs(args.url)
        else:
            sys.exit(1)
