import csv

def classify_as_manufacturer(lead):
    """
    Determine if a lead is a manufacturer or vendor/dealer.
    Returns True if manufacturer, False if vendor/dealer.
    """
    business_type = (lead.get('type') or '').lower()
    source_query = (lead.get('source_query') or '').lower()
    
    # Strong manufacturer indicators
    manufacturer_keywords = [
        'manufacturer',
        'manufacturing',
        'factory',
        'industrial equipment',
        'chemical manufacturer',
        'machining manufacturer',
    ]
    
    # Vendor/Dealer/Distributor indicators
    vendor_keywords = [
        'vendor',
        'dealer',
        'distributor',
        'supplier',
        'seller',
        'reseller',
        'showroom',
        'retail',
    ]
    
    # Check business type first (more reliable)
    for keyword in manufacturer_keywords:
        if keyword in business_type:
            return True
    
    for keyword in vendor_keywords:
        if keyword in business_type:
            return False
    
    # If business type is ambiguous, check source query
    for keyword in manufacturer_keywords:
        if keyword in source_query:
            return True
    
    for keyword in vendor_keywords:
        if keyword in source_query:
            return False
    
    # Default: if unclear, classify based on source query presence of "manufacturer"
    if 'manufacturer' in source_query:
        return True
    else:
        return False

def split_leads_by_type(input_file, output_manufacturers, output_vendors):
    """
    Read CSV and split into manufacturer and vendor files.
    """
    manufacturers = []
    vendors = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if classify_as_manufacturer(row):
                manufacturers.append(row)
            else:
                vendors.append(row)
    
    # Write manufacturers
    if manufacturers:
        with open(output_manufacturers, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=manufacturers[0].keys())
            writer.writeheader()
            writer.writerows(manufacturers)
        print(f"✅ Created {output_manufacturers} with {len(manufacturers)} manufacturers")
    
    # Write vendors
    if vendors:
        with open(output_vendors, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=vendors[0].keys())
            writer.writeheader()
            writer.writerows(vendors)
        print(f"✅ Created {output_vendors} with {len(vendors)} vendors/dealers")
    
    return len(manufacturers), len(vendors)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SPLITTING LEADS BY TYPE: MANUFACTURERS vs VENDORS")
    print("="*60 + "\n")
    
    # Process Mumbai
    print("📍 Processing MUMBAI leads...")
    m_manufacturers, m_vendors = split_leads_by_type(
        'h2_machine_leads_mumbai.csv',
        'h2_mumbai_manufacturers.csv',
        'h2_mumbai_vendors.csv'
    )
    
    print(f"\nMumbai Summary:")
    print(f"  - Manufacturers: {m_manufacturers}")
    print(f"  - Vendors/Dealers: {m_vendors}")
    print(f"  - Total: {m_manufacturers + m_vendors}")
    
    print("\n" + "-"*60 + "\n")
    
    # Process Pune
    print("📍 Processing PUNE leads...")
    p_manufacturers, p_vendors = split_leads_by_type(
        'h2_machine_leads_pune.csv',
        'h2_pune_manufacturers.csv',
        'h2_pune_vendors.csv'
    )
    
    print(f"\nPune Summary:")
    print(f"  - Manufacturers: {p_manufacturers}")
    print(f"  - Vendors/Dealers: {p_vendors}")
    print(f"  - Total: {p_manufacturers + p_vendors}")
    
    print("\n" + "="*60)
    print("✅ ALL FILES CREATED SUCCESSFULLY")
    print("="*60 + "\n")
    
    print("📁 Final Files:")
    print("  Mumbai:")
    print("    - h2_mumbai_manufacturers.csv")
    print("    - h2_mumbai_vendors.csv")
    print("  Pune:")
    print("    - h2_pune_manufacturers.csv")
    print("    - h2_pune_vendors.csv")
