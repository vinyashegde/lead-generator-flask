import os
import csv
import time
import re
import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
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
        logging.FileHandler("execution.log", encoding='utf-8'),
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
    print("Error: SERPAPI_KEY not found in .env.local or .env")
    exit(1)

def extract_emails_from_text(text):
    """Extract emails from text using regex"""
    # Improved regex to avoid some junk
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = set(re.findall(email_pattern, text))
    # Filter out invalid emails that might be image filenames or too long
    valid_emails = {e for e in emails if len(e) < 50 and not any(ext in e.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'])}
    return valid_emails

def scrape_email_from_website(url):
    """Scrape emails from a website"""
    if not url:
        return ""
    
    try:
        # Add http if missing
        if not url.startswith('http'):
            url = 'http://' + url
            
        logging.info(f"Scraping emails from {url}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Use separator to avoid concatenated text like "info@kykindia.comHomeAbout"
            text = soup.get_text(separator=' ')
            emails = extract_emails_from_text(text)
            
            # Also check contact page if found
            if not emails:
                contact_links = soup.find_all('a', href=re.compile(r'contact', re.I))
                for link in contact_links:
                    contact_url = link.get('href')
                    if contact_url:
                        if not contact_url.startswith('http'):
                            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                            contact_url = base_url + contact_url if contact_url.startswith('/') else base_url + '/' + contact_url
                        
                        try:
                            contact_response = requests.get(contact_url, headers=headers, timeout=5)
                            if contact_response.status_code == 200:
                                contact_soup = BeautifulSoup(contact_response.text, 'html.parser')
                                emails.update(extract_emails_from_text(contact_soup.get_text(separator=' ')))
                        except:
                            pass
            
            filtered_emails = {e for e in emails if not any(x in e.lower() for x in ['example.com', 'yourdomain', 'sentry.io', 'wixpress.com'])}
            
            if filtered_emails:
                result = ", ".join(filtered_emails)
                logging.info(f"Found: {result}")
                return result
    except Exception as e:
        logging.error(f"Scrape error: {str(e)[:50]}")
        pass
        
    return ""

def save_lead_incrementally(lead, filename):
    """Append a single lead to CSV"""
    output_path = os.path.join("hydrogen_leads", filename)
    file_exists = os.path.isfile(output_path)
    
    with open(output_path, 'a', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=lead.keys())
        if not file_exists:
            dict_writer.writeheader()
        dict_writer.writerow(lead)

def fetch_leads(base_queries, locations, city, limit, category, filename):
    """
    Fetch leads using SerpAPI Google Maps search and save incrementally.
    """
    leads = []
    seen_identifiers = set()
    output_path = os.path.join("hydrogen_leads", filename)
    
    # Check if file exists and load seen identifiers to avoid duplicates on restart
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
                        leads.append(row) # Keep count correct
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
                    logging.info(f"No results found")
                    continue
                
                new_count = 0
                for result in local_results:
                    if len(leads) >= limit:
                        break
                        
                    title = result.get("title")
                    phone = result.get("phone")
                    address = result.get("address")
                    website = result.get("website")
                    
                    # Deduplicate by phone or title+address
                    dedup_key = phone if phone else (f"{title}|{address}" if address else title)
                    
                    if dedup_key and dedup_key not in seen_identifiers:
                        seen_identifiers.add(dedup_key)
                        
                        # Scrape email if website exists
                        email = ""
                        if website:
                            email = scrape_email_from_website(website)
                        
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

def get_manufacturer_leads(city, limit=100):
    """
    Get MANUFACTURER leads specifically - factories, production companies.
    """
    logging.info(f"MANUFACTURERS - {city.upper()}")
    
    # Manufacturer-specific queries
    base_queries = [
        "Hydrogen water machine manufacturer",
        "Alkaline water ionizer manufacturer",
        "Water ionizer manufacturer",
        "Hydrogen water bottle manufacturer",
        "Water purification equipment manufacturer",
        "Electrolysis water machine manufacturer",
        "Hydrogen generator manufacturer",
        "Industrial water equipment manufacturer",
        "Water treatment equipment manufacturer",
        "Alkaline water machine factory",
    ]
    
    # Location variations
    if city == "Mumbai":
        locations = [city, f"{city} Andheri", f"{city} Borivali", "Thane", "Navi Mumbai", f"{city} Goregaon"]
    else:
        locations = [city, f"{city} Kothrud", f"{city} Wakad", f"{city} Hadapsar", "Pimpri Chinchwad", f"{city} Hinjewadi"]
    
    filename = "mumbai_manufacturers.csv" if city == "Mumbai" else "pune_manufacturers.csv"
    return fetch_leads(base_queries, locations, city, limit, "MANUFACTURER", filename)

def get_vendor_leads(city, limit=100):
    """
    Get VENDOR/DEALER leads specifically - distributors, dealers, suppliers.
    """
    logging.info(f"VENDORS/DEALERS - {city.upper()}")
    
    # Vendor/dealer-specific queries
    base_queries = [
        "Hydrogen water machine dealer",
        "Hydrogen water machine vendor",
        "Hydrogen water machine supplier",
        "Kangen water distributor",
        "Enagic distributor",
        "Alkaline water ionizer dealer",
        "Hydrogen water ionizer dealer",
        "Water ionizer supplier",
        "Alkaline water machine dealer",
        "Hydrogen water equipment supplier",
        "Kangen water seller",
        "Water purifier dealer",
    ]
    
    # Location variations
    if city == "Mumbai":
        locations = [city, f"{city} Bandra", f"{city} Malad", f"{city} Powai", f"{city} Kurla", "Navi Mumbai", f"{city} Kandivali"]
    else:
        locations = [city, f"{city} Baner", f"{city} Viman Nagar", f"{city} Aundh", f"{city} Koregaon Park", "Pimpri Chinchwad", f"{city} Magarpatta"]
        
    filename = "mumbai_vendors.csv" if city == "Mumbai" else "pune_vendors.csv"
    return fetch_leads(base_queries, locations, city, limit, "VENDOR", filename)

if __name__ == "__main__":
    logging.info("HYDROGEN WATER MACHINE LEADS - 400 UNIQUE LEADS WITH EMAILS")
    
    # Mumbai Manufacturers
    get_manufacturer_leads("Mumbai", 100)
    
    # Mumbai Vendors
    get_vendor_leads("Mumbai", 100)
    
    # Pune Manufacturers
    get_manufacturer_leads("Pune", 100)
    
    # Pune Vendors
    get_vendor_leads("Pune", 100)
    
    logging.info("ALL FILES CREATED/UPDATED IN hydrogen_leads/")
