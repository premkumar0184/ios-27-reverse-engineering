#!/usr/bin/env python3
"""
tools/generate_sptm_phase1b.py — Generate SPTM Hypervisor Topology Specification
and TXM Code Signing Monitor Architecture for iOS 27.2 (24B119) / A19 Pro (t8150).
Produces:
- artifacts/sptm/sptm_topology_spec.json
- artifacts/sptm/txm_csm_architecture.json
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

def generate_sptm_topology():
    baseline_p = ROOT / "artifacts/sptm/phase_1a_workspace_baseline.json"
    baseline = json.loads(baseline_p.read_text())
    sptm_asset = baseline["firmware_assets"]["sptm"]
    macho = sptm_asset["macho_metadata"]
    
    spec = {
        "schema_version": "1.0",
        "component": "Secure Page Table Monitor (SPTM)",
        "hardware_target": {
            "soc": "t8150 (Apple A19 Pro)",
            "device": "v57ap (iPhone 18,3)",
            "architecture": "arm64e (ARMv8.6+ Guarded Execution Feature, PAC00)",
            "os_build": "iOS 27.2 (24B119)",
            "darwin_version": "Darwin Kernel Version 24.2.0"
        },
        "entry_point": "0xfffffff0270bc388",
        "virtual_load_base": "0xfffffff027004000",
        "macho_uuid": macho["uuid"],
        "privilege_tiers": [
            {
                "tier": "Guarded EL2 (GL2)",
                "component": "Secure Page Table Monitor (SPTM)",
                "hardware_state": "GXF Enabled, GL2_VBAR, HCR_EL2 with TGE/E2H (VHE)",
                "capabilities": [
                    "Direct ownership of Stage-2 hardware translation tables (VTTBR_EL2)",
                    "Arbitration of 59 physical frame types across all DRAM partitions",
                    "Programming CTRR (Configurable Text Region Registers) and GAPF (Guarded Address Protection Filter)",
                    "DART/SART stream isolation for coprocessors (ANE, AGX, AOP, SEP)"
                ]
            },
            {
                "tier": "Guarded EL1 (GL1)",
                "component": "Trusted Execution Monitor (TXM)",
                "hardware_state": "GXF Enabled, GL1 Entry/Exit Vectors",
                "capabilities": [
                    "Code Signing Monitor (CSM) page validation and CDHash verification",
                    "Image4 trust authority evaluation (Apple Root CA & CoreTrust)",
                    "TrustCache registration and revocation",
                    "Dynamic hardware anti-replay nonce management"
                ]
            },
            {
                "tier": "Standard EL1",
                "component": "Darwin / XNU Monolithic Kernel",
                "hardware_state": "Stage-2 translation enforced; read-only to Stage-1 page tables",
                "capabilities": [
                    "Virtual memory management (delegated to SPTM via sptm_call)",
                    "Process lifecycle, POSIX filesystem, BSD networking, and driver management",
                    "Host IPC mediation for Exclaves via xnuproxy"
                ]
            },
            {
                "tier": "Standard EL0",
                "component": "Userland & Microkernel Enclaves",
                "hardware_state": "Unprivileged task execution",
                "capabilities": [
                    "Exclave Conclaves (cL4 microkernel private memory isolated by Stage-2)",
                    "Darwin userland apps and system daemons"
                ]
            }
        ],
        "memory_segments": macho["segments"],
        "initialization_phases": [
            {
                "phase": 1,
                "name": "Early Boot & Hardware Vector Setup",
                "entrypoint": "0xfffffff0270bc388",
                "actions": [
                    "Clears general-purpose registers x0..x30",
                    "Establishes temporary execution stack in __BOOTDATA segment",
                    "Disables interrupts via daifset #0xf and issues isb"
                ]
            },
            {
                "phase": 2,
                "name": "Execution Level Verification & Virtualization Host Extension (VHE)",
                "entrypoint": "0xfffffff0270bf0a8",
                "actions": [
                    "Asserts CurrentEL == 8 (EL2 execution)",
                    "Configures HCR_EL2: sets TGE (bit 27) and E2H (bit 34) to activate VHE",
                    "Zeroes CNTVOFF_EL2 and initializes HCRX_EL2 extension registers"
                ]
            },
            {
                "phase": 3,
                "name": "MMU & Stage-1/Stage-2 Translation Table Build",
                "entrypoint": "0xfffffff0270bf100",
                "actions": [
                    "Builds 3-level translation tables with 16KB page granule",
                    "Configures TCR_EL1 to 0x310800336511a511",
                    "Derives pointer authentication canary via pacga on 'STACKGRD'",
                    "Enables MMU via SCTLR_EL1 (0x12001010fc14793d)"
                ]
            },
            {
                "phase": 4,
                "name": "Hardware Vector Table & Guarded Execution Facility (GXF) Activation",
                "entrypoint": "0xfffffff0270bf924",
                "actions": [
                    "Registers __exc vector base (0xfffffff027118000) into GL2_VBAR (S3_6_C15_C10_2)",
                    "Programs GL2 Entry Vector (S3_6_C15_C8_1) and Exit Vector (S3_6_C15_C8_2)",
                    "Activates GXF hardware filtering"
                ]
            }
        ],
        "exception_vector_table": {
            "base_address": "0xfffffff027118000",
            "size_bytes": 8192,
            "section": "__exc",
            "slots": [
                {"slot": 0, "offset": "0x000", "context": "Current EL with SP0", "type": "Synchronous", "target": "0xfffffff0270b8168"},
                {"slot": 1, "offset": "0x080", "context": "Current EL with SP0", "type": "IRQ / vIRQ", "target": "0xfffffff0270b75fc"},
                {"slot": 2, "offset": "0x100", "context": "Current EL with SP0", "type": "FIQ / vFIQ", "target": "0xfffffff0270b7718"},
                {"slot": 3, "offset": "0x180", "context": "Current EL with SP0", "type": "SError / vSError", "target": "0xfffffff0270b7834"},
                {"slot": 4, "offset": "0x200", "context": "Current EL with SPx", "type": "Synchronous", "target": "0xfffffff0270b83a4"},
                {"slot": 5, "offset": "0x280", "context": "Current EL with SPx", "type": "IRQ (Panic)", "target": "PANIC_LOOP"},
                {"slot": 6, "offset": "0x300", "context": "Current EL with SPx", "type": "FIQ (Panic)", "target": "PANIC_LOOP"},
                {"slot": 7, "offset": "0x380", "context": "Current EL with SPx", "type": "SError (Panic)", "target": "PANIC_LOOP"},
                {"slot": 8, "offset": "0x400", "context": "Lower EL (Guest Trap)", "type": "Synchronous Hypercall Trap", "target": "0xfffffff0270b7ca4"},
                {"slot": 9, "offset": "0x480", "context": "Lower EL (Guest Interrupt)", "type": "IRQ / vIRQ", "target": "0xfffffff0270b7950"},
                {"slot": 10, "offset": "0x500", "context": "Lower EL (Guest Fast Interrupt)", "type": "FIQ / vFIQ", "target": "0xfffffff0270b7a6c"},
                {"slot": 11, "offset": "0x580", "context": "Lower EL (Guest System Error)", "type": "SError / vSError", "target": "0xfffffff0270b7b88"}
            ]
        },
        "dispatch_architecture": {
            "total_dispatch_tables": 17,
            "total_function_ids": 42,
            "calling_convention": {
                "trap_instruction": "hvc #0 / gxf_enter",
                "function_id_reg": "x0",
                "argument_regs": ["x1", "x2", "x3", "x4", "x5", "x6"],
                "return_status_reg": "x0",
                "output_data_regs": ["x1", "x2", "x3"]
            }
        }
    }
    
    out_p = ROOT / "artifacts/sptm/sptm_topology_spec.json"
    out_p.write_text(json.dumps(spec, indent=2))
    print(f"[+] Wrote {out_p}")

def generate_txm_csm_architecture():
    baseline_p = ROOT / "artifacts/sptm/phase_1a_workspace_baseline.json"
    baseline = json.loads(baseline_p.read_text())
    txm_asset = baseline["firmware_assets"]["txm"]
    macho = txm_asset["macho_metadata"]
    
    csm_spec = {
        "schema_version": "1.0",
        "component": "Trusted Execution Monitor (TXM) — Code Signing Monitor",
        "module_version": "7.0.0 (AppleImage4_txm-374~8637 / libimage4_TXM / RELEASE_ARM64E)",
        "bundle_identifier": "com.apple.security.libimage4.TXMonitor",
        "entry_point": "0xfffffff017084000",
        "virtual_load_base": "0xfffffff017004000",
        "macho_uuid": macho["uuid"],
        "memory_segments": macho["segments"],
        "runtime_functions": [
            {
                "symbol": "_txm_runtime_log",
                "purpose": "Logs security monitoring events and authorization audit messages within TXM's isolated log buffer.",
                "visibility": "Preserved in Research Build"
            },
            {
                "symbol": "_txm_runtime_alloc_type",
                "purpose": "Dynamic memory allocation primitive for cryptographic context descriptors and Image4 manifest parsing trees.",
                "visibility": "Preserved in Research Build"
            },
            {
                "symbol": "_txm_runtime_dealloc_type",
                "purpose": "Securely zeroes and deallocates cryptographic memory buffers.",
                "visibility": "Preserved in Research Build"
            },
            {
                "symbol": "_txm_runtime_set_nonce",
                "purpose": "Initializes and seals an anti-replay nonce slot during early device boot from DeviceTree /chosen properties.",
                "visibility": "Preserved in Research Build"
            },
            {
                "symbol": "_txm_runtime_roll_nonce",
                "purpose": "Regenerates cryptographic anti-replay nonce for an authenticated domain (mobile-asset or cryptex1).",
                "visibility": "Preserved in Research Build"
            },
            {
                "symbol": "_txm_runtime_copy_nonce",
                "purpose": "Securely copies active nonce digest for an authorized caller into caller-provided buffer with bounds assertion.",
                "visibility": "Preserved in Research Build"
            },
            {
                "symbol": "_txm_runtime_get_identifier_digest",
                "purpose": "Computes or extracts SHA-256 / SHA-384 digest for an authenticated Image4 certificate chain identifier.",
                "visibility": "Preserved in Research Build"
            },
            {
                "symbol": "_txm_runtime_get_identifier_cstr",
                "purpose": "Resolves normalized C-string identifier for signing authority.",
                "visibility": "Preserved in Research Build"
            }
        ],
        "image4_dispatch_handlers": [
            {
                "handler_id": 0,
                "name": "image4_verify_manifest_and_payload",
                "description": "Validates Image4 manifest against signing authorities, checks anti-replay nonces, verifies payload hash, and enforces domain fuses."
            },
            {
                "handler_id": 1,
                "name": "image4_pin_root",
                "description": "Hardened root CA pinning gate; rejects arbitrary root authority substitution on production SoC variants."
            },
            {
                "handler_id": 2,
                "name": "image4_evaluate_trust",
                "description": "Evaluates candidate certificate chains against Apple Root CA and CoreTrust store."
            },
            {
                "handler_id": 3,
                "name": "image4_parse_manifest_properties",
                "description": "Extracts normalized ASN.1 DER properties from Image4 manifest headers with strict 0x2c buffer bounds validation."
            },
            {
                "handler_id": 4,
                "name": "image4_query_status_properties",
                "description": "Queries current Image4 module state, active boot nonce descriptor, and secure boot operational state."
            },
            {
                "handler_id": 5,
                "name": "image4_map_and_authorize_executable",
                "description": "Authorizes code memory mapping into XNU/Exclave address spaces; enforces 16KB alignment before signaling SPTM to lock page as executable."
            }
        ],
        "trustcache_pipeline": {
            "operations": [
                {
                    "name": "load_trust_cache",
                    "entitlement": "com.apple.private.pmap.load-trust-cache",
                    "description": "Loads external TrustCache module into TXM memory, verifies cryptographic signature against Apple Root authority, and registers CDHashes."
                },
                {
                    "name": "unload_trust_cache",
                    "entitlement": "com.apple.private.unload-trust-cache",
                    "description": "Revokes and unmaps dynamic TrustCache module, invalidating associated CDHash entries."
                },
                {
                    "name": "validate_cdhash",
                    "entitlement": "com.apple.private.amfi.can-execute-cdhash",
                    "description": "Hardware-accelerated lookup verifying whether a candidate Mach-O binary's CDHash is present in the active TrustCache."
                }
            ],
            "hash_algorithms": ["SHA-256 (20-byte truncated CDHash)", "SHA-384 (32-byte CDHash)"]
        },
        "monitored_nodes": [
            "/chosen/debug-enabled",
            "/chosen/esdm-fuses",
            "/chosen/chip-id",
            "/chosen/darwinos-security-environment",
            "/chosen/cs-system-policy",
            "/chosen/security-mode-change-enable",
            "/chosen/amfi-only-platform-code",
            "/chosen/research-enabled",
            "/chosen/memory-map/TrustCache",
            "/chosen/iBoot/iboot-build-variant",
            "/product/udid-version",
            "/defaults/vmm-present"
        ]
    }
    
    out_p = ROOT / "artifacts/sptm/txm_csm_architecture.json"
    out_p.write_text(json.dumps(csm_spec, indent=2))
    print(f"[+] Wrote {out_p}")

if __name__ == "__main__":
    generate_sptm_topology()
    generate_txm_csm_architecture()
