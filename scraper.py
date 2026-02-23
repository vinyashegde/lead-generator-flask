import os
import csv
import time
import re
import requests
import json
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from urllib.parse import urlparse
import datetime

def extract_emails_from_text(text):
    """Extract emails from text using regex"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = set(re.findall(email_pattern, text))
    # Filter out invalid emails that might be image filenames or too long
    valid_emails = {e for e in emails if len(e) < 50 and not any(ext in e.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'])}
    return valid_emails

def scrape_email_from_website(url, emit_log=None):
    """Scrape emails from a website"""
    if not url:
        return ""
    
    try:
        # Add http if missing
        if not url.startswith('http'):
            url = 'http://' + url
            
        if emit_log:
            emit_log(f"Scraping emails from {url}...")
            
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
            
            # check mailto links
            mailto_links = soup.select('a[href^=mailto]')
            for link in mailto_links:
                href = link.get('href', '')
                email = href.replace('mailto:', '').split('?')[0].strip()
                if email:
                    emails.add(email)

            filtered_emails = {e for e in emails if not any(x in e.lower() for x in ['example.com', 'yourdomain', 'sentry.io', 'wixpress.com'])}
            
            if filtered_emails:
                result = ", ".join(filtered_emails)
                if emit_log:
                    emit_log(f"Found emails: {result}")
                return result
    except Exception as e:
        if emit_log:
            emit_log(f"Scrape error for {url}: {str(e)[:50]}")
        pass
        
    return ""

def generate_leads(keyword, location, limit, api_key, require_email=False, require_website=False):
    """
    Fetch leads using SerpAPI Google Maps search.
    Yields progress dictionaries for Server-Sent Events (SSE).
    """
    leads = []
    seen_identifiers = set()
    
    # Setup directory and filename
    os.makedirs('generated_leads', exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = re.sub(r'[^a-zA-Z0-9]', '_', keyword)
    safe_location = re.sub(r'[^a-zA-Z0-9]', '_', location)
    filename = f"leads_{safe_keyword}_{safe_location}_{timestamp}.csv"
    output_path = os.path.join("generated_leads", filename)
    
    yield {"type": "log", "message": f"Starting lead generation for '{keyword}' in '{location}'. Target: {limit} leads."}
    
    query = f"{keyword} {location}"
    start = 0
    total_found_approx = 100 # Default to something > 0 to start loop
    
    while len(leads) < limit:
        yield {"type": "log", "message": f"Fetching results from SerpAPI (start={start})..."}
        params = {
            "engine": "google_maps",
            "q": query,
            "type": "search",
            "api_key": api_key,
            "start": start
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            local_results = results.get("local_results", [])
            
            if not local_results:
                yield {"type": "log", "message": "No more results found from Google Maps."}
                break
            
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
                    
                    email = ""
                    if website:
                        # Modified scrape_email_from_website to not take a callback to avoid complexity here.
                        # We'll just print or log inside there, or not log at all, or just yield before/after.
                        yield {"type": "log", "message": f"Scraping emails from {website}..."}
                        email = scrape_email_from_website(website)
                        if email:
                            yield {"type": "log", "message": f"Found emails: {email}"}
                    
                    if require_website and not website:
                        yield {"type": "log", "message": f"Skipping {title} (no website)"}
                        continue
                        
                    if require_email and not email:
                        yield {"type": "log", "message": f"Skipping {title} (no email)"}
                        continue
                    
                    lead = {
                        "title": title,
                        "address": address,
                        "phone": phone,
                        "website": website,
                        "email": email,
                        "rating": result.get("rating"),
                        "reviews": result.get("reviews"),
                        "type": result.get("type"),
                        "source_query": query,
                    }
                    
                    leads.append(lead)
                    
                    # Save to CSV incrementally
                    file_exists = os.path.isfile(output_path)
                    with open(output_path, 'a', newline='', encoding='utf-8') as output_file:
                        dict_writer = csv.DictWriter(output_file, fieldnames=lead.keys())
                        if not file_exists:
                            dict_writer.writeheader()
                        dict_writer.writerow(lead)
                    
                    # Emit progress update
                    yield {
                        "type": "progress",
                        "count": len(leads),
                        "total": limit,
                        "latest_lead": title
                    }
            
            start += 20 # Google maps pagination typically goes by 20
            time.sleep(1) # Be nice to SerpAPI
            
        except Exception as e:
            yield {"type": "error", "message": f"Google Maps/SerpAPI Error: {str(e)}"}
            return
            
    yield {"type": "log", "message": f"Finished. Generated {len(leads)} leads. Saved to {filename}"}
    
    yield {
        "type": "done",
        "filename": filename,
        "path": output_path,
        "count": len(leads)
    }
