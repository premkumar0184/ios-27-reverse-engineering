#!/usr/bin/env python3
"""
Populates and synchronizes /home/prem/Projects/apple-audio-subsystem-re
from /home/prem/Projects/iOS 27.
"""

import os
import shutil
import glob

SRC = "/home/prem/Projects/iOS 27"
DEST = "/home/prem/Projects/apple-audio-subsystem-re"

os.makedirs(os.path.join(DEST, "docs"), exist_ok=True)
os.makedirs(os.path.join(DEST, "runtime"), exist_ok=True)
os.makedirs(os.path.join(DEST, "specs"), exist_ok=True)
os.makedirs(os.path.join(DEST, "tools"), exist_ok=True)

print("[*] Copying docs/...")
shutil.copyfile(os.path.join(SRC, "findings/audio/00_MASTER_AUDIO_SUBSYSTEM_SYNTHESIS.md"), os.path.join(DEST, "docs/MASTER_DOSSIER.md"))
shutil.copyfile(os.path.join(SRC, "findings/audio/01_SMARTIO_ASC7_RTKIT_MICROKERNEL.md"), os.path.join(DEST, "docs/01_SMARTIO_ASC7_RTKIT_MICROKERNEL.md"))
shutil.copyfile(os.path.join(SRC, "findings/audio/02_ADMAC_EVOLUTION_AUDIO_DMA_ARCHITECTURE.md"), os.path.join(DEST, "docs/02_ADMAC_EVOLUTION_AUDIO_DMA_ARCHITECTURE.md"))
shutil.copyfile(os.path.join(SRC, "findings/audio/03_CIRRUS_LOGIC_CODECS_AND_BOOT_CHIME.md"), os.path.join(DEST, "docs/03_CIRRUS_LOGIC_CODECS_AND_BOOT_CHIME.md"))
shutil.copyfile(os.path.join(SRC, "findings/audio/04_AOP_AUDIO_VOICETRIGGER_AND_EXCLAVE_PRIVACY.md"), os.path.join(DEST, "docs/04_AOP_AUDIO_VOICETRIGGER_AND_EXCLAVE_PRIVACY.md"))

print("[*] Copying runtime/...")
shutil.copyfile(os.path.join(SRC, "artifacts/audio/runtime/audio_host_interface.h"), os.path.join(DEST, "runtime/audio_host_interface.h"))
shutil.copyfile(os.path.join(SRC, "artifacts/audio/runtime/audio_direct_submit.c"), os.path.join(DEST, "runtime/audio_direct_submit.c"))

print("[*] Copying specs/...")
for folder in ["smartio", "dma", "codec", "privacy"]:
    spec_dir = os.path.join(SRC, f"artifacts/audio/{folder}")
    if os.path.exists(spec_dir):
        for json_file in glob.glob(os.path.join(spec_dir, "*.json")):
            shutil.copyfile(json_file, os.path.join(DEST, "specs", os.path.basename(json_file)))

print("[*] Creating standalone .gitignore...")
with open(os.path.join(DEST, ".gitignore"), "w") as f:
    f.write("""__pycache__/
*.py[cod]
*.o
*.a
*.so
*.dylib
*.out
*.raw
*.wav
*.macho
audio_direct_submit
.DS_Store
""")

print("[+] Synchronized files successfully to", DEST)
