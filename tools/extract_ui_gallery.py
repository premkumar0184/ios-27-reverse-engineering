#!/usr/bin/env python3
"""
tools/extract_ui_gallery.py - Extraction, CgBI normalization, and cataloging of iOS UI visual assets.

Extracts factory wallpapers (HEIC, JPEG, PNG) and core application icons from decrypted rootfs APFS DMG.
Decodes Apple CgBI compressed PNGs into standard W3C PNGs.
Converts HEIC images to JPEG previews for cross-platform rendering and artifact embedding.
"""

import os
import sys
import json
import shutil
import struct
import zlib
import subprocess
from PIL import Image

DMG_PATH = "artifacts/crypto/141-08876-216_rootfs.dmg"
WALLPAPERS_DIR = "artifacts/ui/sample_wallpapers"
ICONS_DIR = "artifacts/ui/sample_icons"
ARTIFACT_DIR = "/home/prem/.config/AntigravityManager/profiles/0a687723-2b9e-410c-849a-39cdb95fe290/home/.gemini/antigravity/brain/96d42e85-0010-4518-bdd1-4faf512d9084"
ARTIFACT_ASSETS_DIR = os.path.join(ARTIFACT_DIR, "gallery_assets")

WALLPAPERS_MANIFEST = [
    {
        "id": "ios17_bg_light",
        "title": "iOS Factory Default Wallpaper (Light)",
        "category": "Factory Default",
        "rootfs_path": "Library/Wallpaper/Collections/iOS_17~iphone.wallpaperCollection/Wallpapers/7565.iOS_17-440w-956h@3x~iphone.wallpaper/7565.iOS_17_Background-440w-956h@3x~iphone.ca/assets/Background Light.HEIC",
        "out_filename": "ios17_background_light.heic",
        "preview_filename": "ios17_background_light.jpg"
    },
    {
        "id": "ios17_bg_dark",
        "title": "iOS Factory Default Wallpaper (Dark)",
        "category": "Factory Default",
        "rootfs_path": "Library/Wallpaper/Collections/iOS_17~iphone.wallpaperCollection/Wallpapers/7565.iOS_17-440w-956h@3x~iphone.wallpaper/7565.iOS_17_Background-440w-956h@3x~iphone.ca/assets/Background Dark.HEIC",
        "out_filename": "ios17_background_dark.heic",
        "preview_filename": "ios17_background_dark.jpg"
    },
    {
        "id": "ios17_blue_light",
        "title": "iOS Floating Blue (Light)",
        "category": "Color Variant",
        "rootfs_path": "Library/Wallpaper/Collections/iOS_17~iphone.wallpaperCollection/Wallpapers/7565.iOS_17-440w-956h@3x~iphone.wallpaper/7565.iOS_17_Floating-440w-956h@3x~iphone.ca/assets/Blue Light.HEIC",
        "out_filename": "ios17_floating_blue_light.heic",
        "preview_filename": "ios17_floating_blue_light.jpg"
    },
    {
        "id": "ios17_blue_dark",
        "title": "iOS Floating Blue (Dark)",
        "category": "Color Variant",
        "rootfs_path": "Library/Wallpaper/Collections/iOS_17~iphone.wallpaperCollection/Wallpapers/7565.iOS_17-440w-956h@3x~iphone.wallpaper/7565.iOS_17_Floating-440w-956h@3x~iphone.ca/assets/Blue Dark.HEIC",
        "out_filename": "ios17_floating_blue_dark.heic",
        "preview_filename": "ios17_floating_blue_dark.jpg"
    },
    {
        "id": "ios17_purple_light",
        "title": "iOS Floating Purple (Light)",
        "category": "Color Variant",
        "rootfs_path": "Library/Wallpaper/Collections/iOS_17~iphone.wallpaperCollection/Wallpapers/7565.iOS_17-440w-956h@3x~iphone.wallpaper/7565.iOS_17_Floating-440w-956h@3x~iphone.ca/assets/Purple Light.HEIC",
        "out_filename": "ios17_floating_purple_light.heic",
        "preview_filename": "ios17_floating_purple_light.jpg"
    },
    {
        "id": "ios17_purple_dark",
        "title": "iOS Floating Purple (Dark)",
        "category": "Color Variant",
        "rootfs_path": "Library/Wallpaper/Collections/iOS_17~iphone.wallpaperCollection/Wallpapers/7565.iOS_17-440w-956h@3x~iphone.wallpaper/7565.iOS_17_Floating-440w-956h@3x~iphone.ca/assets/Purple Dark.HEIC",
        "out_filename": "ios17_floating_purple_dark.heic",
        "preview_filename": "ios17_floating_purple_dark.jpg"
    },
    {
        "id": "ios17_red_light",
        "title": "iOS Floating Red (Light)",
        "category": "Color Variant",
        "rootfs_path": "Library/Wallpaper/Collections/iOS_17~iphone.wallpaperCollection/Wallpapers/7565.iOS_17-440w-956h@3x~iphone.wallpaper/7565.iOS_17_Floating-440w-956h@3x~iphone.ca/assets/Red Light.HEIC",
        "out_filename": "ios17_floating_red_light.heic",
        "preview_filename": "ios17_floating_red_light.jpg"
    },
    {
        "id": "ios17_red_dark",
        "title": "iOS Floating Red (Dark)",
        "category": "Color Variant",
        "rootfs_path": "Library/Wallpaper/Collections/iOS_17~iphone.wallpaperCollection/Wallpapers/7565.iOS_17-440w-956h@3x~iphone.wallpaper/7565.iOS_17_Floating-440w-956h@3x~iphone.ca/assets/Red Dark.HEIC",
        "out_filename": "ios17_floating_red_dark.heic",
        "preview_filename": "ios17_floating_red_dark.jpg"
    },
    {
        "id": "ios17_orange_light",
        "title": "iOS Floating Orange (Light)",
        "category": "Color Variant",
        "rootfs_path": "Library/Wallpaper/Collections/iOS_17~iphone.wallpaperCollection/Wallpapers/7565.iOS_17-440w-956h@3x~iphone.wallpaper/7565.iOS_17_Floating-440w-956h@3x~iphone.ca/assets/Orange Lock Home Light.HEIC",
        "out_filename": "ios17_floating_orange_light.heic",
        "preview_filename": "ios17_floating_orange_light.jpg"
    },
    {
        "id": "ios17_orange_dark",
        "title": "iOS Floating Orange (Dark)",
        "category": "Color Variant",
        "rootfs_path": "Library/Wallpaper/Collections/iOS_17~iphone.wallpaperCollection/Wallpapers/7565.iOS_17-440w-956h@3x~iphone.wallpaper/7565.iOS_17_Floating-440w-956h@3x~iphone.ca/assets/Orange Lock Home Dark.HEIC",
        "out_filename": "ios17_floating_orange_dark.heic",
        "preview_filename": "ios17_floating_orange_dark.jpg"
    },
    {
        "id": "clownfish_bg",
        "title": "Apple Clownfish Heritage Wallpaper (Background)",
        "category": "Heritage Collection",
        "rootfs_path": "Library/Wallpaper/Collections/Clownfish~iphone.wallpaperCollection/Wallpapers/7420.Clownfish-402w-874h@3x~iphone.wallpaper/7420.Clownfish_Background-402w-874h@3x~iphone.ca/assets/Background.HEIC",
        "out_filename": "clownfish_background.heic",
        "preview_filename": "clownfish_background.jpg"
    },
    {
        "id": "clownfish_fg",
        "title": "Apple Clownfish Heritage Wallpaper (Foreground)",
        "category": "Heritage Collection",
        "rootfs_path": "Library/Wallpaper/Collections/Clownfish~iphone.wallpaperCollection/Wallpapers/7420.Clownfish-402w-874h@3x~iphone.wallpaper/7420.Clownfish_Foreground-402w-874h@3x~iphone.ca/assets/Foreground.HEIC",
        "out_filename": "clownfish_foreground.heic",
        "preview_filename": "clownfish_foreground.jpg"
    },
    {
        "id": "springboard_full_light",
        "title": "SpringBoard Full Screen Wallpaper (Light)",
        "category": "Compositor Framework",
        "rootfs_path": "System/Library/PrivateFrameworks/SpringBoardUIServices.framework/Full-Screen-Apps-Light.ca/assets/wallpaper.jpg",
        "out_filename": "springboard_wallpaper_light.jpg",
        "preview_filename": "springboard_wallpaper_light.jpg"
    },
    {
        "id": "springboard_full_dark",
        "title": "SpringBoard Full Screen Wallpaper (Dark)",
        "category": "Compositor Framework",
        "rootfs_path": "System/Library/PrivateFrameworks/SpringBoardUIServices.framework/Full-Screen-Apps-Dark.ca/assets/wallpaper-dark.jpg",
        "out_filename": "springboard_wallpaper_dark.jpg",
        "preview_filename": "springboard_wallpaper_dark.jpg"
    },
    {
        "id": "settings_default_light",
        "title": "Display & Brightness System Default (Light)",
        "category": "Settings System UI",
        "rootfs_path": "System/Library/PrivateFrameworks/Settings/DisplayAndBrightnessSettings.framework/Modern-Standard~iphone.ca/assets/iPhone_LTR_LM_default_wallpaper.png",
        "out_filename": "settings_default_wallpaper_light.png",
        "preview_filename": "settings_default_wallpaper_light.png"
    },
    {
        "id": "settings_default_dark",
        "title": "Display & Brightness System Default (Dark)",
        "category": "Settings System UI",
        "rootfs_path": "System/Library/PrivateFrameworks/Settings/DisplayAndBrightnessSettings.framework/Modern-Standard-Dark~iphone.ca/assets/iPhone_LTR_DM_default_wallpaper.png",
        "out_filename": "settings_default_wallpaper_dark.png",
        "preview_filename": "settings_default_wallpaper_dark.png"
    }
]

ICONS_MANIFEST = [
    {
        "id": "safari",
        "title": "Safari",
        "bundle_id": "com.apple.mobilesafari",
        "rootfs_path": "private/var/staged_system_apps/MobileSafari.app/AppIconUpdated60x60@2x.png",
        "out_filename": "safari.png"
    },
    {
        "id": "camera",
        "title": "Camera",
        "bundle_id": "com.apple.camera",
        "rootfs_path": "private/var/staged_system_apps/Camera.app/AppIcon60x60@2x.png",
        "out_filename": "camera.png"
    },
    {
        "id": "messages",
        "title": "Messages",
        "bundle_id": "com.apple.MobileSMS",
        "rootfs_path": "private/var/staged_system_apps/MobileSMS.app/AppIcon60x60@2x.png",
        "out_filename": "messages.png"
    },
    {
        "id": "settings",
        "title": "Settings",
        "bundle_id": "com.apple.Preferences",
        "rootfs_path": "Applications/Preferences.app/Settings60x60@2x.png",
        "out_filename": "settings.png"
    },
    {
        "id": "music",
        "title": "Apple Music",
        "bundle_id": "com.apple.Music",
        "rootfs_path": "private/var/staged_system_apps/Music.app/AppIcon-iOS60x60@2x.png",
        "out_filename": "music.png"
    },
    {
        "id": "photos",
        "title": "Photos",
        "bundle_id": "com.apple.mobileslideshow",
        "rootfs_path": "private/var/staged_system_apps/Photos.app/AppIcon60x60@2x.png",
        "out_filename": "photos.png"
    },
    {
        "id": "phone",
        "title": "Phone",
        "bundle_id": "com.apple.mobilephone",
        "rootfs_path": "Applications/MobilePhone.app/AppIcon60x60@2x.png",
        "out_filename": "phone.png"
    },
    {
        "id": "mail",
        "title": "Mail",
        "bundle_id": "com.apple.mobilemail",
        "rootfs_path": "private/var/staged_system_apps/MobileMail.app/AppIcon60x60@2x.png",
        "out_filename": "mail.png"
    },
    {
        "id": "maps",
        "title": "Apple Maps",
        "bundle_id": "com.apple.Maps",
        "rootfs_path": "private/var/staged_system_apps/Maps.app/AppIcon60x60@2x.png",
        "out_filename": "maps.png"
    },
    {
        "id": "appstore",
        "title": "App Store",
        "bundle_id": "com.apple.AppStore",
        "rootfs_path": "private/var/staged_system_apps/MobileStore.app/AppIcon60x60@2x.png",
        "out_filename": "app_store.png"
    },
    {
        "id": "facetime",
        "title": "FaceTime",
        "bundle_id": "com.apple.facetime",
        "rootfs_path": "private/var/staged_system_apps/FaceTime.app/AppIcon60x60@2x.png",
        "out_filename": "facetime.png"
    },
    {
        "id": "health",
        "title": "Health",
        "bundle_id": "com.apple.Health",
        "rootfs_path": "private/var/staged_system_apps/Health.app/AppIcon60x60@2x.png",
        "out_filename": "health.png"
    },
    {
        "id": "findmy",
        "title": "Find My",
        "bundle_id": "com.apple.findmy",
        "rootfs_path": "private/var/staged_system_apps/FindMy.app/AppIcon60x60@2x.png",
        "out_filename": "find_my.png"
    },
    {
        "id": "files",
        "title": "Files",
        "bundle_id": "com.apple.DocumentsApp",
        "rootfs_path": "private/var/staged_system_apps/Files.app/AppIcon60x60@2x.png",
        "out_filename": "files.png"
    },
    {
        "id": "weather",
        "title": "Weather",
        "bundle_id": "com.apple.weather",
        "rootfs_path": "private/var/staged_system_apps/Weather.app/AppIcon60x60@2x.png",
        "out_filename": "weather.png"
    },
    {
        "id": "calculator",
        "title": "Calculator",
        "bundle_id": "com.apple.calculator",
        "rootfs_path": "private/var/staged_system_apps/Calculator.app/AppIcon60x60@2x.png",
        "out_filename": "calculator.png"
    },
    {
        "id": "notes",
        "title": "Notes",
        "bundle_id": "com.apple.mobilenotes",
        "rootfs_path": "private/var/staged_system_apps/MobileNotes.app/AppIcon60x60@2x.png",
        "out_filename": "notes.png"
    },
    {
        "id": "reminders",
        "title": "Reminders",
        "bundle_id": "com.apple.reminders",
        "rootfs_path": "private/var/staged_system_apps/Reminders.app/AppIcon60x60@2x.png",
        "out_filename": "reminders.png"
    },
    {
        "id": "clock",
        "title": "Clock",
        "bundle_id": "com.apple.mobiletimer",
        "rootfs_path": "private/var/staged_system_apps/MobileTimer.app/AppIcon60x60@2x.png",
        "out_filename": "clock.png"
    },
    {
        "id": "calendar",
        "title": "Calendar",
        "bundle_id": "com.apple.mobilecal",
        "rootfs_path": "private/var/staged_system_apps/MobileCal.app/AppIcon60x60@2x.png",
        "out_filename": "calendar.png"
    },
    {
        "id": "shortcuts",
        "title": "Shortcuts",
        "bundle_id": "com.apple.shortcuts",
        "rootfs_path": "private/var/staged_system_apps/Shortcuts.app/AppIcon60x60@2x.png",
        "out_filename": "shortcuts.png"
    },
    {
        "id": "passwords",
        "title": "Passwords",
        "bundle_id": "com.apple.Passwords",
        "rootfs_path": "private/var/staged_system_apps/Passwords.app/AppIconUpdated60x60@2x.png",
        "out_filename": "passwords.png"
    }
]

def paeth_predictor(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    else:
        return c

def decode_cgbi_png(input_bytes):
    """
    Decodes an Apple CgBI-compressed PNG into standard PIL Image with correct RGBA channels.
    Handles scanline filters 0, 1, 2, 3, 4 and unpremultiplication of alpha channels.
    """
    if len(input_bytes) < 8 or input_bytes[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError("Invalid PNG header")
    
    pos = 8
    width, height = 0, 0
    bit_depth, color_type = 8, 6
    compressed_idat = b''
    is_cgbi = False
    
    while pos < len(input_bytes):
        length = struct.unpack('>I', input_bytes[pos:pos+4])[0]
        chunk_type = input_bytes[pos+4:pos+8]
        chunk_data = input_bytes[pos+8:pos+8+length]
        pos += 12 + length
        
        if chunk_type == b'CgBI':
            is_cgbi = True
        elif chunk_type == b'IHDR':
            width, height, bit_depth, color_type, comp_m, filter_m, inter_m = struct.unpack('>IIBBBBB', chunk_data[:13])
        elif chunk_type == b'IDAT':
            compressed_idat += chunk_data
    
    if not is_cgbi:
        # Standard PNG, open directly via PIL
        import io
        return Image.open(io.BytesIO(input_bytes))
    
    # Apple CgBI IDAT is raw deflate without zlib wrapper (wbits = -15)
    decompressed = zlib.decompress(compressed_idat, -15)
    bpp = 4 # RGBA
    line_stride = width * bpp
    
    raw_pixels = bytearray(width * height * 4)
    prev_line = bytearray(line_stride)
    current_line = bytearray(line_stride)
    
    in_idx = 0
    out_idx = 0
    
    for y in range(height):
        filter_type = decompressed[in_idx]
        in_idx += 1
        filt_bytes = decompressed[in_idx:in_idx + line_stride]
        in_idx += line_stride
        
        # Unfilter scanline
        for x in range(line_stride):
            f_val = filt_bytes[x]
            left = current_line[x - bpp] if x >= bpp else 0
            up = prev_line[x]
            up_left = prev_line[x - bpp] if x >= bpp else 0
            
            if filter_type == 0: # None
                recon = f_val
            elif filter_type == 1: # Sub
                recon = (f_val + left) & 0xFF
            elif filter_type == 2: # Up
                recon = (f_val + up) & 0xFF
            elif filter_type == 3: # Average
                recon = (f_val + ((left + up) >> 1)) & 0xFF
            elif filter_type == 4: # Paeth
                recon = (f_val + paeth_predictor(left, up, up_left)) & 0xFF
            else:
                recon = f_val
            current_line[x] = recon
        
        # Convert scanline: BGRA -> RGBA and unpremultiply alpha
        for p in range(0, line_stride, 4):
            b = current_line[p]
            g = current_line[p + 1]
            r = current_line[p + 2]
            a = current_line[p + 3]
            
            if a > 0 and a < 255:
                r = min(255, int(r * 255 / a))
                g = min(255, int(g * 255 / a))
                b = min(255, int(b * 255 / a))
            elif a == 0:
                r, g, b = 0, 0, 0
                
            raw_pixels[out_idx] = r
            raw_pixels[out_idx + 1] = g
            raw_pixels[out_idx + 2] = b
            raw_pixels[out_idx + 3] = a
            out_idx += 4
            
        prev_line[:] = current_line
        
    return Image.frombytes('RGBA', (width, height), bytes(raw_pixels))

def extract_file_from_dmg(rootfs_path, temp_dest):
    cmd = ["7z", "x", DMG_PATH, rootfs_path, f"-o{temp_dest}", "-y"]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        return None
    full_extracted = os.path.join(temp_dest, rootfs_path)
    if os.path.exists(full_extracted):
        return full_extracted
    # Search recursively in temp_dest for basename
    basename = os.path.basename(rootfs_path)
    for root, dirs, files in os.walk(temp_dest):
        if basename in files:
            return os.path.join(root, basename)
    return None

def main():
    print("[*] Initializing Visual UI Asset Extractor...")
    os.makedirs(WALLPAPERS_DIR, exist_ok=True)
    os.makedirs(ICONS_DIR, exist_ok=True)
    os.makedirs(ARTIFACT_ASSETS_DIR, exist_ok=True)
    
    temp_dir = "/tmp/ios27_ui_extract"
    os.makedirs(temp_dir, exist_ok=True)
    
    extracted_wallpapers = []
    extracted_icons = []
    
    # 1. Extract Wallpapers
    print(f"[*] Extracting {len(WALLPAPERS_MANIFEST)} factory wallpapers...")
    for wp in WALLPAPERS_MANIFEST:
        dest_path = os.path.join(WALLPAPERS_DIR, wp["out_filename"])
        preview_dest_path = os.path.join(WALLPAPERS_DIR, wp["preview_filename"])
        artifact_embed_path = os.path.join(ARTIFACT_ASSETS_DIR, wp["preview_filename"])
        
        if not os.path.exists(dest_path):
            extracted = extract_file_from_dmg(wp["rootfs_path"], temp_dir)
            if not extracted or not os.path.exists(extracted):
                print(f"[-] FAILED to extract wallpaper: {wp['rootfs_path']}")
                continue
            shutil.copy2(extracted, dest_path)
        file_size = os.path.getsize(dest_path)
        
        # Preview handling: if HEIC, convert to JPG using heif-convert
        if dest_path.lower().endswith(".heic"):
            cmd = ["heif-convert", dest_path, preview_dest_path]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif dest_path.lower().endswith((".jpg", ".png")):
            if os.path.abspath(dest_path) != os.path.abspath(preview_dest_path):
                shutil.copy2(dest_path, preview_dest_path)
            
        # Copy preview to artifact assets directory for markdown embedding
        if os.path.exists(preview_dest_path):
            shutil.copy2(preview_dest_path, artifact_embed_path)
            try:
                with Image.open(preview_dest_path) as im:
                    res_str = f"{im.width}x{im.height}"
            except Exception:
                res_str = "N/A"
        else:
            res_str = "N/A"
            
        print(f"[+] Wallpaper: {wp['title']} -> {dest_path} ({file_size} B, {res_str})")
        extracted_wallpapers.append({
            "id": wp["id"],
            "title": wp["title"],
            "category": wp["category"],
            "rootfs_path": wp["rootfs_path"],
            "local_file": dest_path,
            "preview_file": preview_dest_path,
            "artifact_path": artifact_embed_path,
            "size_bytes": file_size,
            "resolution": res_str,
            "format": os.path.splitext(wp["out_filename"])[1].upper().replace(".", "")
        })
        
    # 2. Extract App Icons
    print(f"[*] Extracting {len(ICONS_MANIFEST)} core application icons...")
    for icon in ICONS_MANIFEST:
        dest_path = os.path.join(ICONS_DIR, icon["out_filename"])
        artifact_embed_path = os.path.join(ARTIFACT_ASSETS_DIR, icon["out_filename"])
        
        extracted = extract_file_from_dmg(icon["rootfs_path"], temp_dir)
        if not extracted or not os.path.exists(extracted):
            print(f"[-] FAILED to extract icon: {icon['rootfs_path']}")
            continue
            
        with open(extracted, "rb") as f:
            raw_bytes = f.read()
            
        # Decode Apple CgBI PNG and save as clean W3C PNG
        try:
            clean_img = decode_cgbi_png(raw_bytes)
            clean_img.save(dest_path, "PNG")
            clean_img.save(artifact_embed_path, "PNG")
            res_str = f"{clean_img.width}x{clean_img.height}"
            file_size = os.path.getsize(dest_path)
            status = "Decoded CgBI -> W3C PNG"
        except Exception as e:
            # Fallback to direct raw copy
            shutil.copy2(extracted, dest_path)
            shutil.copy2(extracted, artifact_embed_path)
            res_str = "120x120"
            file_size = len(raw_bytes)
            status = f"Raw PNG copy ({e})"
            
        print(f"[+] App Icon: {icon['title']} ({icon['bundle_id']}) -> {dest_path} ({file_size} B, {res_str}, {status})")
        extracted_icons.append({
            "id": icon["id"],
            "title": icon["title"],
            "bundle_id": icon["bundle_id"],
            "rootfs_path": icon["rootfs_path"],
            "local_file": dest_path,
            "artifact_path": artifact_embed_path,
            "size_bytes": file_size,
            "resolution": res_str,
            "status": status
        })
        
    # Clean up temp extraction
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    # 3. Save Structured Manifest
    manifest_data = {
        "wallpapers_count": len(extracted_wallpapers),
        "wallpapers": extracted_wallpapers,
        "icons_count": len(extracted_icons),
        "icons": extracted_icons
    }
    manifest_path = "artifacts/ui/ui_asset_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"[+] Wrote UI Asset Manifest to {manifest_path}")

if __name__ == "__main__":
    main()
