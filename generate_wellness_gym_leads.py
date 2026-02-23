import os
import csv
import time
import re
import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from dotenv import load_dotenv
from urllib.parse import urlparse
import sys
import logging

# Configure stdout to handle emojis on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Configure logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wellness_gym_execution.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Load environment variables
load_dotenv('.env.local')
api_key = os.getenv("SERPAPI_KEY")
if not api_key:
    load_dotenv('.env')
    api_key = os.getenv("SERPAPI_KEY")
if not api_key:
    print("Error: SERPAPI_KEY not found")
    exit(1)

OUTPUT_DIR = "wellness_gym_leads"

def extract_emails_from_text(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = set(re.findall(email_pattern, text))
    valid_emails = {e for e in emails if len(e) < 50
                    and not any(ext in e.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'])
                    and not any(x in e.lower() for x in ['example.com', 'yourdomain', 'sentry.io', 'wixpress.com', 'google.com'])}
    return valid_emails

def scrape_email_from_website(url):
    if not url:
        return ""
    try:
        if not url.startswith('http'):
            url = 'http://' + url
        logging.info(f"Scraping emails from {url}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator=' ')
            emails = extract_emails_from_text(text)
            # Also check mailto links
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if href.startswith('mailto:'):
                    email = href.replace('mailto:', '').split('?')[0].strip()
                    if email and '@' in email:
                        emails.add(email)
            # Check contact page if no emails found
            if not emails:
                contact_links = soup.find_all('a', href=re.compile(r'contact', re.I))
                for link in contact_links[:2]:
                    contact_url = link.get('href')
                    if contact_url:
                        if not contact_url.startswith('http'):
                            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                            contact_url = base_url + (contact_url if contact_url.startswith('/') else '/' + contact_url)
                        try:
                            cr = requests.get(contact_url, headers=headers, timeout=5)
                            if cr.status_code == 200:
                                cs = BeautifulSoup(cr.text, 'html.parser')
                                emails.update(extract_emails_from_text(cs.get_text(separator=' ')))
                                for a_tag in cs.find_all('a', href=True):
                                    href = a_tag['href']
                                    if href.startswith('mailto:'):
                                        emails.add(href.replace('mailto:', '').split('?')[0].strip())
                        except:
                            pass
            if emails:
                result = ", ".join(emails)
                logging.info(f"Found: {result}")
                return result
    except Exception as e:
        logging.error(f"Scrape error: {str(e)[:60]}")
    return ""

def save_lead_incrementally(lead, filename):
    output_path = os.path.join(OUTPUT_DIR, filename)
    file_exists = os.path.isfile(output_path)
    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=lead.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(lead)

def fetch_leads(base_queries, locations, city, limit, category, filename):
    leads = []
    seen_identifiers = set()
    output_path = os.path.join(OUTPUT_DIR, filename)

    # Resume from existing file
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    phone = row.get("phone")
                    title = row.get("title")
                    address = row.get("address")
                    dedup_key = phone if phone else (f"{title}|{address}" if address else title)
                    if dedup_key:
                        seen_identifiers.add(dedup_key)
                        leads.append(row)
            logging.info(f"Resuming {filename}: Found {len(leads)} existing leads.")
        except Exception as e:
            logging.error(f"Error reading existing file: {e}")

    for location in locations:
        if len(leads) >= limit:
            break
        for query_base in base_queries:
            if len(leads) >= limit:
                break
            query = f"{query_base} {location}"
            logging.info(f"Searching: {query}")
            params = {
                "engine": "google_maps",
                "q": query,
                "type": "search",
                "api_key": api_key,
                "start": 0
            }
            try:
                search = GoogleSearch(params)
                results = search.get_dict()
                local_results = results.get("local_results", [])
                if not local_results:
                    logging.info("No results found")
                    continue
                new_count = 0
                for result in local_results:
                    if len(leads) >= limit:
                        break
                    title = result.get("title")
                    phone = result.get("phone")
                    address = result.get("address")
                    website = result.get("website")
                    dedup_key = phone if phone else (f"{title}|{address}" if address else title)
                    if dedup_key and dedup_key not in seen_identifiers:
                        seen_identifiers.add(dedup_key)
                        email = scrape_email_from_website(website) if website else ""
                        lead = {
                            "title": title,
                            "address": address,
                            "phone": phone,
                            "website": website,
                            "email": email,
                            "rating": result.get("rating"),
                            "reviews": result.get("reviews"),
                            "type": result.get("type"),
                            "category": category,
                            "source_query": query,
                            "city": city
                        }
                        leads.append(lead)
                        save_lead_incrementally(lead, filename)
                        new_count += 1
                if new_count > 0:
                    logging.info(f"Added {new_count} | Total: {len(leads)}/{limit}")
                time.sleep(0.5)
            except Exception as e:
                logging.error(f"Error: {e}")
                time.sleep(1)
    return leads

def get_wellness_leads(city, limit=100):
    logging.info(f"===== WELLNESS CENTRES - {city.upper()} =====")
    base_queries = [
        "wellness centre",
        "wellness spa",
        "wellness clinic",
        "holistic wellness centre",
        "ayurveda wellness centre",
        "health and wellness centre",
        "wellness retreat",
        "naturopathy centre",
        "wellness studio",
        "spa and wellness",
        "yoga wellness centre",
        "physiotherapy wellness centre",
        "wellness therapy centre",
        "rejuvenation centre",
        "detox and wellness centre",
        "healing and wellness centre",
        "wellness hub",
        "mind body wellness",
        "wellness health club",
        "luxury wellness centre",
    ]
    if city == "Mumbai":
        locations = [
            city, f"{city} Andheri", f"{city} Bandra", f"{city} Juhu",
            f"{city} Powai", f"{city} Malad", f"{city} Goregaon",
            f"{city} Borivali", "Thane", "Navi Mumbai",
            f"{city} Worli", f"{city} Lower Parel", f"{city} Dadar",
            f"{city} Kandivali", f"{city} Vile Parle",
        ]
    else:
        locations = [
            city, f"{city} Koregaon Park", f"{city} Baner", f"{city} Kothrud",
            f"{city} Viman Nagar", f"{city} Aundh", f"{city} Wakad",
            f"{city} Hinjewadi", f"{city} Hadapsar", "Pimpri Chinchwad",
            f"{city} Kalyani Nagar", f"{city} Deccan", f"{city} Camp",
            f"{city} Magarpatta", f"{city} Shivaji Nagar",
        ]
    filename = f"{city.lower()}_wellness.csv"
    return fetch_leads(base_queries, locations, city, limit, "WELLNESS CENTRE", filename)

def get_gym_leads(city, limit=100):
    logging.info(f"===== GYM CENTRES - {city.upper()} =====")
    base_queries = [
        "gym",
        "fitness centre",
        "fitness gym",
        "crossfit gym",
        "strength training gym",
        "personal training gym",
        "health club",
        "fitness studio",
        "bodybuilding gym",
        "premium gym",
        "luxury gym",
        "women's gym",
        "unisex gym",
        "functional training gym",
        "gym and fitness centre",
        "workout gym",
        "fitness academy",
        "sports gym",
        "gym membership",
        "24 hour gym",
    ]
    if city == "Mumbai":
        locations = [
            city, f"{city} Andheri", f"{city} Bandra", f"{city} Powai",
            f"{city} Malad", f"{city} Goregaon", f"{city} Borivali",
            "Thane", "Navi Mumbai", f"{city} Worli",
            f"{city} Lower Parel", f"{city} Dadar", f"{city} Kandivali",
            f"{city} Vile Parle", f"{city} Kurla",
        ]
    else:
        locations = [
            city, f"{city} Koregaon Park", f"{city} Baner", f"{city} Kothrud",
            f"{city} Viman Nagar", f"{city} Aundh", f"{city} Wakad",
            f"{city} Hinjewadi", f"{city} Hadapsar", "Pimpri Chinchwad",
            f"{city} Kalyani Nagar", f"{city} Deccan", f"{city} Camp",
            f"{city} Magarpatta", f"{city} Shivaji Nagar",
        ]
    filename = f"{city.lower()}_gyms.csv"
    return fetch_leads(base_queries, locations, city, limit, "GYM CENTRE", filename)

if __name__ == "__main__":
    logging.info("WELLNESS & GYM CENTRE LEADS - 400 UNIQUE LEADS WITH EMAILS")

    # Mumbai Wellness
    get_wellness_leads("Mumbai", 100)

    # Mumbai Gyms
    get_gym_leads("Mumbai", 100)

    # Pune Wellness
    get_wellness_leads("Pune", 100)

    # Pune Gyms
    get_gym_leads("Pune", 100)

    logging.info("ALL FILES CREATED/UPDATED IN wellness_gym_leads/")
