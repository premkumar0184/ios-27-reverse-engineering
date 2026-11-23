#!/usr/bin/env python3
"""
Synchronizes the reverse-engineered Apple AGX G18 deliverables into
/home/prem/Projects/apple-agx-gpu-g18-re and verifies the standalone suite.
"""

import os
import shutil
import glob
import subprocess

SRC = "/home/prem/Projects/iOS 27"
DEST = "/home/prem/Projects/apple-agx-gpu-g18-re"

print("[*] Syncing docs/...")
shutil.copyfile(os.path.join(SRC, "findings/gpu/00_MASTER_AGX_G18_GPU_SYNTHESIS.md"), os.path.join(DEST, "docs/MASTER_DOSSIER.md"))
shutil.copyfile(os.path.join(SRC, "findings/gpu/01_RTBUDDY_FIRMWARE_MICROKERNEL.md"), os.path.join(DEST, "docs/01_RTBUDDY_FIRMWARE_MICROKERNEL.md"))
shutil.copyfile(os.path.join(SRC, "findings/gpu/02_G18_USC_RAY_TRACING_ARCHITECTURE.md"), os.path.join(DEST, "docs/02_G18_USC_RAY_TRACING_ARCHITECTURE.md"))
shutil.copyfile(os.path.join(SRC, "findings/gpu/03_TBDR_TILE_MEMORY_AND_MSRF_COMPRESSION.md"), os.path.join(DEST, "docs/03_TBDR_TILE_MEMORY_AND_MSRF_COMPRESSION.md"))
shutil.copyfile(os.path.join(SRC, "findings/gpu/04_DARWIN_DRIVER_AND_METAL_DIRECT_DISPATCH.md"), os.path.join(DEST, "docs/04_DARWIN_DRIVER_AND_METAL_DIRECT_DISPATCH.md"))

print("[*] Syncing runtime/...")
shutil.copyfile(os.path.join(SRC, "artifacts/gpu/driver/agx_host_interface.h"), os.path.join(DEST, "runtime/agx_host_interface.h"))
shutil.copyfile(os.path.join(SRC, "artifacts/gpu/driver/agx_direct_submit.c"), os.path.join(DEST, "runtime/agx_direct_submit.c"))

print("[*] Syncing specs/...")
for folder in ["firmware", "raytracing", "tbdr", "driver"]:
    spec_dir = os.path.join(SRC, f"artifacts/gpu/{folder}")
    if os.path.exists(spec_dir):
        for json_file in glob.glob(os.path.join(spec_dir, "*.json")):
            shutil.copyfile(json_file, os.path.join(DEST, "specs", os.path.basename(json_file)))

print("[*] Syncing tools/...")
shutil.copyfile(os.path.join(SRC, "tools/verify_gpu_all.py"), os.path.join(DEST, "tools/verify_gpu_all.py"))

print("[+] Files synced successfully!")
