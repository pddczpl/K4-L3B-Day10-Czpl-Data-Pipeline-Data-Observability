from __future__ import annotations
from datetime import datetime
from dataclasses import asdict
import re
import pandas as pd
from ingestion.crossref import PaperRecord

def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    records_dict = [asdict(r) for r in records]
    df = pd.DataFrame(records_dict)
    
    if df.empty:
        return df
        
    df['title'] = df['title'].apply(lambda x: re.sub(r'<[^>]+>', '', str(x)).strip())
    df['title'] = df['title'].apply(lambda x: re.sub(r'\s+', ' ', x).strip())
    
    df['summary'] = df['summary'].apply(lambda x: re.sub(r'<[^>]+>', '', str(x)).strip())
    df['summary'] = df['summary'].apply(lambda x: re.sub(r'\s+', ' ', x).strip())
    
    published_dt = pd.to_datetime(df['published'], errors='coerce')
    if run_date.tzinfo is not None:
        run_date = run_date.replace(tzinfo=None)
    
    df['age_days'] = (run_date - published_dt).dt.days
    
    df['authors_joined'] = df['authors'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    df['categories_joined'] = df['categories'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    df['summary_chars'] = df['summary'].str.len()
    
    df['text_for_embedding'] = df.apply(
        lambda row: f"Title: {row['title']}\nAuthors: {row['authors_joined']}\nPublished: {row['published']}\nCategories: {row['categories_joined']}\nSummary: {row['summary']}",
        axis=1
    )
    
    df = df.drop_duplicates(subset=['paper_id'], keep='first')
    df = df[(df['summary'].str.len() > 0) & (df['title'].str.len() > 0)]
    df = df.sort_values(by='published', ascending=False).reset_index(drop=True)
    
    return df
