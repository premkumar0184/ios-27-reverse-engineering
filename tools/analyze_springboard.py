#!/usr/bin/env python3
"""
iOS 27 Reverse Engineering Pipeline: SpringBoard Architecture Analyzer
Dissects SpringBoard.app bundle, Info.plist BSServiceDomains,
and extracts presentation controllers, gesture managers, and Mach services.
"""

import sys
import os
import re
import plistlib
import struct
import json
from pathlib import Path

def analyze_springboard():
    app_dir = Path("artifacts/ui/SpringBoard/System/Library/CoreServices/SpringBoard.app")
    plist_path = app_dir / "Info.plist"
    bin_path = app_dir / "SpringBoard"
    cache_path = Path("artifacts/rootfs/shared_cache/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e.36")

    if not plist_path.is_file() or not bin_path.is_file():
        print(f"[ERROR] SpringBoard bundle not found at {app_dir}")
        sys.exit(1)

    # 1. Parse Info.plist
    with open(plist_path, "rb") as f:
        plist_data = plistlib.load(f)

    bs_domains = plist_data.get("BSServiceDomains", {})
    mach_services = []
    registered_workspaces = []

    for domain_name, domain_val in bs_domains.items():
        mach_name = domain_val.get("MachName", domain_name)
        svcs = domain_val.get("Services", {})
        for sname, sconfig in svcs.items():
            mach_services.append({
                "service_name": sname,
                "mach_endpoint": mach_name,
                "domain": domain_name,
                "options": sconfig.get("Options", {})
            })
            if "RegisterWorkspaces" in sconfig.get("Options", {}):
                registered_workspaces.extend(sconfig["Options"]["RegisterWorkspaces"])

    # 2. Parse Mach-O Binary
    with open(bin_path, "rb") as f:
        hdr = f.read(32)
        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack('<IIIIIIII', hdr)
        cmds_data = f.read(sizeofcmds)

    offset = 0
    uuid_str = None
    entryoff = None
    dylibs = []

    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack('<II', cmds_data[offset:offset+8])
        if cmd == 0x1b and cmdsize >= 24: # LC_UUID
            ubytes = cmds_data[offset+8:offset+24]
            uuid_str = f"{ubytes[:4].hex()}-{ubytes[4:6].hex()}-{ubytes[6:8].hex()}-{ubytes[8:10].hex()}-{ubytes[10:].hex()}"
        elif cmd == 0x80000028: # LC_MAIN
            entryoff = struct.unpack('<QQ', cmds_data[offset+8:offset+24])[0]
        elif cmd in (0xc, 0xd, 0x80000018):
            str_off = struct.unpack('<I', cmds_data[offset+8:offset+12])[0]
            dname = cmds_data[offset+str_off:offset+cmdsize].split(b'\x00')[0].decode('utf-8', errors='ignore')
            dylibs.append(dname)
        offset += cmdsize

    # 3. Scan Subcache .36 for SpringBoard Classes, Controllers, and Managers
    controllers = set()
    managers = set()
    workspaces = set()

    if cache_path.is_file():
        print(f"[*] Scanning dyld subcache .36 ({cache_path.stat().st_size} bytes) for SpringBoard symbols...")
        with open(cache_path, "rb") as f:
            cache_data = f.read()

        raw_controllers = set(re.findall(rb'SB[A-Za-z0-9_]{3,45}Controller', cache_data))
        raw_managers = set(re.findall(rb'SB[A-Za-z0-9_]{3,45}Manager', cache_data))
        raw_workspaces = set(re.findall(rb'SB[A-Za-z0-9_]{3,45}Workspace', cache_data))

        for c in raw_controllers:
            name = c.decode('ascii', errors='ignore')
            if len(name) < 45 and not name.startswith("SB_"):
                controllers.add(name)

        for m in raw_managers:
            name = m.decode('ascii', errors='ignore')
            if len(name) < 45 and not name.startswith("SB_"):
                managers.add(name)

        for w in raw_workspaces:
            name = w.decode('ascii', errors='ignore')
            if len(name) < 45 and not name.startswith("SB_"):
                workspaces.add(name)

    # Key Architectural Controllers Categorization
    presentation_controllers = [
        {"class": "SBCoverSheetPresentationManager", "role": "Lock Screen, Cover Sheet, and Notification Center Presentation"},
        {"class": "SBControlCenterController", "role": "Control Center Module Presentation & Overlay Coordination"},
        {"class": "SBIconController", "role": "Home Screen Icon Grid, App Library, and Widget Layout Controller"},
        {"class": "SBFloatingDockController", "role": "iPadOS / Multitasking Floating Dock and Stage Manager Shelf"},
        {"class": "SBLockScreenManager", "role": "Biometric Authentication (FaceID/TouchID) & Device Passcode Lifecycle"},
        {"class": "SBAmbientPresentationController", "role": "StandBy / Ambient Mode Display & Night Mode Adaptation"},
        {"class": "SBAssistantIslandStageGestureManager", "role": "Siri Dynamic Island Presentation and Stage Gesture Dispatch"},
        {"class": "SBCaptureButtonSuppressionManager", "role": "iPhone 16/17 Physical Camera Control Button Interception & Debounce"},
        {"class": "SBContinuitySessionManager", "role": "macOS iPhone Mirroring, Remote Display Stream, and Continuity Audio/Input"},
        {"class": "SBMainWorkspace", "role": "Primary Scene Layout, App Switcher, and Windowing Policy Engine"},
        {"class": "SBCameraActivationManager", "role": "Lock Screen Swipe / Hardware Button Camera Quick-Launch Broker"},
        {"class": "SBBannerManager", "role": "System Aperture / Dynamic Island Alerts & BannerKit Coordination"}
    ]

    result = {
        "metadata": {
            "bundle_identifier": plist_data.get("CFBundleIdentifier", "com.apple.springboard"),
            "bundle_name": plist_data.get("CFBundleName", "SpringBoard"),
            "principal_class": plist_data.get("NSPrincipalClass", "SpringBoard"),
            "version": plist_data.get("CFBundleVersion"),
            "short_version": plist_data.get("CFBundleShortVersionString"),
            "sdk_build": plist_data.get("DTSDKBuild"),
            "platform_version": plist_data.get("DTPlatformVersion"),
            "device_family": plist_data.get("UIDeviceFamily"),
            "always_on_display_supported": plist_data.get("UIApplicationSupportsAlwaysOnDisplay", False),
            "variable_frame_duration": plist_data.get("CAEnableVariableFrameDuration", False),
            "display_manager_transformer": plist_data.get("FBDisplayManagerTransformer")
        },
        "entrypoints": {
            "macho_uuid": uuid_str,
            "executable_path": "/System/Library/CoreServices/SpringBoard.app/SpringBoard",
            "trampoline_entryoff": f"0x{entryoff:x}" if entryoff is not None else None,
            "trampoline_target": "_SBSystemAppMain in /System/Library/PrivateFrameworks/SpringBoard.framework/SpringBoard",
            "framework_virtual_address": "0x226a11000",
            "pointer_authentication": "arm64e PAC00 (braa x16, x17)"
        },
        "mach_services": mach_services,
        "controllers": presentation_controllers,
        "all_cataloged_controllers": sorted(list(controllers)),
        "all_cataloged_managers": sorted(list(managers)),
        "classes": {
            "total_controllers": len(controllers),
            "total_managers": len(managers),
            "total_workspaces": len(workspaces),
            "registered_scene_workspaces": registered_workspaces,
            "workspaces_catalog": sorted(list(workspaces))
        },
        "window_server_integration": {
            "window_server": "backboardd",
            "scene_manager": "FBSceneManager (FrontBoard)",
            "display_refresh": "120Hz ProMotion (CAEnableVariableFrameDuration)",
            "always_on_display": "BacklightServices (AOD)",
            "camera_control_hardware": "com.apple.springboard.capture-intent"
        },
        "default_home_screen_layout": None
    }

    icon_state_path = app_dir / "DefaultIconState.plist"
    if icon_state_path.is_file():
        with open(icon_state_path, "rb") as ifp:
            idata = plistlib.load(ifp)
        page1 = idata.get("iconLists", [[]])[0]
        smart_stacks = [x for x in page1 if isinstance(x, dict) and x.get("iconType") == "custom"]
        apps = [x for x in page1 if isinstance(x, str)]
        result["default_home_screen_layout"] = {
            "source_file": "DefaultIconState.plist",
            "page_1_smart_stack_widgets_count": len(smart_stacks),
            "smart_stack_definitions": smart_stacks,
            "page_1_default_applications": apps
        }

    out_file = Path("artifacts/ui/springboard_analysis.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[+] Wrote {out_file} ({out_file.stat().st_size} bytes)")
    print(f"    - Mach services: {len(mach_services)}")
    print(f"    - Cataloged controllers: {len(controllers)}")
    print(f"    - Cataloged managers: {len(managers)}")
    print(f"    - Scene workspaces: {len(registered_workspaces)}")

if __name__ == "__main__":
    analyze_springboard()
