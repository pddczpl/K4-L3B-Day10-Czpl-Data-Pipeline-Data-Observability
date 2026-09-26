from __future__ import annotations
import json
from pathlib import Path
from typing import Any

import pandas as pd
from core.utils import write_json

def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if len(df) < 2:
        raise ValueError("Need at least 2 documents to build test set.")
    
    test_items = []
    question_id = 0
    papers = df.to_dict(orient="records")
    
    # Generate questions cycling through types
    question_types = ["summary", "authors", "date", "categories"]
    
    for i, paper in enumerate(papers):
        if len(test_items) >= 10:
            break
        
        qtype = question_types[i % len(question_types)]
        title = paper["title"]
        paper_id = paper["paper_id"]
        
        if qtype == "summary":
            question = f"What is the main contribution of '{title}'?"
            ground_truth = paper["summary"]
        elif qtype == "authors":
            question = f"Who authored '{title}'?"
            ground_truth = paper["authors_joined"]
        elif qtype == "date":
            question = f"When was '{title}' published?"
            ground_truth = paper["published"]
        elif qtype == "categories":
            question = f"What categories does '{title}' belong to?"
            ground_truth = paper["categories_joined"]
        
        test_items.append({
            "id": f"q{question_id:03d}",
            "question_type": qtype,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [paper_id],
        })
        question_id += 1
    
    # If we still need more questions, cycle again with different types
    type_idx = 0
    paper_idx = 0
    while len(test_items) < 10 and paper_idx < len(papers):
        paper = papers[paper_idx]
        qtype = question_types[(type_idx + 2) % len(question_types)]  # offset to avoid duplicates
        title = paper["title"]
        paper_id = paper["paper_id"]
        
        # Check not duplicate
        existing = {(item["question_type"], tuple(item["ground_truth_doc_ids"])) for item in test_items}
        if (qtype, (paper_id,)) not in existing:
            if qtype == "summary":
                question = f"Summarize the paper '{title}'."
                ground_truth = paper["summary"]
            elif qtype == "authors":
                question = f"List the authors of '{title}'."
                ground_truth = paper["authors_joined"]
            elif qtype == "date":
                question = f"What is the publication date of '{title}'?"
                ground_truth = paper["published"]
            elif qtype == "categories":
                question = f"What research categories is '{title}' classified under?"
                ground_truth = paper["categories_joined"]
            
            test_items.append({
                "id": f"q{question_id:03d}",
                "question_type": qtype,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            })
            question_id += 1
        
        type_idx += 1
        if type_idx % 4 == 0:
            paper_idx += 1
    
    # Trim to exactly 10
    test_items = test_items[:10]
    
    # Save
    write_json(Path(output_path), test_items)
    return test_items
