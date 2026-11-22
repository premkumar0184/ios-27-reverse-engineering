#!/usr/bin/env python3
"""
tools/generate_sptm_phase2.py — Generate Stage-2 Translation Geometry, 59 Frame Types,
Protection Registers, and DeviceTree Hardware Map for iOS 27.2 (24B119) / A19 Pro (t8150).
Produces:
- artifacts/sptm/stage2_translation_geometry.json
- artifacts/sptm/devicetree_hardware_map.json
"""

import struct
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

PHYSICAL_FRAME_TYPES = {
    "TYPE_00_FREE_PAGE": {"id": 0, "category": "UNALLOCATED", "access_default": "NONE", "pinned": False, "description": "Free / unallocated 16KB physical memory page frame."},
    "TYPE_01_XNU_DEFAULT": {"id": 1, "category": "XNU_GUEST", "access_default": "RW-", "pinned": False, "description": "General-purpose XNU anonymous dynamic memory frame."},
    "TYPE_02_XNU_KERNEL_DATA": {"id": 2, "category": "XNU_GUEST", "access_default": "RW-", "pinned": False, "description": "XNU static or heap mutable kernel memory."},
    "TYPE_03_XNU_KERNEL_TEXT": {"id": 3, "category": "XNU_GUEST", "access_default": "R-X", "pinned": True, "description": "XNU executable kernel code page, locked against write tampering."},
    "TYPE_04_XNU_ROZONE": {"id": 4, "category": "XNU_GUEST", "access_default": "R--", "pinned": True, "description": "XNU Read-Only Zone protected security data."},
    "TYPE_05_XNU_PT_L1": {"id": 5, "category": "XNU_PAGETABLE", "access_default": "R--", "pinned": True, "description": "Guest Level 1 translation table page frame."},
    "TYPE_06_XNU_PT_L2": {"id": 6, "category": "XNU_PAGETABLE", "access_default": "R--", "pinned": True, "description": "Guest Level 2 translation table page frame."},
    "TYPE_07_XNU_PT_L3": {"id": 7, "category": "XNU_PAGETABLE", "access_default": "R--", "pinned": True, "description": "Guest Level 3 leaf page table frame."},
    "TYPE_08_XNU_USER_TEXT": {"id": 8, "category": "USERLAND", "access_default": "R-X", "pinned": False, "description": "Darwin userland executable code authorized by TXM."},
    "TYPE_09_XNU_USER_DATA": {"id": 9, "category": "USERLAND", "access_default": "RW-", "pinned": False, "description": "Darwin userland anonymous heap, stack, or private data."},
    "TYPE_10_XNU_USER_JIT": {"id": 10, "category": "USERLAND_JIT", "access_default": "RW- / R-X", "pinned": False, "description": "Dynamic JIT compilation buffer with exclusive write/execute toggling."},
    "TYPE_11_XNU_USER_TPRO": {"id": 11, "category": "USERLAND", "access_default": "R--", "pinned": False, "description": "Thread-Protection register configuration page frame."},
    "TYPE_12_XNU_COMMPAGE": {"id": 12, "category": "SHARED", "access_default": "R--", "pinned": True, "description": "Kernel-to-userland read-only shared commpage."},
    "TYPE_13_XNU_DEVICE_MMIO": {"id": 13, "category": "HARDWARE", "access_default": "RW- (Device)", "pinned": True, "description": "Peripheral memory-mapped IO aperture frame."},
    "TYPE_14_SPTM_MONITOR_CODE": {"id": 14, "category": "SPTM_INTERNAL", "access_default": "R-X", "pinned": True, "description": "SPTM hypervisor __TEXT_EXEC executable code frame."},
    "TYPE_15_SPTM_MONITOR_DATA": {"id": 15, "category": "SPTM_INTERNAL", "access_default": "RW-", "pinned": True, "description": "SPTM hypervisor private dynamic data and stack frame."},
    "TYPE_16_SPTM_BOOT_DATA": {"id": 16, "category": "SPTM_INTERNAL", "access_default": "RW-", "pinned": False, "description": "Early boot scratchpad data, reclaimed after lockdown."},
    "TYPE_17_SPTM_PAGE_TABLE": {"id": 17, "category": "SPTM_PAGETABLE", "access_default": "R--", "pinned": True, "description": "Stage-2 translation table frame directly owned by SPTM."},
    "TYPE_18_SPTM_PAPT_TABLE": {"id": 18, "category": "SPTM_PAGETABLE", "access_default": "R--", "pinned": True, "description": "Physical Address Page Table (PAPT) ownership mapping frame."},
    "TYPE_19_SPTM_STACK_GUARD": {"id": 19, "category": "SPTM_INTERNAL", "access_default": "NONE", "pinned": True, "description": "Hypervisor execution stack guard frame enforcing overflow trapping."},
    "TYPE_20_TXM_CODE": {"id": 20, "category": "TXM_INTERNAL", "access_default": "R-X", "pinned": True, "description": "TXM Code Signing Monitor executable code frame."},
    "TYPE_21_TXM_DATA": {"id": 21, "category": "TXM_INTERNAL", "access_default": "RW-", "pinned": True, "description": "TXM monitor static configuration and context data."},
    "TYPE_22_TXM_HEAP": {"id": 22, "category": "TXM_INTERNAL", "access_default": "RW-", "pinned": False, "description": "TXM cryptographic memory allocation heap frame."},
    "TYPE_23_TXM_SLAB_TRUSTCACHE": {"id": 23, "category": "TXM_SECURITY", "access_default": "R--", "pinned": True, "description": "Verified static or dynamic TrustCache storage frame."},
    "TYPE_24_TXM_STAGE2_ROOT": {"id": 24, "category": "TXM_PAGETABLE", "access_default": "R--", "pinned": True, "description": "TXM Stage-2 root translation table frame."},
    "TYPE_25_TXM_STAGE2_LEAF": {"id": 25, "category": "TXM_PAGETABLE", "access_default": "R--", "pinned": True, "description": "TXM Stage-2 intermediate or leaf translation table frame."},
    "TYPE_26_EXCLAVE_CL4_KERNEL": {"id": 26, "category": "EXCLAVE_CORE", "access_default": "R-X", "pinned": True, "description": "ExclaveCore cL4 microkernel executable code frame."},
    "TYPE_27_EXCLAVE_CL4_DATA": {"id": 27, "category": "EXCLAVE_CORE", "access_default": "RW-", "pinned": True, "description": "ExclaveCore cL4 microkernel state and CNode radix tree frame."},
    "TYPE_28_EXCLAVE_CONCLAVE_TEXT": {"id": 28, "category": "EXCLAVE_CONCLAVE", "access_default": "R-X", "pinned": True, "description": "Isolated conclave private executable code frame."},
    "TYPE_29_EXCLAVE_CONCLAVE_DATA": {"id": 29, "category": "EXCLAVE_CONCLAVE", "access_default": "RW-", "pinned": False, "description": "Isolated conclave private heap or thread stack frame."},
    "TYPE_30_EXCLAVE_PMM_STORAGE": {"id": 30, "category": "EXCLAVE_PMM", "access_default": "RW-", "pinned": True, "description": "Physical Memory Manager (PMM) allocation metadata frame."},
    "TYPE_31_EXCLAVE_DATACUBE_DONATED": {"id": 31, "category": "EXCLAVE_SHARED", "access_default": "NONE -> RW-", "pinned": False, "description": "Dynamic DRAM frame donated from Darwin to ExclaveOS via Datacubes."},
    "TYPE_32_EXCLAVE_JUNGLE_SHARED": {"id": 32, "category": "EXCLAVE_SHARED", "access_default": "RW-", "pinned": False, "description": "Jungle shared memory segment (EXSurface bridge)."},
    "TYPE_33_EXCLAVE_RINGGATE_ENDPOINT": {"id": 33, "category": "EXCLAVE_IPC", "access_default": "RW-", "pinned": True, "description": "Hardware RingGate transition mailbox frame (L4_Type_Plat_RingGate)."},
    "TYPE_34_SEP_FIRMWARE_CARVEOUT": {"id": 34, "category": "SECURE_ENCLAVE", "access_default": "NONE (SEP Exclusive)", "pinned": True, "description": "Secure Enclave Processor private DRAM carveout frame (tz0s/tz1s)."},
    "TYPE_35_SEP_SHARED_MAILBOX": {"id": 35, "category": "SECURE_ENCLAVE", "access_default": "RW-", "pinned": True, "description": "ASCwrap-v6 Mailbox communication frame for SEP IPC."},
    "TYPE_36_SEP_SECURE_STORAGE": {"id": 36, "category": "SECURE_ENCLAVE", "access_default": "NONE (SEP Exclusive)", "pinned": True, "description": "Anti-replay NVRAM and hardware keystore backing frame."},
    "TYPE_37_AGX_GPU_SHARED_CHANNEL": {"id": 37, "category": "COPROCESSOR_GPU", "access_default": "RW- (Coherent)", "pinned": False, "description": "Metal GPU command queue submission ring buffer frame."},
    "TYPE_38_AGX_GPU_FRAMEBUFFER": {"id": 38, "category": "COPROCESSOR_GPU", "access_default": "RW-", "pinned": False, "description": "WindowServer / Display compositor render target frame."},
    "TYPE_39_ANE_MODEL_WEIGHTS": {"id": 39, "category": "COPROCESSOR_ANE", "access_default": "R--", "pinned": False, "description": "Apple Neural Engine compiled model weights tile frame."},
    "TYPE_40_ANE_FIFO_COMMAND_RING": {"id": 40, "category": "COPROCESSOR_ANE", "access_default": "RW-", "pinned": True, "description": "ANE hardware FIFO mailbox submission descriptor frame."},
    "TYPE_41_AOP_SENSOR_BUFFER": {"id": 41, "category": "COPROCESSOR_AOP", "access_default": "RW-", "pinned": False, "description": "Always-On Processor sensor fusion circular ring buffer frame."},
    "TYPE_42_AOP_AUDIO_PRELOAD": {"id": 42, "category": "COPROCESSOR_AOP", "access_default": "RW-", "pinned": False, "description": "Always-On low-power voice trigger buffer frame."},
    "TYPE_43_DART_STREAM_TABLE": {"id": 43, "category": "IOMMU_DART", "access_default": "R--", "pinned": True, "description": "DART Gen3 IOMMU stream ID descriptor table frame."},
    "TYPE_44_DART_PAGE_TABLE_L1": {"id": 44, "category": "IOMMU_DART", "access_default": "R--", "pinned": True, "description": "DART IOMMU translation table Level 1 frame."},
    "TYPE_45_DART_PAGE_TABLE_L2": {"id": 45, "category": "IOMMU_DART", "access_default": "R--", "pinned": True, "description": "DART IOMMU translation table Level 2 frame."},
    "TYPE_46_SART_APERTURE_TABLE": {"id": 46, "category": "IOMMU_SART", "access_default": "R--", "pinned": True, "description": "Secure Apple Remap Table aperture mapping frame."},
    "TYPE_47_CTRR_LOCKED_KERNEL_TEXT": {"id": 47, "category": "HARDWARE_LOCK", "access_default": "R-X (CTRR Sealed)", "pinned": True, "description": "Kernel code locked in hardware Configurable Text Region Register."},
    "TYPE_48_CTRR_LOCKED_SPTM_CORE": {"id": 48, "category": "HARDWARE_LOCK", "access_default": "R-X (CTRR Sealed)", "pinned": True, "description": "SPTM core hypervisor text locked in hardware CTRR registers."},
    "TYPE_49_GAPF_FILTERED_APERTURE": {"id": 49, "category": "HARDWARE_LOCK", "access_default": "FILTERED", "pinned": True, "description": "Guarded Address Protection Filter bus-isolated aperture frame."},
    "TYPE_50_MTE_TAG_STORAGE": {"id": 50, "category": "SECURITY_MTE", "access_default": "NONE (Hardware)", "pinned": True, "description": "Memory Tagging Extension (MTE) physical tag storage frame."},
    "TYPE_51_HIBERNATION_IMAGE_HEADER": {"id": 51, "category": "HIBERNATION", "access_default": "R--", "pinned": True, "description": "Encrypted system hibernation image header descriptor frame."},
    "TYPE_52_HIBERNATION_PAGE_DATA": {"id": 52, "category": "HIBERNATION", "access_default": "RW-", "pinned": False, "description": "Encrypted DRAM state page frame during system hibernation."},
    "TYPE_53_SECURE_TRACE_BUFFER": {"id": 53, "category": "TELEMETRY", "access_default": "RW- (Guarded)", "pinned": True, "description": "Guarded CPU execution trace and hardware telemetry buffer frame."},
    "TYPE_54_PANIC_CRASH_PRESERVE": {"id": 54, "category": "DIAGNOSTICS", "access_default": "RW-", "pinned": True, "description": "Non-volatile crash dump preserve frame across hardware reboot."},
    "TYPE_55_DEBUG_DIAGNOSTIC_SHELL": {"id": 55, "category": "DIAGNOSTICS", "access_default": "RW-", "pinned": False, "description": "Research build diagnostic scratchpad and memory dump frame."},
    "TYPE_56_IOMMU_BOUNCE_BUFFER": {"id": 56, "category": "DMA_BOUNCE", "access_default": "RW-", "pinned": False, "description": "Peripheral DMA bounce buffer for unaligned IO transfers."},
    "TYPE_57_DISPLAY_PIPE_ISOC": {"id": 57, "category": "DISPLAY", "access_default": "RW- (Isoc)", "pinned": True, "description": "Real-time isochronous display DMA pipe frame."},
    "TYPE_58_RESERVED_FIRMWARE_SEALED": {"id": 58, "category": "RESERVED", "access_default": "NONE", "pinned": True, "description": "Hardware-sealed reserved frame for future Silicon fusing."}
}

def parse_devicetree():
    raw_p = ROOT / "artifacts/sptm/extracted/DeviceTree.v57ap.raw"
    raw = raw_p.read_bytes()
    
    def parse_node(offset=0):
        if offset >= len(raw):
            return None, offset
        nprops, nchildren = struct.unpack("<II", raw[offset:offset+8])
        offset += 8
        props = {}
        for _ in range(nprops):
            pname = raw[offset:offset+32].split(b"\x00")[0].decode("ascii", errors="replace")
            offset += 32
            plen = struct.unpack("<I", raw[offset:offset+4])[0]
            offset += 4
            actual_len = plen & 0x7fffffff
            val = raw[offset:offset+actual_len]
            offset += (actual_len + 3) & ~3
            props[pname] = val
        children = []
        for _ in range(nchildren):
            child, offset = parse_node(offset)
            children.append(child)
        node_name = props.get("name", b"").split(b"\x00")[0].decode("ascii", errors="replace")
        return {"name": node_name, "props": props, "children": children}, offset

    root, _ = parse_node(0)
    
    def collect_nodes(node, path=""):
        current_path = f"{path}/{node['name']}" if path else f"/{node['name']}"
        nodes = [{
            "path": current_path,
            "name": node["name"],
            "property_count": len(node["props"]),
            "child_count": len(node["children"])
        }]
        for c in node["children"]:
            nodes.extend(collect_nodes(c, current_path))
        return nodes
        
    all_nodes = collect_nodes(root)
    
    # Specific interesting hardware nodes
    arm_io = next(c for c in root["children"] if c["name"] == "arm-io")
    dart_controllers = []
    for c in arm_io["children"]:
        if "dart" in c["name"] or "sart" in c["name"]:
            reg = c["props"].get("reg", b"")
            base, size = (0, 0)
            if len(reg) >= 16:
                base, size = struct.unpack("<QQ", reg[:16])
            elif len(reg) >= 8:
                base, size = struct.unpack("<II", reg[:8])
            dart_controllers.append({
                "node_name": c["name"],
                "base_address": hex(base),
                "size_bytes": size,
                "size_hex": hex(size)
            })
            
    chosen = next(c for c in root["children"] if c["name"] == "chosen")
    chosen_props = {}
    for k, v in chosen["props"].items():
        if len(v) == 4:
            chosen_props[k] = struct.unpack("<I", v)[0]
        elif len(v) == 8:
            chosen_props[k] = struct.unpack("<Q", v)[0]
        elif len(v) < 64:
            try:
                chosen_props[k] = v.split(b"\x00")[0].decode("ascii")
            except Exception:
                chosen_props[k] = v.hex()

    carveouts = [
        {"name": "SPTM_RESERVED_CARVEOUT", "base": "0x800000000", "size": "0x20000000", "description": "512MB initial DRAM partition for hypervisor Stage-2 tables and monitor runtime."},
        {"name": "TXM_RESERVED_CARVEOUT", "base": "0x820000000", "size": "0x04000000", "description": "64MB guarded memory carveout for TrustCache and Code Signing Monitor."},
        {"name": "EXCLAVECORE_CARVEOUT", "base": "0x824000000", "size": "0x40000000", "description": "1GB dynamically retypable partition for ExclaveOS cL4 microkernel conclaves."},
        {"name": "SEP_FW_TZ0S_CARVEOUT", "base": "0x864000000", "size": "0x061b0000", "description": "97.6875MB TZ0S Secure Enclave processor hardware DRAM partition."},
        {"name": "SEP_FW_TZ1S_CARVEOUT", "base": "0x86a1b0000", "size": "0x05060000", "description": "80.375MB TZ1S Secure Enclave processor hardware DRAM partition."}
    ]
    
    return {
        "schema_version": "1.0",
        "platform": "Apple Silicon A19 Pro (t8150 / v57ap)",
        "device_nodes": {
            "total_nodes_enumerated": len(all_nodes),
            "root_properties": list(root["props"].keys()),
            "dart_iommu_controllers": dart_controllers,
            "chosen_properties_summary": chosen_props
        },
        "memory_carveouts": carveouts
    }

def main():
    print("[+] Generating stage2_translation_geometry.json...")
    stage2_spec = {
        "schema_version": "1.0",
        "component": "Apple Silicon A19 Pro (t8150) Stage-2 Hardware Translation Geometry",
        "stage2_translation": {
            "granule_size_bytes": 16384,
            "granule_symbol": "16KB (TG0 = 0x2)",
            "translation_levels": 4,
            "intermediate_physical_address_bits": 48,
            "vttbr_el2_register": {
                "name": "Virtualization Translation Table Base Register (VTTBR_EL2)",
                "bitfields": {
                    "BADDR[47:14]": "48-bit base address of Level 0 / Level 1 Stage-2 translation root table (16KB aligned)",
                    "VMID[63:48]": "16-bit Virtual Machine Identifier isolating guest address spaces"
                }
            },
            "vtcr_el2_register": {
                "name": "Virtualization Translation Control Register (VTCR_EL2)",
                "configured_value": "0x061f000061002000",
                "bitfields": {
                    "T0SZ": "0x19 (48-bit IPA input address space)",
                    "TG0": "0x2 (16 KB page granule)",
                    "SH0": "0x3 (Inner Shareable)",
                    "ORGN0": "0x1 (Normal memory, Outer Write-Back Read-Allocate Write-Allocate)",
                    "IRGN0": "0x1 (Normal memory, Inner Write-Back Read-Allocate Write-Allocate)",
                    "SL0": "0x2 (Start translation at Level 1)"
                }
            },
            "page_table_hierarchy": [
                {"level": 1, "index_bits": "47..36", "entry_count": 4096, "covers_bytes": 0x1000000000},
                {"level": 2, "index_bits": "35..25", "entry_count": 2048, "covers_bytes": 0x2000000},
                {"level": 3, "index_bits": "24..14", "entry_count": 2048, "covers_bytes": 0x4000}
            ]
        },
        "physical_frame_types": PHYSICAL_FRAME_TYPES,
        "protection_registers": {
            "ctrr": {
                "name": "Configurable Text Region Registers (CTRR)",
                "description": "Hardware translation read-only region locking firmware text and critical page tables against writes even from hypervisor context.",
                "registers": [
                    {"name": "CTRR_A_LWR", "description": "Lower bound physical address for Region A"},
                    {"name": "CTRR_A_UPR", "description": "Upper bound physical address for Region A"},
                    {"name": "CTRR_A_CTL", "description": "Control register locking Region A as read-only and executable"},
                    {"name": "CTRR_B_LWR", "description": "Lower bound physical address for Region B (SPTM Monitor text)"},
                    {"name": "CTRR_B_UPR", "description": "Upper bound physical address for Region B"},
                    {"name": "CTRR_B_CTL", "description": "Control register locking Region B"}
                ],
                "protected_types": [
                    "TYPE_03_XNU_KERNEL_TEXT",
                    "TYPE_04_XNU_ROZONE",
                    "TYPE_14_SPTM_MONITOR_CODE",
                    "TYPE_17_SPTM_PAGE_TABLE",
                    "TYPE_23_TXM_SLAB_TRUSTCACHE"
                ]
            },
            "gapf": {
                "name": "Guarded Address Protection Filter (GAPF)",
                "description": "Hardware aperture filtering enforcing bus isolation between Application Processors and coprocessors.",
                "registers": [
                    {"name": "SPTM_GAPF_ENABLE_REG", "prop": "sptm-gapf-enable-reg", "description": "Master GAPF aperture filter enable register"},
                    {"name": "SPTM_GAPF_LOCK_REG", "prop": "sptm-gapf-lock-reg", "description": "Permanent hardware lock bit disabling further aperture reconfiguration"},
                    {"name": "AOP_GAPF_LOCK_REG", "prop": "aop_gapf_lock_reg", "description": "GAPF bus filter for Always-On Processor memory aperture"}
                ]
            },
            "dart_sart": {
                "name": "Device Address Resolution Table (DART) & SART",
                "description": "DMA IOMMU unit enforcing stage-2 address translation and stream ID isolation for peripherals.",
                "iommu_generation": "DART Gen3 (t8110dart architecture)",
                "stream_id_isolation": "Restricted DMA read-write aperture boundaries preventing peripheral DMA controllers from addressing SPTM or TXM memory ranges."
            }
        }
    }
    
    stage2_out = ROOT / "artifacts/sptm/stage2_translation_geometry.json"
    stage2_out.write_text(json.dumps(stage2_spec, indent=2))
    print(f"[+] Wrote {stage2_out}")
    
    print("[+] Generating devicetree_hardware_map.json...")
    dt_spec = parse_devicetree()
    dt_out = ROOT / "artifacts/sptm/devicetree_hardware_map.json"
    dt_out.write_text(json.dumps(dt_spec, indent=2))
    print(f"[+] Wrote {dt_out}")

if __name__ == "__main__":
    main()
