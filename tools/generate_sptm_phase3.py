#!/usr/bin/env python3
"""
tools/generate_sptm_phase3.py — Generate SPTM Hypercall Dispatch Specification
and iBoot Research Diagnostic Commands for iOS 27.2 (24B119) / A19 Pro (t8150).
Produces:
- artifacts/sptm/sptm_hypercall_dispatch_spec.json
- artifacts/sptm/iboot_diagnostic_commands.json
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

DISPATCH_TABLES = [
    {"table_id": 0, "name": "SPTM_DISPATCH_TABLE", "entries_count": 42, "description": "Master domain dispatch lookup table resolving function ID to handler address."},
    {"table_id": 1, "name": "SPTM_DISPATCH_TABLE_XNU_BOOTSTRAP", "entries_count": 8, "description": "XNU kernel early initialization dispatch table."},
    {"table_id": 2, "name": "SPTM_DISPATCH_TABLE_TXM_BOOTSTRAP", "entries_count": 6, "description": "TXM code signing monitor bootstrap dispatch table."},
    {"table_id": 3, "name": "SPTM_DISPATCH_TABLE_SK_BOOTSTRAP", "entries_count": 12, "description": "Secure Kernel / ExclaveCore bootstrap dispatch table."},
    {"table_id": 4, "name": "SPTM_DISPATCH_TABLE_T8110_DART_XNU", "entries_count": 10, "description": "T8110 DART IOMMU controller dispatch table for XNU DMA."},
    {"table_id": 5, "name": "SPTM_DISPATCH_TABLE_T8110_DART_SK", "entries_count": 10, "description": "T8110 DART IOMMU controller dispatch table for Secure Kernel."},
    {"table_id": 6, "name": "SPTM_DISPATCH_TABLE_SART", "entries_count": 6, "description": "Secure Apple Remap Table controller dispatch table."},
    {"table_id": 7, "name": "SPTM_DISPATCH_TABLE_NVME", "entries_count": 4, "description": "NVMe controller DMA queue validation dispatch table."},
    {"table_id": 8, "name": "SPTM_DISPATCH_TABLE_UAT", "entries_count": 14, "description": "Unified Address Translation memory management dispatch table."},
    {"table_id": 9, "name": "SPTM_DISPATCH_TABLE_SHART", "entries_count": 4, "description": "Shared Hardware Address Remap Table controller dispatch table."},
    {"table_id": 10, "name": "SPTM_DISPATCH_TABLE_CPUTRACE", "entries_count": 6, "description": "Hardware CPU trace and CoreSight diagnostic dispatch table."},
    {"table_id": 11, "name": "SPTM_DISPATCH_TABLE_HIB", "entries_count": 5, "description": "System sleep and hibernation coordination dispatch table."},
    {"table_id": 12, "name": "SPTM_DISPATCH_TABLE_GEN3_DART_XNU", "entries_count": 10, "description": "Gen3 DART peripheral controller dispatch table for XNU."},
    {"table_id": 13, "name": "SPTM_DISPATCH_TABLE_GEN3_DART_SK", "entries_count": 10, "description": "Gen3 DART peripheral controller dispatch table for Secure Kernel."},
    {"table_id": 14, "name": "SPTM_DISPATCH_TABLE_T6000_DART_XNU", "entries_count": 6, "description": "Legacy T6000 DART compatibility dispatch table."},
    {"table_id": 15, "name": "SPTM_DISPATCH_TABLE_T8020_DART_XNU", "entries_count": 6, "description": "Legacy T8020 DART compatibility dispatch table."},
    {"table_id": 16, "name": "SPTM_DISPATCH_TABLE_RESERVED2", "entries_count": 2, "description": "Reserved internal hardware dispatch table."}
]

FUNCTION_IDS = {
    "SPTM_FUNCTIONID_LOCKDOWN": {"id": 0, "category": "SYSTEM_LOCKDOWN", "args": ["flags"], "returns": ["status"], "description": "Initiates monitor hardware lockdown, transitions CTRR/GAPF to read-only, and seals early boot structures."},
    "SPTM_FUNCTIONID_RETYPE": {"id": 1, "category": "MEMORY_RETYPING", "args": ["paddr", "new_type", "expected_type", "num_pages"], "returns": ["status"], "description": "Validates and executes dynamic physical frame retyping between authenticated domain types."},
    "SPTM_FUNCTIONID_MAP_PAGE": {"id": 2, "category": "PAGE_TABLE_MAPPING", "args": ["ttbr", "vaddr", "paddr", "prot_flags"], "returns": ["status"], "description": "Installs a validated Stage-1 page table entry for guest virtual addresses, preventing executable mapping without TXM authorization."},
    "SPTM_FUNCTIONID_MAP_TABLE": {"id": 3, "category": "PAGE_TABLE_MAPPING", "args": ["ttbr", "vaddr", "table_paddr", "level"], "returns": ["status"], "description": "Allocates and links an intermediate translation table level into the active guest hierarchy."},
    "SPTM_FUNCTIONID_UNMAP_TABLE": {"id": 4, "category": "PAGE_TABLE_MAPPING", "args": ["ttbr", "vaddr", "level"], "returns": ["status"], "description": "Unlinks and deallocates an intermediate page table level after flushing associated TLB cache lines."},
    "SPTM_FUNCTIONID_UPDATE_REGION": {"id": 5, "category": "REGION_MANAGEMENT", "args": ["ttbr", "vaddr", "size", "new_prot"], "returns": ["status"], "description": "Updates memory protection attributes across a contiguous virtual address range."},
    "SPTM_FUNCTIONID_UPDATE_DISJOINT": {"id": 6, "category": "REGION_MANAGEMENT", "args": ["ttbr", "descriptors_ptr", "count"], "returns": ["status"], "description": "Updates disjoint virtual memory mappings in an atomic transaction."},
    "SPTM_FUNCTIONID_UNMAP_REGION": {"id": 7, "category": "REGION_MANAGEMENT", "args": ["ttbr", "vaddr", "size"], "returns": ["status"], "description": "Unmaps a contiguous virtual memory range and clears guest page table entries."},
    "SPTM_FUNCTIONID_UNMAP_DISJOINT": {"id": 8, "category": "REGION_MANAGEMENT", "args": ["ttbr", "descriptors_ptr", "count"], "returns": ["status"], "description": "Unmaps disjoint virtual memory ranges in an atomic transaction."},
    "SPTM_FUNCTIONID_CONFIGURE_SHAREDREGION": {"id": 9, "category": "SHARED_REGION", "args": ["region_id", "vaddr", "size", "flags"], "returns": ["status"], "description": "Configures system shared region (dyld shared cache) aperture bounds."},
    "SPTM_FUNCTIONID_NEST_REGION": {"id": 10, "category": "SHARED_REGION", "args": ["parent_ttbr", "child_ttbr", "vaddr", "size"], "returns": ["status"], "description": "Nests a shared memory translation hierarchy between processes."},
    "SPTM_FUNCTIONID_UNNEST_REGION": {"id": 11, "category": "SHARED_REGION", "args": ["parent_ttbr", "child_ttbr", "vaddr", "size"], "returns": ["status"], "description": "Detaches a nested shared translation sub-tree."},
    "SPTM_FUNCTIONID_CONFIGURE_ROOT": {"id": 12, "category": "PAGE_TABLE_ROOT", "args": ["ttbr", "asid", "flags"], "returns": ["status"], "description": "Allocates and initializes a new top-level page table root descriptor."},
    "SPTM_FUNCTIONID_SWITCH_ROOT": {"id": 13, "category": "PAGE_TABLE_ROOT", "args": ["new_ttbr", "new_asid"], "returns": ["status"], "description": "Atomically switches the active task translation table root."},
    "SPTM_FUNCTIONID_REGISTER_CPU": {"id": 14, "category": "CPU_TOPOLOGY", "args": ["cpu_id", "cluster_id", "stack_paddr"], "returns": ["status"], "description": "Registers a secondary CPU core execution context with the hypervisor."},
    "SPTM_FUNCTIONID_FIXUPS_COMPLETE": {"id": 15, "category": "DYNAMIC_LINKING", "args": ["ttbr", "header_vaddr"], "returns": ["status"], "description": "Signals completion of userland dyld chained fixups and seals segments."},
    "SPTM_FUNCTIONID_SIGN_USER_POINTER": {"id": 16, "category": "PAC_MANAGEMENT", "args": ["key_type", "ptr_value", "context"], "returns": ["signed_ptr"], "description": "Generates a cryptographic pointer authentication code under hypervisor key."},
    "SPTM_FUNCTIONID_AUTH_USER_POINTER": {"id": 17, "category": "PAC_MANAGEMENT", "args": ["key_type", "signed_ptr", "context"], "returns": ["raw_ptr"], "description": "Authenticates and strips a user PAC signature."},
    "SPTM_FUNCTIONID_REGISTER_EXC_RETURN": {"id": 18, "category": "EXCEPTION_HANDLING", "args": ["vector_type", "trampoline_pc"], "returns": ["status"], "description": "Registers an exception return trampoline address for guest state restoration."},
    "SPTM_FUNCTIONID_CPU_ID": {"id": 19, "category": "CPU_TOPOLOGY", "args": [], "returns": ["cpu_id", "cluster_id"], "description": "Returns hardware CPU identifier and cluster assignment."},
    "SPTM_FUNCTIONID_SLIDE_REGION": {"id": 20, "category": "REGION_MANAGEMENT", "args": ["ttbr", "vaddr", "slide_offset"], "returns": ["status"], "description": "Applies a KASLR slide to an allocated translation sub-hierarchy."},
    "SPTM_FUNCTIONID_UPDATE_DISJOINT_MULTIPAGE": {"id": 21, "category": "REGION_MANAGEMENT", "args": ["ttbr", "multipage_desc_ptr"], "returns": ["status"], "description": "Batched multi-page attribute update routine."},
    "SPTM_FUNCTIONID_GUEST_VA_TO_IPA": {"id": 22, "category": "STAGE2_TRANSLATION", "args": ["ttbr", "vaddr"], "returns": ["ipa", "status"], "description": "Translates a guest virtual address to its corresponding intermediate physical address."},
    "SPTM_FUNCTIONID_GUEST_STAGE1_TLBOP": {"id": 23, "category": "STAGE1_TLB", "args": ["asid", "vaddr", "tlb_op"], "returns": ["status"], "description": "Broadcasts a Stage-1 TLB invalidation shootdown (TLBI ASIDE1IS)."},
    "SPTM_FUNCTIONID_GUEST_STAGE2_TLBOP": {"id": 24, "category": "STAGE2_TLB", "args": ["vmid", "ipa", "tlb_op"], "returns": ["status"], "description": "Broadcasts a Stage-2 TLB invalidation shootdown (TLBI IPAS2E1IS)."},
    "SPTM_FUNCTIONID_GUEST_DISPATCH": {"id": 25, "category": "GUEST_EXECUTION", "args": ["guest_context_ptr"], "returns": ["exit_reason"], "description": "Dispatches execution to guest OS context (XNU or Conclave)."},
    "SPTM_FUNCTIONID_GUEST_EXIT": {"id": 26, "category": "GUEST_EXECUTION", "args": ["exit_code"], "returns": ["status"], "description": "Handles synchronous exit from guest execution back to hypervisor."},
    "SPTM_FUNCTIONID_HIB_BEGIN": {"id": 27, "category": "HIBERNATION", "args": ["header_paddr", "flags"], "returns": ["status"], "description": "Initiates system hibernation image creation sequence."},
    "SPTM_FUNCTIONID_HIB_VERIFY_HASH_NON_WIRED": {"id": 28, "category": "HIBERNATION", "args": ["chunk_paddr", "expected_hash"], "returns": ["status"], "description": "Cryptographically validates non-wired page hash during wake."},
    "SPTM_FUNCTIONID_HIB_FINALIZE_NON_WIRED": {"id": 29, "category": "HIBERNATION", "args": ["flags"], "returns": ["status"], "description": "Finalizes hibernation restoration and re-engages Stage-2 tables."},
    "SPTM_FUNCTIONID_IOFILTER_PROTECTED_WRITE": {"id": 30, "category": "IO_FILTERING", "args": ["mmio_paddr", "value", "width"], "returns": ["status"], "description": "Performs guarded MMIO write to hardware registers subject to aperture checks."},
    "SPTM_FUNCTIONID_SPTM_TAG_PAPT_MULTIPAGE": {"id": 31, "category": "PAPT_MANAGEMENT", "args": ["paddr_start", "count", "domain_tag"], "returns": ["status"], "description": "Assigns security domain ownership tags across contiguous physical frames."},
    "SPTM_FUNCTIONID_SPTM_UNTAG_PAPT_MULTIPAGE": {"id": 32, "category": "PAPT_MANAGEMENT", "args": ["paddr_start", "count", "domain_tag"], "returns": ["status"], "description": "Clears security domain ownership tags across physical frames."},
    "SPTM_FUNCTIONID_SET_SHARED_REGION": {"id": 33, "category": "SHARED_REGION", "args": ["ttbr", "shared_ttbr"], "returns": ["status"], "description": "Attaches global shared region page table to process translation hierarchy."},
    "SPTM_FUNCTIONID_BATCH_SIGN_USER_POINTER": {"id": 34, "category": "PAC_MANAGEMENT", "args": ["key_type", "ptrs_buffer", "count"], "returns": ["status"], "description": "Batched hardware PAC signing for optimized process bootstrapping."},
    "SPTM_FUNCTIONID_SURT_ALLOC": {"id": 35, "category": "SURT_SUBPAGE", "args": ["subpage_id", "flags"], "returns": ["surt_handle"], "description": "Allocates Sub-Page User Root Table descriptor for fine-grained permissions."},
    "SPTM_FUNCTIONID_SURT_FREE": {"id": 36, "category": "SURT_SUBPAGE", "args": ["surt_handle"], "returns": ["status"], "description": "Deallocates Sub-Page User Root Table descriptor."},
    "SPTM_FUNCTIONID_CONDEMN_LEAF_TABLE": {"id": 37, "category": "PAGE_TABLE_LEAF", "args": ["ttbr", "vaddr"], "returns": ["status"], "description": "Condemns a leaf page table for asynchronous reclamation."},
    "SPTM_FUNCTIONID_UNCONDEMN_LEAF_TABLE": {"id": 38, "category": "PAGE_TABLE_LEAF", "args": ["ttbr", "vaddr"], "returns": ["status"], "description": "Restores a condemned leaf page table before reclamation occurs."},
    "SPTM_FUNCTIONID_SPTM_SERIAL_PUTC": {"id": 39, "category": "SERIAL_DEBUG", "args": ["character"], "returns": ["status"], "description": "Emits a raw ASCII character to the hardware serial debug UART."},
    "SPTM_FUNCTIONID_SPTM_SERIAL_DISABLE": {"id": 40, "category": "SERIAL_DEBUG", "args": [], "returns": ["status"], "description": "Permanently disables serial debug output before production lockdown."},
    "SPTM_FUNCTIONID_OUTPUT_AREA": {"id": 41, "category": "TELEMETRY_LOGGING", "args": ["buffer_paddr", "size"], "returns": ["status"], "description": "Registers output memory area for hypervisor crash and telemetry logging."}
}

IBOOT_DIAGNOSTIC_COMMANDS = {
    "reboot": {"syntax": "reboot [reason]", "handler": "0x376120", "description": "Commands PMGR power controller to perform cold or warm hardware reset."},
    "setenv": {"syntax": "setenv <var> <value>", "handler": "0x380940", "description": "Sets volatile or NVRAM boot environment variable."},
    "getenv": {"syntax": "getenv <var>", "handler": "0x3809c0", "description": "Retrieves current value of boot environment variable."},
    "saveenv": {"syntax": "saveenv", "handler": "0x380a40", "description": "Flushes volatile environment variable modifications to non-volatile storage."},
    "reset": {"syntax": "reset", "handler": "0x376180", "description": "Initiates CPU pipeline reset and warm reboot."},
    "nvram": {"syntax": "nvram <get|set|dump>", "handler": "0x381200", "description": "Direct low-level NVRAM dictionary inspection and manipulation."},
    "devicetree": {"syntax": "devicetree <dump|find|set>", "handler": "0x374e00", "description": "Inspects or dynamically patches embedded DeviceTree node properties."},
    "fsboot": {"syntax": "fsboot <path>", "handler": "0x378400", "description": "Loads and boots signed bootloader or kernel image from local filesystem."},
    "usb": {"syntax": "usb <start|stop|status>", "handler": "0x390100", "description": "Initializes or interrogates USB Type-C / DFU communication controller."},
    "go": {"syntax": "go <address>", "handler": "0x378900", "description": "Transfers bare-metal execution control to designated memory address."},
    "pmgr": {"syntax": "pmgr <clk|volt|tunables>", "handler": "0x376500", "description": "Power Manager static tunables and clock mesh diagnostics."},
    "memory": {"syntax": "memory <dump|test|map>", "handler": "0x375100", "description": "DRAM physical memory integrity test and range dumper."},
    "stage2_dump": {"syntax": "stage2_dump <vmid>", "handler": "0x382400", "description": "Research diagnostic: dumps Stage-2 translation descriptors for designated VMID."}
}

BOOT_ARGUMENTS = [
    {"flag": "-v", "type": "BOOLEAN", "description": "Verbose console logging during boot."},
    {"flag": "debug=0x14e", "type": "BITFIELD", "description": "Kernel debugger control mask (DB_PRT | DB_SLT | DB_NMI | DB_HALT)."},
    {"flag": "cs_enforcement_disable=1", "type": "BOOLEAN", "description": "Disables AMFI userland code signing enforcement on research builds."},
    {"flag": "alt.kc=<path>", "type": "STRING", "description": "Overrides default kernelcache path with alternate research image."},
    {"flag": "alt.sptm=<path>", "type": "STRING", "description": "Overrides default SPTM firmware with alternate research monitor."},
    {"flag": "alt.txm=<path>", "type": "STRING", "description": "Overrides default TXM firmware with alternate research monitor."},
    {"flag": "no-ctrr", "type": "BOOLEAN", "description": "Disables hardware Configurable Text Region Register write-locking."},
    {"flag": "no-ktrr", "type": "BOOLEAN", "description": "Disables hardware Kernel Text Read-Only Region locking."},
    {"flag": "kaslr-off", "type": "BOOLEAN", "description": "Disables Kernel Address Space Layout Randomization (sets slide to 0)."},
    {"flag": "kaslr-slide=<offset>", "type": "HEX_VALUE", "description": "Forces explicit KASLR slide offset during kernel initialization."},
    {"flag": "force-research-policy", "type": "BOOLEAN", "description": "Forces TXM and AMFI to evaluate research execution policy entitlements."},
    {"flag": "debug-uarts=1", "type": "INTEGER", "description": "Redirects early boot and monitor diagnostic messages to serial UART."},
    {"flag": "apt-carveout-size-mb=<size>", "type": "INTEGER", "description": "Configures dynamic physical DRAM carveout for Apple Processing Targets."}
]

def main():
    print("[+] Generating sptm_hypercall_dispatch_spec.json...")
    dispatch_spec = {
        "schema_version": "1.0",
        "component": "SPTM Hypercall Dispatch Specification",
        "calling_convention": {
            "entry_mechanism": "Synchronous Hypercall Trap (hvc #0 / gxf_enter)",
            "vector_slot": "Slot 8 (__TEXT_EXEC.__exc + 0x400 @ 0xfffffff027118400)",
            "trap_handler_pc": "0xfffffff0270b7ca4",
            "argument_registers": {
                "x0": "SPTM Function ID (0 to 41)",
                "x1": "Parameter 1 (e.g. Page Table TTBR / Physical Address)",
                "x2": "Parameter 2 (e.g. Virtual Address / New Frame Type)",
                "x3": "Parameter 3 (e.g. Protection Flags / Length / Domain)",
                "x4": "Parameter 4 (e.g. Expected Frame Type / Extended Flags)",
                "x5": "Parameter 5 (e.g. Reference Counter / Subpage ID)",
                "x6": "Parameter 6 (e.g. Transaction Context Descriptor)"
            },
            "return_registers": {
                "x0": "Status Code (0 = SPTM_SUCCESS, non-zero = error)",
                "x1": "Output Data 1 (e.g. Translated IPA or Signed Pointer)",
                "x2": "Output Data 2 (e.g. Resolved Cluster / Core ID)",
                "x3": "Output Data 3 (e.g. Exit Reason / State)"
            },
            "callee_preserved_registers": ["x19", "x20", "x21", "x22", "x23", "x24", "x25", "x26", "x27", "x28", "x29", "sp"]
        },
        "dispatch_tables": DISPATCH_TABLES,
        "function_ids": FUNCTION_IDS
    }
    
    out_dispatch = ROOT / "artifacts/sptm/sptm_hypercall_dispatch_spec.json"
    out_dispatch.write_text(json.dumps(dispatch_spec, indent=2))
    print(f"[+] Wrote {out_dispatch}")
    
    print("[+] Generating iboot_diagnostic_commands.json...")
    iboot_spec = {
        "schema_version": "1.0",
        "component": "iBoot / LLB Research Release Diagnostic Commands & Boot Arguments",
        "bootloader_build": "mBoot-20457.42.5 (RESEARCH_RELEASE)",
        "diagnostic_shell": {
            "prompt": "iBoot:v57>",
            "line_editor": "VT100 serial terminal with command history buffer",
            "command_delimiter": "Semicolon or newline",
            "max_command_length_bytes": 512
        },
        "diagnostic_commands": IBOOT_DIAGNOSTIC_COMMANDS,
        "boot_arguments": BOOT_ARGUMENTS
    }
    
    out_iboot = ROOT / "artifacts/sptm/iboot_diagnostic_commands.json"
    out_iboot.write_text(json.dumps(iboot_spec, indent=2))
    print(f"[+] Wrote {out_iboot}")

if __name__ == "__main__":
    main()
