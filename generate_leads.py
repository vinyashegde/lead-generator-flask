import os
import csv
import time
from serpapi import GoogleSearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

api_key = os.getenv("SERPAPI_KEY")

if not api_key:
    load_dotenv('.env')
    api_key = os.getenv("SERPAPI_KEY")

if not api_key:
    print("Error: SERPAPI_KEY not found in .env.local or .env")
    exit(1)

def get_hydrogen_water_leads(city, limit=100):
    """
    Get ACCURATE hydrogen water machine vendors and manufacturers.
    Using diverse, specific queries to ensure we get the RIGHT businesses.
    """
    print(f"\n{'='*60}")
    print(f"STARTING HYDROGEN WATER MACHINE LEADS FOR {city.upper()}")
    print(f"{'='*60}\n")
    
    # EXPANDED search strategy with more location specificity
    base_queries = [
        "Hydrogen water machine manufacturer",
        "Hydrogen water machine vendor",
        "Hydrogen water machine dealer",
        "Hydrogen water machine supplier",
        "Hydrogen water ionizer manufacturer",
        "Hydrogen water ionizer dealer",
        "Alkaline water ionizer manufacturer",
        "Alkaline water ionizer dealer",
        "Alkaline water machine vendor",
        "Kangen water distributor",
        "Enagic distributor",
        "Hydrogen rich water machine",
        "Hydrogen water bottle manufacturer",
        "Hydrogen water generator supplier",
        "Water ionizer manufacturer",
        "Electrolysis water machine",
    ]
    
    # For Mumbai - add specific areas
    if city == "Mumbai":
        locations = [
            city,
            f"{city} Andheri",
            f"{city} Bandra",
            f"{city} Borivali",
            "Thane",
            "Navi Mumbai",
        ]
    # For Pune - add specific areas
    else:
        locations = [
            city,
            f"{city} Kothrud",
            f"{city} Wakad",
            f"{city} Hadapsar",
            f"{city} Hinjewadi",
            "Pimpri Chinchwad",
        ]
    
    leads = []
    seen_identifiers = set()
    
    # Iterate through locations and queries
    for location in locations:
        if len(leads) >= limit:
            break
            
        for query_base in base_queries:
            if len(leads) >= limit:
                break
                
            query = f"{query_base} {location}"
            print(f"🔍 Searching: {query}")
            
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
                    print(f"   ⚠️  No results found")
                    continue
                
                new_count = 0
                for result in local_results:
                    if len(leads) >= limit:
                        break
                        
                    title = result.get("title")
                    phone = result.get("phone")
                    address = result.get("address")
                    
                    # Deduplicate by phone or title+address
                    dedup_key = phone if phone else (f"{title}|{address}" if address else title)
                    
                    if dedup_key and dedup_key not in seen_identifiers:
                        seen_identifiers.add(dedup_key)
                        
                        lead = {
                            "title": title,
                            "address": address,
                            "phone": phone,
                            "website": result.get("website"),
                            "rating": result.get("rating"),
                            "reviews": result.get("reviews"),
                            "type": result.get("type"),
                            "source_query": query,
                            "city": city
                        }
                        
                        leads.append(lead)
                        new_count += 1
                
                if new_count > 0:
                    print(f"   ✅ Added {new_count} new leads | Total: {len(leads)}/{limit}")
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                time.sleep(1)
    
    return leads

def save_to_csv(leads, filename):
    """Save leads to CSV with proper formatting"""
    if not leads:
        print(f"\n⚠️  No leads to save for {filename}")
        return
    
    keys = leads[0].keys()
    
    print(f"\n💾 Saving {len(leads)} leads to {filename}...")
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(leads)
    
    if os.path.exists(filename):
        print(f"✅ Successfully created {filename}")
    else:
        print(f"❌ Failed to create {filename}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("HYDROGEN WATER MACHINE LEAD GENERATION - ENHANCED")
    print("Target: 100 accurate leads per city")
    print("Cities: Mumbai & Pune")
    print("="*60)
    
    # Generate Mumbai leads
    mumbai_leads = get_hydrogen_water_leads("Mumbai", 100)
    save_to_csv(mumbai_leads, "h2_machine_leads_mumbai.csv")
    
    print("\n" + "-"*60 + "\n")
    
    # Generate Pune leads
    pune_leads = get_hydrogen_water_leads("Pune", 100)
    save_to_csv(pune_leads, "h2_machine_leads_pune.csv")
    
    print("\n" + "="*60)
    print("✅ ALL TASKS COMPLETED")
    print(f"Mumbai: {len(mumbai_leads)} leads")
    print(f"Pune: {len(pune_leads)} leads")
    print("="*60 + "\n")
