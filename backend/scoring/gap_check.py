from typing import Any, Dict, List, Optional

import pandas as pd


def analyze_ais_reporting_gaps(
    trajectory: List[Dict[str, Any]],
    suspicious_gap_hours: float = 6.0,
    report_gap_hours: float = 1.0,
) -> Dict[str, Any]:
    """
    Detect AIS reporting outages by inspecting timestamp deltas between points.
    Returns summary statistics and suspicious gap windows.
    """
    result: Dict[str, Any] = {
        "available": False,
        "timestamp_field": None,
        "total_points": len(trajectory),
        "points_with_timestamp": 0,
        "max_gap_hours": 0.0,
        "avg_gap_hours": 0.0,
        "gap_count_over_1h": 0,
        "suspicious": False,
        "suspicious_threshold_hours": suspicious_gap_hours,
        "suspicious_gaps": [],
    }

    if len(trajectory) < 2:
        return result

    df_seq = pd.DataFrame(trajectory)
    ts_candidates = ["TIMESTAMP", "timestamp", "ts", "time", "datetime"]
    ts_col: Optional[str] = next((c for c in ts_candidates if c in df_seq.columns), None)
    if ts_col is None:
        return result

    parsed = pd.to_datetime(df_seq[ts_col], errors="coerce", utc=True)
    valid = parsed.notna()
    if valid.sum() < 2:
        result["timestamp_field"] = ts_col
        result["points_with_timestamp"] = int(valid.sum())
        return result

    work = pd.DataFrame({"timestamp": parsed[valid]}).sort_values("timestamp").reset_index(drop=True)
    gap_hours = (work["timestamp"].diff().dt.total_seconds() / 3600.0).fillna(0.0)

    suspicious_rows = []
    for idx in range(1, len(work)):
        hours = float(gap_hours.iloc[idx])
        if hours >= suspicious_gap_hours:
            suspicious_rows.append({
                "start": work["timestamp"].iloc[idx - 1].isoformat(),
                "end": work["timestamp"].iloc[idx].isoformat(),
                "gap_hours": round(hours, 2),
            })

    result.update({
        "available": True,
        "timestamp_field": ts_col,
        "points_with_timestamp": int(len(work)),
        "max_gap_hours": round(float(gap_hours.max()), 2),
        "avg_gap_hours": round(float(gap_hours.iloc[1:].mean()) if len(work) > 1 else 0.0, 2),
        "gap_count_over_1h": int((gap_hours >= report_gap_hours).sum()),
        "suspicious": len(suspicious_rows) > 0,
        "suspicious_gaps": suspicious_rows[:5],
    })
    return result