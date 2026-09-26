import re
import json
import requests
from dataclasses import dataclass, asdict
from pathlib import Path
from core.config import Settings
from core.utils import read_json, write_json

@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str

def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records = []
    items = payload.get("message", {}).get("items", [])
    for item in items:
        doi = item.get("DOI")
        title_list = item.get("title", [])
        abstract = item.get("abstract")
        
        if not doi or not title_list or not abstract:
            continue
            
        title = title_list[0]
        title = re.sub(r'<[^>]+>', '', title).strip()
        summary = re.sub(r'<[^>]+>', '', abstract).strip()
        
        authors = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            if given or family:
                authors.append(f"{given} {family}".strip())
                
        categories = item.get("subject", [])
        primary_category = categories[0] if categories else ""
        
        published = ""
        published_parts = item.get("published", {}).get("date-parts", [])
        if published_parts and published_parts[0]:
            parts = published_parts[0]
            if len(parts) == 3:
                published = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
            elif len(parts) == 2:
                published = f"{parts[0]:04d}-{parts[1]:02d}-01"
            elif len(parts) == 1:
                published = f"{parts[0]:04d}-01-01"
                
        updated = published
        if not updated:
            created = item.get("created", {}).get("date-time", "")
            updated = created[:10] if created else ""
            if not published:
                published = updated
                
        url = item.get("URL", "")
        comment = f"Crossref record {doi}"
        
        records.append(PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=url,
            pdf_url=url,
            comment=comment
        ))
        
    return records

def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results
    }
    
    payload = None
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        write_json(settings.paths.raw_api_response, payload)
    except Exception as e:
        print(f"API fetch failed, falling back to local snapshot: {e}")
        try:
            payload = read_json(settings.paths.raw_api_response)
        except Exception as inner_e:
            print(f"Failed to read local snapshot: {inner_e}")
            return []
            
    records = parse_crossref_payload(payload)
    records_dict = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_dict)
    
    return records

def load_raw_records(path: Path) -> list[PaperRecord]:
    records_dict = read_json(path)
    return [PaperRecord(**r) for r in records_dict]
