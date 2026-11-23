#!/usr/bin/env python3
"""
verify_admac_evolution.py - Comprehensive Invariant and Geometry Verification
Tracks: AudioDMA Controller (ADMAC Evolution t8150) & Multichannel Audio (MCA)
Reverse Engineering on Apple Silicon A19 Pro (t8150 / iOS 27.2).

Asserts 100% green verification across:
1. Devicetree unpacked raw binary (artifacts/dcp/devicetree_unpacked.raw)
2. Kernelcache release raw binary (artifacts/kernel/kernelcache.release.raw)
3. Kext catalog release (artifacts/kernel/kext_catalog_release.json)
4. JSON specifications:
   - artifacts/audio/dma/admac_channel_geometry_spec.json
   - artifacts/audio/dma/mca_bus_topology_spec.json
   - artifacts/audio/dma/audio_dma_ring_buffer_protocol.json
"""

import sys
import os
import struct
import json
import re

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
DT_RAW_PATH = os.path.join(ROOT_DIR, "artifacts/dcp/devicetree_unpacked.raw")
KERNEL_RAW_PATH = os.path.join(ROOT_DIR, "artifacts/kernel/kernelcache.release.raw")
KEXT_CATALOG_PATH = os.path.join(ROOT_DIR, "artifacts/kernel/kext_catalog_release.json")

GEOMETRY_SPEC_PATH = os.path.join(ROOT_DIR, "artifacts/audio/dma/admac_channel_geometry_spec.json")
TOPOLOGY_SPEC_PATH = os.path.join(ROOT_DIR, "artifacts/audio/dma/mca_bus_topology_spec.json")
PROTOCOL_SPEC_PATH = os.path.join(ROOT_DIR, "artifacts/audio/dma/audio_dma_ring_buffer_protocol.json")

class TestFailure(Exception):
    pass

total_asserts = 0
passed_asserts = 0

def check(condition, message):
    global total_asserts, passed_asserts
    total_asserts += 1
    if not condition:
        print(f"[FAIL] {message}")
        raise TestFailure(message)
    else:
        passed_asserts += 1

def parse_devicetree_node(data, offset):
    num_props, num_children = struct.unpack_from('<II', data, offset)
    offset += 8
    props = {}
    for _ in range(num_props):
        prop_name = data[offset:offset+32].split(b'\x00')[0].decode('latin1')
        length = struct.unpack_from('<I', data, offset+32)[0] & 0x7fffffff
        val = data[offset+36:offset+36+length]
        props[prop_name] = val
        pad = (4 - (length % 4)) % 4
        offset += 36 + length + pad
    children = []
    for _ in range(num_children):
        child, offset = parse_devicetree_node(data, offset)
        children.append(child)
    return {'props': props, 'children': children}, offset

def test_json_specifications():
    print("\n--- 1. Testing JSON Specifications Integrity ---")
    for spec_path, name in [
        (GEOMETRY_SPEC_PATH, "admac_channel_geometry_spec.json"),
        (TOPOLOGY_SPEC_PATH, "mca_bus_topology_spec.json"),
        (PROTOCOL_SPEC_PATH, "audio_dma_ring_buffer_protocol.json")
    ]:
        check(os.path.exists(spec_path), f"Spec file exists: {name}")
        with open(spec_path, "r") as f:
            data = json.load(f)
        check("soc" in data and data["soc"] == "t8150", f"{name}: soc == t8150")
        check("target_os" in data and "27.2" in data["target_os"], f"{name}: target_os == iOS 27.2")

    # Geometry spec specifics
    with open(GEOMETRY_SPEC_PATH, "r") as f:
        geom = json.load(f)
    check(len(geom["controllers"]) == 4, "Geometry spec contains exactly 4 ADMAC controllers")
    controller_names = [c["node_name"] for c in geom["controllers"]]
    check("admac-base-ns" in controller_names, "admac-base-ns present in geometry spec")
    check("admac-base-s" in controller_names, "admac-base-s present in geometry spec")
    check("admac-leap-ns" in controller_names, "admac-leap-ns present in geometry spec")
    check("admac-leap-s" in controller_names, "admac-leap-s present in geometry spec")

    # Topology spec specifics
    with open(TOPOLOGY_SPEC_PATH, "r") as f:
        topo = json.load(f)
    check(len(topo["mca_buses"]) == 6, "MCA bus count == 6 (audio-mca0 to audio-mca5)")
    check(len(topo["pdm_microphone_buses"]) == 3, "PDM bus count == 3 (audio-pdm0 to audio-pdm2)")
    check(len(topo["hardware_loopback_monitors"]) == 4, "Loopback count == 4")

    # Protocol spec specifics
    with open(PROTOCOL_SPEC_PATH, "r") as f:
        proto = json.load(f)
    check(proto["channel_state_machine"]["states_count"] == 11, "State machine states count == 11")
    check(proto["channel_state_machine"]["operations_count"] == 14, "State machine operations count == 14")
    check(proto["hardware_descriptor_geometry"]["descriptor_size_bytes"] == 16, "Hardware descriptor size == 16 bytes")
    print("  [OK] JSON specifications passed validation.")

def test_devicetree_admac_invariants():
    print("\n--- 2. Testing DeviceTree ADMAC Hardware Invariants ---")
    check(os.path.exists(DT_RAW_PATH), "Devicetree raw binary exists")
    with open(DT_RAW_PATH, "rb") as f:
        dt_data = f.read()

    root, _ = parse_devicetree_node(dt_data, 0)
    arm_io_nodes = [c for c in root['children'] if c['props'].get('name', b'').startswith(b'arm-io')]
    check(len(arm_io_nodes) > 0, "arm-io node found in devicetree")
    arm_io = arm_io_nodes[0]

    # Map children by name
    children_by_name = {}
    for c in arm_io['children']:
        cname = c['props'].get('name', b'').split(b'\x00')[0].decode('latin1')
        children_by_name[cname] = c

    # 1. admac-base-ns
    check("admac-base-ns" in children_by_name, "admac-base-ns node exists")
    base_ns = children_by_name["admac-base-ns"]
    check(base_ns['props'].get('compatible', b'').startswith(b'admac-evolution,t8150'), "base-ns compatible is admac-evolution,t8150")
    check(base_ns['props'].get('device_type', b'').startswith(b'admac'), "base-ns device_type is admac")
    check(struct.unpack('<I', base_ns['props']['role'])[0] == 0x42414e53, "base-ns role is 'BANS' (0x42414e53)")
    check(struct.unpack('<Q', base_ns['props']['#dma-channels-tx'])[0] == 13, "base-ns #dma-channels-tx == 13")
    check(struct.unpack('<Q', base_ns['props']['#dma-channels-rx'])[0] == 13, "base-ns #dma-channels-rx == 13")
    check(struct.unpack('<I', base_ns['props']['interrupts'])[0] == 408, "base-ns interrupt == 408 (0x198)")
    check(len(base_ns['children']) == 7, "base-ns has exactly 7 instantiated channel nodes")

    # Verify channel nodes in admac-base-ns
    base_ns_ch_names = [sc['props'].get('name', b'').split(b'\x00')[0].decode('latin1') for sc in base_ns['children']]
    expected_base_ns_channels = [
        "base-ns-adma-tx-1", "base-ns-adma-rx-1", "base-ns-adma-rx-3",
        "base-ns-adma-rx-4", "base-ns-adma-rx-5", "base-ns-adma-rx-6", "base-ns-adma-tx-8"
    ]
    for ch_name in expected_base_ns_channels:
        check(ch_name in base_ns_ch_names, f"base-ns channel {ch_name} present")

    # 2. admac-base-s
    check("admac-base-s" in children_by_name, "admac-base-s node exists")
    base_s = children_by_name["admac-base-s"]
    check(base_s['props'].get('compatible', b'').startswith(b'admac-evolution,t8150'), "base-s compatible is admac-evolution,t8150")
    check(struct.unpack('<I', base_s['props']['role'])[0] == 0x42415353, "base-s role is 'BASS' (0x42415353)")
    check(struct.unpack('<I', base_s['props']['#dma-channels-tx'][:4])[0] == 5, "base-s #dma-channels-tx == 5")
    check(struct.unpack('<I', base_s['props']['#dma-channels-rx'][:4])[0] == 14, "base-s #dma-channels-rx == 14")
    check(struct.unpack('<I', base_s['props']['interrupts'])[0] == 407, "base-s interrupt == 407 (0x197)")
    check(len(base_s['children']) == 3, "base-s has exactly 3 instantiated channel nodes")

    # 3. admac-leap-ns
    check("admac-leap-ns" in children_by_name, "admac-leap-ns node exists")
    leap_ns = children_by_name["admac-leap-ns"]
    check(leap_ns['props'].get('compatible', b'').startswith(b'admac-evolution,t8150'), "leap-ns compatible is admac-evolution,t8150")
    check(struct.unpack('<I', leap_ns['props']['role'])[0] == 0x4c454e53, "leap-ns role is 'LENS' (0x4c454e53)")
    check(struct.unpack('<I', leap_ns['props']['#dma-channels-tx'][:4])[0] == 9, "leap-ns #dma-channels-tx == 9")
    check(struct.unpack('<I', leap_ns['props']['#dma-channels-rx'][:4])[0] == 9, "leap-ns #dma-channels-rx == 9")
    check(struct.unpack('<I', leap_ns['props']['interrupts'])[0] == 411, "leap-ns interrupt == 411 (0x19b)")
    check(len(leap_ns['children']) == 5, "leap-ns has exactly 5 instantiated channel nodes")

    # 4. admac-leap-s
    check("admac-leap-s" in children_by_name, "admac-leap-s node exists")
    leap_s = children_by_name["admac-leap-s"]
    check(leap_s['props'].get('compatible', b'').startswith(b'admac-evolution,t8150'), "leap-s compatible is admac-evolution,t8150")
    check(struct.unpack('<I', leap_s['props']['role'])[0] == 0x4c455353, "leap-s role is 'LESS' (0x4c455353)")
    check(struct.unpack('<I', leap_s['props']['#dma-channels-tx'][:4])[0] == 4, "leap-s #dma-channels-tx == 4")
    check(struct.unpack('<I', leap_s['props']['#dma-channels-rx'][:4])[0] == 9, "leap-s #dma-channels-rx == 9")
    check(struct.unpack('<I', leap_s['props']['interrupts'])[0] == 410, "leap-s interrupt == 410 (0x19a)")
    check(len(leap_s['children']) == 1, "leap-s has exactly 1 instantiated channel node (leap-s-adma-rx-4)")

    # Test 4-aperture geometry for each channel
    for controller_node in [base_ns, base_s, leap_ns, leap_s]:
        for ch in controller_node['children']:
            ch_name = ch['props'].get('name', b'').split(b'\x00')[0].decode('latin1')
            reg_val = ch['props'].get('reg', b'')
            check(len(reg_val) == 64, f"Channel {ch_name} has 64-byte reg property (4 apertures)")
            # unpack 4 apertures
            b0, s0, b1, s1, b2, s2, b3, s3 = struct.unpack('<QQQQQQQQ', reg_val)
            check(s0 == 0x4000, f"Channel {ch_name} aperture 0 (Control) size == 0x4000 (16KB)")
            check(s1 == 4, f"Channel {ch_name} aperture 1 (TD FIFO) size == 4 bytes")
            check(s2 == 4, f"Channel {ch_name} aperture 2 (CS FIFO) size == 4 bytes")
            check(s3 == 4, f"Channel {ch_name} aperture 3 (PCT FIFO) size == 4 bytes")

    # DART Mappers under dart-aop
    check("dart-aop" in children_by_name, "dart-aop found in arm-io")
    dart_aop = children_by_name["dart-aop"]
    dart_mappers = {sc['props'].get('name', b'').split(b'\x00')[0].decode('latin1'): sc for sc in dart_aop['children']}

    check("mapper-admac-base-ns" in dart_mappers, "mapper-admac-base-ns present in dart-aop")
    check(struct.unpack('<I', dart_mappers["mapper-admac-base-ns"]['props']['reg'])[0] == 8, "mapper-admac-base-ns SID == 8")
    check('allow-subpage-mapping' in dart_mappers["mapper-admac-base-ns"]['props'], "mapper-admac-base-ns allows subpage mapping")

    check("mapper-admac-base-s" in dart_mappers, "mapper-admac-base-s present in dart-aop")
    check(struct.unpack('<I', dart_mappers["mapper-admac-base-s"]['props']['reg'])[0] == 9, "mapper-admac-base-s SID == 9")

    check("mapper-admac-leap-ns" in dart_mappers, "mapper-admac-leap-ns present in dart-aop")
    check(struct.unpack('<I', dart_mappers["mapper-admac-leap-ns"]['props']['reg'])[0] == 10, "mapper-admac-leap-ns SID == 10")
    check('allow-subpage-mapping' in dart_mappers["mapper-admac-leap-ns"]['props'], "mapper-admac-leap-ns allows subpage mapping")

    check("mapper-admac-leap-s" in dart_mappers, "mapper-admac-leap-s present in dart-aop")
    check(struct.unpack('<I', dart_mappers["mapper-admac-leap-s"]['props']['reg'])[0] == 11, "mapper-admac-leap-s SID == 11")

    # PMGR audio devices
    check("pmgr" in children_by_name, "pmgr found in arm-io")
    pmgr_devs = children_by_name["pmgr"]['props']['devices']
    for pmgr_target in [b'AUDIO_MCA0_M', b'AUDIO_MCA1_M', b'AUDIO_MCA2_M', b'AUDIO_MCA3_M', b'AUDIO_MCA4_M', b'AUDIO_MCA5_M', b'AUDIO_LEAP_MCA', b'AUDIO_SENSE_PDMC', b'PDM0_AUDIO_REF', b'PDM1_AUDIO_REF', b'AUDIO-LLT-V']:
        check(pmgr_target in pmgr_devs, f"PMGR devices contains {pmgr_target.decode()}")

    # IOP Audio Controller endpoints
    check("iop-audio-controller" in children_by_name, "iop-audio-controller found in arm-io")
    iop_audio = children_by_name["iop-audio-controller"]
    iop_children = {sc['props'].get('name', b'').split(b'\x00')[0].decode('latin1'): sc for sc in iop_audio['children']}
    for ep in ["audio-hp", "audio-receiver", "audio-speaker-mca", "audio-speaker-tap", "audio-mca-loopback", "audio-s-leap-internal-loopback", "audio-leap-internal-loopback"]:
        check(ep in iop_children, f"IOP audio endpoint {ep} found")

    print("  [OK] DeviceTree ADMAC hardware invariants verified.")

def test_kernelcache_symbols_and_classes():
    print("\n--- 3. Testing Kernelcache Symbols & Class Hierarchy ---")
    check(os.path.exists(KERNEL_RAW_PATH), "Kernelcache release binary exists")
    with open(KERNEL_RAW_PATH, "rb") as f:
        kernel_data = f.read()

    # Check kext catalog
    check(os.path.exists(KEXT_CATALOG_PATH), "Kext catalog json exists")
    with open(KEXT_CATALOG_PATH, "r") as f:
        kext_catalog = json.load(f)
    kext_ids = [k.get("bundle_id") for k in kext_catalog if k.get("bundle_id")]

    for required_kext in [
        "com.apple.driver.AudioDMAController-T8150",
        "com.apple.driver.AudioDMACLLTEscalationDetector-T8150",
        "com.apple.driver.AudioDMAFamily",
        "com.apple.driver.AudioSharedDARTMapperProxy",
        "com.apple.driver.DMAChannelProxy",
        "com.apple.driver.AppleIOPADMAStream",
        "com.apple.iokit.AppleARMIISAudio",
        "com.apple.driver.AppleAOPAudio"
    ]:
        check(required_kext in kext_ids, f"Kext present in kernelcache catalog: {required_kext}")

    # Check symbols in kernel binary
    symbols_to_check = [
        b"AudioDMAController_T8150_iOS",
        b"AudioDMACLLTEscalationDetector_T8150_iOS",
        b"AudioDMAFamily",
        b"AudioDMAChannelStateMachine",
        b"AudioDMAChannelConfiguration",
        b"AudioDMATransferCommand",
        b"AudioSharedDARTMapperProxy",
        b"ADMACOPER_ProcessMoreTransfers",
        b"ADMACOPER_ProcessDone",
        b"ADMACOPER_Finish",
        b"ADMACOPER_CountOf",
        b"kAudioDMAChannelPowerStateAvailable",
        b"kAudioDMAChannelPowerStateSuspended",
        b"kAudioDMAControllerPowerStateAvailable",
        b"kAudioDMAControllerPowerStateSuspended",
        b"kAudioDMAControllerPowerStateInvalid",
        b"AppleAOPAudioMCA2Device",
        b"AppleAOPAudioPDM2Device",
        b"AppleAOPMCALoopbackAudio",
        b"MCA2RxAShimOverrun"
    ]
    for sym in symbols_to_check:
        check(sym in kernel_data, f"Symbol present in kernelcache: {sym.decode()}")

    # Check state machine state array strings in binary
    states = [b"Uninitialized", b"Ready", b"Initializing", b"Idle", b"Configure", b"Introspect", b"FirstTransfer", b"Transferring", b"Stopping", b"Complete", b"Sleeping"]
    for state in states:
        check(state in kernel_data, f"State string present: {state.decode()}")

    # Check state machine operation strings in binary
    ops = [b"SetRoleDirection", b"SetApertures", b"Initialize", b"Transfer", b"Error", b"ProcessMoreDescriptors", b"FinishDescriptors", b"Stop", b"Stopped", b"Sleep", b"Wake", b"Atomic", b"Reset", b"ClearIRQ"]
    for op in ops:
        check(op in kernel_data, f"Operation string present: {op.decode()}")

    # Check register names and bitfield macros in binary
    reg_assertions = [
        b"ReadTxChannelBlockRegisterBits(axictl.arcache) == 0x2",
        b"ReadRxChannelBlockRegisterBits(axictl.awcache) == 0x2",
        b"ReadChannelBlockRegisterBits(isTx, csfifostat.empty) == 0",
        b"ReadChannelBlockRegisterBits(isTx, pctfifostat.empty) == 0",
        b"_admaGlobalRegisterBlock->timebase1.valid == 1",
        b"AddressLow   = 0x%08x.",
        b"AddressHigh  = 0x%08x.",
        b"Length       = 0x%08x.",
        b"Misc         = 0x%08x.",
        b"TDID       = 0x%02x.",
        b"Attr       = 0x%02x."
    ]
    for assertion in reg_assertions:
        check(assertion in kernel_data, f"Register assertion/log pattern found: {assertion.decode()[:40]}...")

    print("  [OK] Kernelcache symbols and class hierarchy verified.")

def main():
    print("================================================================================")
    print("ADMAC Evolution t8150 & Multichannel Audio (MCA) Verification Harness")
    print("Apple Silicon A19 Pro / iOS 27.2")
    print("================================================================================")

    try:
        test_json_specifications()
        test_devicetree_admac_invariants()
        test_kernelcache_symbols_and_classes()

        print("\n================================================================================")
        print(f"VERIFICATION SUMMARY: ALL {passed_asserts} / {total_asserts} INVARIANTS PASSED (100% GREEN)")
        print("================================================================================")
        return 0
    except TestFailure as e:
        print(f"\n[ABORT] Verification failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected exception during verification: {e}")
        import traceback
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    sys.exit(main())
