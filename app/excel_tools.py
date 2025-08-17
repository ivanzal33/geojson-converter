import pandas as pd
from typing import List, Dict, Any, Tuple

def extract_combined_headers(file_path, sheet_name: int | str = 0, n_header_rows: int = 3) -> List[str]:
    header_df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=n_header_rows, header=None)
    combined = header_df.fillna("").astype(str).agg(" ".join, axis=0)
    return combined.str.strip().str.replace(r"\s+", " ", regex=True).tolist()

def diff_headers(actual: List[str], reference: List[str]) -> Dict[str, Any]:
    max_len = max(len(actual), len(reference))
    rows: List[Dict[str, Any]] = []
    ok = True

    for i in range(max_len):
        a = actual[i] if i < len(actual) else None
        r = reference[i] if i < len(reference) else None
        status = "match"
        if a != r:
            ok = False
            if a is None: status = "missing"       # отсутствует столбец
            elif r is None: status = "extra"       # лишний столбец
            else: status = "mismatch"              # не то имя/порядок
        rows.append({"index": i+1, "expected": r, "actual": a, "status": status})

    missing = [row["index"] for row in rows if row["status"] == "missing"]
    extra   = [row["index"] for row in rows if row["status"] == "extra"]
    mism    = [row["index"] for row in rows if row["status"] == "mismatch"]

    return {
        "ok": ok,
        "rows": rows,
        "missing_idx": missing,
        "extra_idx": extra,
        "mismatch_idx": mism,
        "expected_len": len(reference),
        "actual_len": len(actual),
        "expected": reference,
        "actual": actual
    }
