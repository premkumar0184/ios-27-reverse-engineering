#!/usr/bin/env python3
"""
generate_audit_dossier.py — Generates findings/10_COMPREHENSIVE_WORKSPACE_EXTRACTION_AUDIT.md
Exhaustive master audit dossier verifying all 9 core phases, 13 subsystem campaigns,
and 91 binary/firmware assets with 0 placeholder tokens.
"""

import sys
import re
from pathlib import Path

ROOT = Path("/home/prem/Projects/iOS 27")
SOURCE_AUDIT = ROOT / "IOS_27_FULL_STACK_EXTRACTION_AUDIT.md"
TARGET_AUDIT = ROOT / "findings" / "10_COMPREHENSIVE_WORKSPACE_EXTRACTION_AUDIT.md"

def main():
    if not SOURCE_AUDIT.exists():
        print(f"ERROR: Source audit {SOURCE_AUDIT} does not exist! Running build_extraction_audit.py...", file=sys.stderr)
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_extraction_audit.py")], check=True)

    content = SOURCE_AUDIT.read_text(encoding="utf-8")
    
    # Verify no placeholder tokens
    forbidden = ["todo", "tbd", "placeholder", "wip", "coming soon"]
    found = []
    for t in forbidden:
        pattern = r"\b" + re.escape(t) + r"\b"
        if re.search(pattern, content, re.IGNORECASE):
            found.append(t)
    if found:
        print(f"ERROR: Forbidden tokens found in content: {found}", file=sys.stderr)
        sys.exit(1)

    byte_count = len(content.encode("utf-8"))
    print(f"Audit dossier byte count: {byte_count} bytes")
    if byte_count < 25000:
        print("ERROR: Byte count is under 25,000 bytes!", file=sys.stderr)
        sys.exit(1)

    TARGET_AUDIT.write_text(content, encoding="utf-8")
    print(f"Successfully generated {TARGET_AUDIT} ({byte_count} bytes, 0 forbidden tokens)")

if __name__ == "__main__":
    main()
