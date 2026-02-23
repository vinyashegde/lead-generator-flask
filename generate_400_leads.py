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

def get_manufacturer_leads(city, limit=100):
    """
    Get MANUFACTURER leads specifically - factories, production companies.
    """
    print(f"\n{'='*60}")
    print(f"🏭 MANUFACTURERS - {city.upper()}")
    print(f"{'='*60}\n")
    
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
    
    return fetch_leads(base_queries, locations, city, limit, "MANUFACTURER")

def get_vendor_leads(city, limit=100):
    """
    Get VENDOR/DEALER leads specifically - distributors, dealers, suppliers.
    """
    print(f"\n{'='*60}")
    print(f"🏪 VENDORS/DEALERS - {city.upper()}")
    print(f"{'='*60}\n")
    
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
    
    return fetch_leads(base_queries, locations, city, limit, "VENDOR")

def fetch_leads(base_queries, locations, city, limit, category):
    """
    Fetch leads using SerpAPI Google Maps search.
    """
    leads = []
    seen_identifiers = set()
    
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
                            "category": category,
                            "source_query": query,
                            "city": city
                        }
                        
                        leads.append(lead)
                        new_count += 1
                
                if new_count > 0:
                    print(f"   ✅ Added {new_count} | Total: {len(leads)}/{limit}")
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                time.sleep(1)
    
    return leads

def save_to_csv(leads, filename):
    """Save leads to CSV"""
    if not leads:
        print(f"\n⚠️  No leads to save for {filename}")
        return
    
    keys = leads[0].keys()
    
    print(f"\n💾 Saving {len(leads)} leads to {filename}...")
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(leads)
    
    print(f"✅ Created {filename}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("HYDROGEN WATER MACHINE LEADS - 400 UNIQUE LEADS")
    print("100 Manufacturers + 100 Vendors per city")
    print("="*60)
    
    # Mumbai Manufacturers
    mumbai_manufacturers = get_manufacturer_leads("Mumbai", 100)
    save_to_csv(mumbai_manufacturers, "h2_mumbai_manufacturers_new.csv")
    
    print("\n" + "-"*60)
    
    # Mumbai Vendors
    mumbai_vendors = get_vendor_leads("Mumbai", 100)
    save_to_csv(mumbai_vendors, "h2_mumbai_vendors_new.csv")
    
    print("\n" + "-"*60)
    
    # Pune Manufacturers
    pune_manufacturers = get_manufacturer_leads("Pune", 100)
    save_to_csv(pune_manufacturers, "h2_pune_manufacturers_new.csv")
    
    print("\n" + "-"*60)
    
    # Pune Vendors
    pune_vendors = get_vendor_leads("Pune", 100)
    save_to_csv(pune_vendors, "h2_pune_vendors_new.csv")
    
    print("\n" + "="*60)
    print("✅ ALL FILES CREATED")
    print(f"Mumbai Manufacturers: {len(mumbai_manufacturers)} leads")
    print(f"Mumbai Vendors: {len(mumbai_vendors)} leads")
    print(f"Pune Manufacturers: {len(pune_manufacturers)} leads")
    print(f"Pune Vendors: {len(pune_vendors)} leads")
    print(f"TOTAL: {len(mumbai_manufacturers) + len(mumbai_vendors) + len(pune_manufacturers) + len(pune_vendors)} leads")
    print("="*60 + "\n")
