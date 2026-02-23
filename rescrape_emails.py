import os
import csv
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import sys
import logging
import time

sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("email_rescrape.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

FOLDER = "wellness_gym_leads"

def extract_emails_from_text(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = set(re.findall(email_pattern, text))
    valid = {e for e in emails if len(e) < 50
             and not any(ext in e.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'])
             and not any(x in e.lower() for x in ['example.com', 'yourdomain', 'sentry.io', 'wixpress.com', 'google.com', 'email.com', 'website.com'])}
    return valid

def scrape_email(url):
    if not url or not url.strip():
        return ""
    try:
        if not url.startswith('http'):
            url = 'http://' + url
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            text = soup.get_text(separator=' ')
            emails = extract_emails_from_text(text)
            # mailto links
            for a in soup.find_all('a', href=True):
                if a['href'].startswith('mailto:'):
                    em = a['href'].replace('mailto:', '').split('?')[0].strip()
                    if em and '@' in em:
                        emails.add(em)
            # Check contact/about pages
            if not emails:
                for pattern in [r'contact', r'about']:
                    links = soup.find_all('a', href=re.compile(pattern, re.I))
                    for link in links[:2]:
                        href = link.get('href')
                        if href:
                            if not href.startswith('http'):
                                base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                                href = base + (href if href.startswith('/') else '/' + href)
                            try:
                                cr = requests.get(href, headers=headers, timeout=8)
                                if cr.status_code == 200:
                                    cs = BeautifulSoup(cr.text, 'html.parser')
                                    emails.update(extract_emails_from_text(cs.get_text(separator=' ')))
                                    for a in cs.find_all('a', href=True):
                                        if a['href'].startswith('mailto:'):
                                            emails.add(a['href'].replace('mailto:', '').split('?')[0].strip())
                            except:
                                pass
                    if emails:
                        break
            filtered = {e for e in emails if '@' in e and '.' in e.split('@')[1]}
            if filtered:
                return ", ".join(filtered)
    except Exception as e:
        logging.error(f"Error scraping {url}: {str(e)[:60]}")
    return ""

def process_csv(filename):
    filepath = os.path.join(FOLDER, filename)
    if not os.path.exists(filepath):
        logging.info(f"File not found: {filepath}")
        return

    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    missing = [i for i, r in enumerate(rows) if not r.get('email', '').strip()]
    logging.info(f"\n{'='*50}")
    logging.info(f"{filename}: {len(rows)} leads, {len(missing)} missing emails")
    logging.info(f"{'='*50}")

    if not missing:
        return

    found_count = 0
    for idx in missing:
        row = rows[idx]
        website = row.get('website', '').strip()
        title = row.get('title', '')
        if not website:
            logging.info(f"  [{idx+1}] {title} - No website, skipping")
            continue

        logging.info(f"  [{idx+1}] {title} -> {website}")
        email = scrape_email(website)
        if email:
            rows[idx]['email'] = email
            found_count += 1
            logging.info(f"    FOUND: {email}")
        else:
            logging.info(f"    No email found")
        time.sleep(0.3)

    # Rewrite CSV
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logging.info(f"Updated {filename}: Found {found_count} new emails out of {len(missing)} missing")

if __name__ == "__main__":
    logging.info("RE-SCRAPING MISSING EMAILS FROM WELLNESS/GYM LEADS")
    for fn in sorted(os.listdir(FOLDER)):
        if fn.endswith('.csv'):
            process_csv(fn)
    logging.info("DONE - All CSVs updated")
