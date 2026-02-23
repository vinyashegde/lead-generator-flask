import os
import csv
import re
import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from dotenv import load_dotenv
import sys
import logging
import time

sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("email_google_search.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

load_dotenv('.env.local')
api_key = os.getenv("SERPAPI_KEY")
if not api_key:
    load_dotenv('.env')
    api_key = os.getenv("SERPAPI_KEY")

FOLDER = "wellness_gym_leads"

def extract_emails_from_text(text):
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = set(re.findall(pattern, text))
    junk = ['example.com', 'yourdomain', 'sentry.io', 'wixpress.com', 'google.com',
            'email.com', 'website.com', 'test.com', 'domain.com', 'placeholder']
    valid = {e for e in emails if len(e) < 50
             and not any(ext in e.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'])
             and not any(x in e.lower() for x in junk)}
    return valid

def search_email_google(business_name, city):
    """Use Google Search to find email for a business."""
    query = f'"{business_name}" {city} email contact'
    try:
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": 5
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        all_text = ""
        # Check snippets from organic results
        for r in results.get("organic_results", []):
            snippet = r.get("snippet", "")
            all_text += " " + snippet
            # Also check rich snippet / about_this_result
            rich = r.get("rich_snippet", {})
            if rich:
                for k, v in rich.items():
                    if isinstance(v, dict):
                        for kk, vv in v.items():
                            if isinstance(vv, str):
                                all_text += " " + vv
                    elif isinstance(v, str):
                        all_text += " " + v

        # Check knowledge graph
        kg = results.get("knowledge_graph", {})
        if kg:
            for key in ['email', 'description', 'snippet']:
                if key in kg and isinstance(kg[key], str):
                    all_text += " " + kg[key]
            # Check attributes
            for attr_key in ['attributes', 'known_attributes']:
                attrs = kg.get(attr_key, {})
                if isinstance(attrs, dict):
                    for k, v in attrs.items():
                        if isinstance(v, str):
                            all_text += " " + v

        emails = extract_emails_from_text(all_text)
        if emails:
            return ", ".join(emails)

        # Try scraping the first organic result page
        for r in results.get("organic_results", [])[:2]:
            link = r.get("link", "")
            if link and not any(x in link for x in ['facebook.com', 'instagram.com', 'youtube.com', 'twitter.com', 'linkedin.com']):
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    resp = requests.get(link, headers=headers, timeout=8)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        page_emails = extract_emails_from_text(soup.get_text(separator=' '))
                        # mailto
                        for a in soup.find_all('a', href=True):
                            if a['href'].startswith('mailto:'):
                                page_emails.add(a['href'].replace('mailto:', '').split('?')[0].strip())
                        if page_emails:
                            return ", ".join(page_emails)
                except:
                    pass

    except Exception as e:
        logging.error(f"Search error: {str(e)[:60]}")
    return ""

def process_csv(filename):
    filepath = os.path.join(FOLDER, filename)
    if not os.path.exists(filepath):
        return

    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    missing = [i for i, r in enumerate(rows) if not r.get('email', '').strip()]
    logging.info(f"\n{'='*50}")
    logging.info(f"{filename}: {len(rows)} leads, {len(missing)} missing emails")

    if not missing:
        return 0

    found_count = 0
    for idx in missing:
        row = rows[idx]
        title = row.get('title', '')
        city = row.get('city', '')

        logging.info(f"  [{idx+1}] Searching: {title}")
        email = search_email_google(title, city)
        if email:
            rows[idx]['email'] = email
            found_count += 1
            logging.info(f"    FOUND: {email}")
        else:
            logging.info(f"    Not found")
        time.sleep(0.5)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logging.info(f"Updated {filename}: Found {found_count}/{len(missing)} emails via Google Search")
    return found_count

if __name__ == "__main__":
    logging.info("FINDING MISSING EMAILS VIA GOOGLE SEARCH")
    total_found = 0
    for fn in sorted(os.listdir(FOLDER)):
        if fn.endswith('.csv'):
            total_found += (process_csv(fn) or 0)
    logging.info(f"\nTOTAL NEW EMAILS FOUND: {total_found}")
    logging.info("DONE")
