from __future__ import annotations
import random
import pandas as pd
from core.utils import write_json

def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    random.seed(42)
    corrupted = df.copy()
    logs = []
    
    if corrupted.empty:
        write_json(output_log_path, logs)
        return corrupted
        
    # 1. Drop latest records
    corrupted = corrupted.sort_values(by='published', ascending=False)
    drop_count = int(len(corrupted) * 0.2)
    if drop_count > 0:
        corrupted = corrupted.iloc[drop_count:]
        logs.append({"type": "drop_latest", "count": drop_count})
        
    # 2. Blank summary
    indices = random.sample(list(corrupted.index), min(3, len(corrupted)))
    affected_ids = corrupted.loc[indices, 'paper_id'].tolist()
    corrupted.loc[indices, 'summary'] = ""
    logs.append({"type": "blank_summary", "affected_ids": affected_ids})
    
    # 3. Inject noise
    indices = random.sample(list(corrupted.index), min(3, len(corrupted)))
    affected_ids = corrupted.loc[indices, 'paper_id'].tolist()
    corrupted.loc[indices, 'summary'] = "@#$%^&*NOISE" + corrupted.loc[indices, 'summary'].astype(str)
    logs.append({"type": "inject_noise", "affected_ids": affected_ids})
    
    # 4. Truncate title
    indices = random.sample(list(corrupted.index), min(3, len(corrupted)))
    affected_ids = corrupted.loc[indices, 'paper_id'].tolist()
    corrupted.loc[indices, 'title'] = corrupted.loc[indices, 'title'].str[:5]
    logs.append({"type": "truncate_title", "affected_ids": affected_ids})
    
    # 5. Stale date
    indices = random.sample(list(corrupted.index), min(3, len(corrupted)))
    affected_ids = corrupted.loc[indices, 'paper_id'].tolist()
    corrupted.loc[indices, 'published'] = "2020-01-01"
    logs.append({"type": "stale_date", "affected_ids": affected_ids})
    
    # 6. Duplicate rows
    dup_rows = corrupted.head(3)
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    logs.append({"type": "duplicate_rows", "count": len(dup_rows)})
    
    # Recalculate text_for_embedding and summary_chars
    corrupted['summary_chars'] = corrupted['summary'].str.len()
    corrupted['text_for_embedding'] = corrupted.apply(
        lambda row: f"Title: {row['title']}\nAuthors: {row['authors_joined']}\nPublished: {row['published']}\nCategories: {row['categories_joined']}\nSummary: {row['summary']}",
        axis=1
    )
    
    write_json(output_log_path, logs)
    corrupted = corrupted.reset_index(drop=True)
    return corrupted
