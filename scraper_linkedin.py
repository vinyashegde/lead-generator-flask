import os
import re
import time
import datetime
import json
from serpapi import GoogleSearch
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def convert_linkedin_leads_to_styled_xlsx(leads, output_xlsx_path):
    """Converts LinkedIn leads into a LinkedIn-branded styled Excel workbook."""
    if not leads:
        return
    
    wb = Workbook()
    ws = wb.active
    ws.title = "LinkedIn Leads"
    
    fieldnames = list(leads[0].keys())
    
    # ── Style definitions (LinkedIn Blue Theme) ──
    header_font = Font(name='Calibri', bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='0077B5', end_color='0077B5', fill_type='solid') # LinkedIn Blue
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    cell_font = Font(name='Calibri', size=10)
    cell_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
    
    row_even_fill = PatternFill(start_color='F3F6F8', end_color='F3F6F8', fill_type='solid') # Very light LinkedIn gray/blue
    
    # Highlight colors
    name_fill = PatternFill(start_color='D9EBF7', end_color='D9EBF7', fill_type='solid')
    link_font = Font(name='Calibri', size=10, color='0077B5', underline='single')
    
    thin_border = Border(
        left=Side(style='thin', color='D9E1E7'),
        right=Side(style='thin', color='D9E1E7'),
        top=Side(style='thin', color='D9E1E7'),
        bottom=Side(style='thin', color='D9E1E7')
    )
    
    # ── Write header row ──
    display_names = {
        'name': 'Full Name',
        'title': 'Job Title',
        'location': 'Location',
        'link': 'LinkedIn Profile',
        'snippet': 'Profile Summary',
        'source_query': 'Search Query'
    }
    
    for col_idx, key in enumerate(fieldnames, 1):
        cell = ws.cell(row=1, column=col_idx, value=display_names.get(key, key.replace('_', ' ').title()))
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
    
    ws.freeze_panes = 'A2'
    
    # ── Write data rows ──
    for row_idx, lead in enumerate(leads, 2):
        is_even = row_idx % 2 == 0
        for col_idx, key in enumerate(fieldnames, 1):
            value = lead.get(key, '')
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = cell_font
            cell.alignment = cell_align
            cell.border = thin_border
            
            if is_even:
                cell.fill = row_even_fill
            
            if key == 'name':
                cell.fill = name_fill
                cell.font = Font(name='Calibri', size=10, bold=True)
            elif key == 'link':
                cell.font = link_font
    
    # ── Auto-size columns ──
    col_widths = {
        'name': 25, 'title': 35, 'location': 25, 'link': 45, 'snippet': 50, 'source_query': 30
    }
    for col_idx, key in enumerate(fieldnames, 1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = col_widths.get(key, 20)
    
    # Row heights
    ws.row_dimensions[1].height = 25
    for row_idx in range(2, len(leads) + 2):
        ws.row_dimensions[row_idx].height = 30
    
    wb.save(output_xlsx_path)

def generate_linkedin_leads(keyword, location, limit, api_key):
    """
    Fetch LinkedIn leads using Google X-Ray search via SerpAPI.
    Yields events for SSE streaming.
    """
    leads = []
    seen_links = set()
    
    os.makedirs('generated_leads', exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = re.sub(r'[^a-zA-Z0-9]', '_', keyword)
    safe_location = re.sub(r'[^a-zA-Z0-9]', '_', location)
    xlsx_filename = f"linkedin_leads_{safe_keyword}_{safe_location}_{timestamp}.xlsx"
    xlsx_output_path = os.path.join("generated_leads", xlsx_filename)
    
    yield {"type": "log", "message": f"🚀 Starting LinkedIn X-Ray search for '{keyword}' in '{location}'."}
    
    # X-Ray Query construction
    query = f'site:linkedin.com/in/ "{keyword}" "{location}"'
    
    start = 0
    while len(leads) < limit:
        yield {"type": "log", "message": f"Scanning profiles (page {int(start/10) + 1})..."}
        
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "start": start,
            "num": 10
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            organic_results = results.get("organic_results", [])
            
            if not organic_results:
                yield {"type": "log", "message": "No more LinkedIn profiles found."}
                break
            
            for result in organic_results:
                if len(leads) >= limit:
                    break
                    
                link = result.get("link", "")
                if "/in/" not in link or link in seen_links:
                    continue
                
                seen_links.add(link)
                
                # Parse title (usually "Name - Job Title - Company | LinkedIn")
                raw_title = result.get("title", "Unknown")
                name = raw_title.split('-')[0].split('|')[0].strip()
                
                # Try to extract title from the raw_title or snippet
                job_title = "N/A"
                if '-' in raw_title:
                    parts = raw_title.split('-')
                    if len(parts) > 1:
                        job_title = parts[1].split('|')[0].strip()
                
                snippet = result.get("snippet", "")
                
                lead = {
                    "name": name,
                    "title": job_title,
                    "location": location,
                    "link": link,
                    "snippet": snippet,
                    "source_query": query
                }
                
                leads.append(lead)
                
                yield {
                    "type": "progress",
                    "count": len(leads),
                    "total": limit,
                    "latest_lead": name
                }
            
            start += 10
            if start > 100: # Google doesn't like deep scraping
                yield {"type": "log", "message": "Reached scan limit for this query."}
                break
                
            time.sleep(1)
            
        except Exception as e:
            yield {"type": "error", "message": f"LinkedIn Search Error: {str(e)}"}
            return
            
    if leads:
        yield {"type": "log", "message": "📊 Formatting LinkedIn Lead Report..."}
        try:
            convert_linkedin_leads_to_styled_xlsx(leads, xlsx_output_path)
        except Exception as e:
            yield {"type": "error", "message": f"Excel generation failed: {str(e)}"}
            return
            
    yield {"type": "log", "message": f"✨ Success! Compiled {len(leads)} LinkedIn leads."}
    yield {
        "type": "done",
        "filename": xlsx_filename,
        "path": xlsx_output_path,
        "count": len(leads)
    }
