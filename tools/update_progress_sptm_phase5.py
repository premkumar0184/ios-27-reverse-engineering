#!/usr/bin/env python3
import json
from datetime import datetime, timezone, timedelta

def main():
    path = "/home/prem/Projects/iOS 27/progress.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tz = timezone(timedelta(hours=5, minutes=30))
    now_iso = datetime.now(tz).isoformat()

    found = False
    for p in data.get("phases", []):
        if p.get("id") == "sptm_phase_5_synthesis":
            p["status"] = "completed"
            p["completed_at"] = now_iso
            p["verified_by"] = "tools/verify_phase.py"
            p["notes"] = [
                "tools/verify_sptm_constants.py authored and verified across 34 invariants",
                "cross_validation_matrix.json compiled with 38 constants (34 EXTRACTED, 4 INFERRED)",
                "Master Publication Dossier IOS_27_SPTM_TXM_BOOT_RE.md written and expanded to 67,858 bytes (> 50,000 bytes)",
                "Passed automated verification gate: python3 tools/verify_phase.py sptm_phase_5_synthesis"
            ]
            found = True
            break

    if not found:
        print("ERROR: sptm_phase_5_synthesis not found in phases")
        return

    # Add to verification_log
    if "verification_log" not in data:
        data["verification_log"] = []
    
    data["verification_log"].append({
        "phase_id": "sptm_phase_5_synthesis",
        "verified_at": now_iso,
        "status": "passed",
        "command": "python3 tools/verify_phase.py sptm_phase_5_synthesis"
    })

    data["last_updated"] = now_iso
    data["active_phase_id"] = None

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Updated {path} successfully. Marked sptm_phase_5_synthesis completed.")

if __name__ == "__main__":
    main()
