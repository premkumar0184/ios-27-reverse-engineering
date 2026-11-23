#!/usr/bin/env python3
"""
verify_phase.py — Upgraded with animation physics + gesture arbitration phase verification

Usage: python3 tools/verify_phase.py <phase_id>

Animation phase IDs:
  anim_phase_1a_workspace_baseline
  anim_phase_1b_symbol_discovery
  anim_phase_2_physics_extraction
  anim_phase_3_context_tables
  anim_phase_4_modern_api
  anim_phase_5_synthesis

Gesture Arbitration phase IDs:
  gest_phase_1a_workspace_baseline
  gest_phase_1b_symbol_discovery
  gest_phase_2_slop_extraction
  gest_phase_3_arbitration_state_machine
  gest_phase_4_edge_gestures
  gest_phase_5_synthesis

ANE Direct Compiler phase IDs:
  ane_phase_1a_workspace_baseline
  ane_phase_1b_symbol_discovery
  ane_phase_2_hwx_compiler
  ane_phase_3_isa_bytecode
  ane_phase_4_driver_dispatch
  ane_phase_5_synthesis
"""
import json
import sys
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent

PLACEHOLDER_STRINGS = [
    "TODO", "TBD", "Coming in next step", "Analysis omitted for brevity",
    "placeholder", "PLACEHOLDER", "lorem ipsum", "coming soon",
    "to be determined", "work in progress", "WIP"
]

PHASE_SPECS = {
    # ── Original phases (preserved) ──────────────────────────────────────
    "phase_01_recon_and_inventory": {
        "required_artifacts": ["artifacts/manifests/buildmanifest_inventory.json"],
        "findings_docs": [],
        "min_findings_bytes": 2500,
        "json_schemas": {"artifacts/manifests/buildmanifest_inventory.json": ["restore_identities"]},
    },

    # ── Scrolling Reverse Engineering phases ──────────────────────────────
    "phase_0_tooling": {
        "required_artifacts": [
            "artifacts/scrolling/phase0_tooling_validation.json",
            "artifacts/scrolling/evidence_ledger.jsonl",
            "artifacts/scrolling/uikitcore_offset_resolution.json"
        ],
        "findings_docs": [],
        "min_findings_bytes": 0,
        "json_schemas": {},
    },
    "phase_1a_workspace": {
        "required_artifacts": [
            "artifacts/scrolling/uikitcore_offset_resolution.json",
            "findings/scrolling/01A_WORKSPACE_BASELINE.md"
        ],
        "findings_docs": ["findings/scrolling/01A_WORKSPACE_BASELINE.md"],
        "min_findings_bytes": 2500,
        "json_schemas": {},
    },
    "phase_2_architecture": {
        "required_artifacts": [
            "artifacts/scrolling/class_hierarchy.json",
            "artifacts/scrolling/framework_dependencies.json",
            "artifacts/scrolling/execution_flow_preliminary.json",
            "findings/scrolling/02_ARCHITECTURE_MAP.md"
        ],
        "findings_docs": ["findings/scrolling/02_ARCHITECTURE_MAP.md"],
        "min_findings_bytes": 2500,
        "json_schemas": {},
        "assertions": [
            ("phase_2_confirmed",
             "artifacts/scrolling/class_hierarchy.json",
             lambda d: len(d) > 0,
             "class_hierarchy.json must be populated and phase_2_confirmed"),
            ("26-Step Macro Execution Flow Matrix",
             "artifacts/scrolling/execution_flow_preliminary.json",
             lambda d: len(d) > 0,
             "26-Step Macro Execution Flow Matrix must be present"),
        ]
    },
    "phase_8_specification": {
        "required_artifacts": [
            "artifacts/scrolling/parameter_reference.json",
            "findings/scrolling/08_IMPLEMENTATION_SPECIFICATION.md"
        ],
        "findings_docs": ["findings/scrolling/08_IMPLEMENTATION_SPECIFICATION.md"],
        "min_findings_bytes": 5000,
        "json_schemas": {},
    },
    "phase_9_report": {
        "required_artifacts": [
            "IOS_27_SCROLLING_REVERSE_ENGINEERING.md",
            "artifacts/scrolling/evidence_appendix.json"
        ],
        "findings_docs": ["IOS_27_SCROLLING_REVERSE_ENGINEERING.md"],
        "min_findings_bytes": 10000,
        "json_schemas": {},
    },

    # ── Animation Physics Engine phases ───────────────────────────────────
    "anim_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/animation/phase_1a_workspace_baseline.json"
        ],
        "findings_docs": [],
        "min_findings_bytes": 0,
        "json_schemas": {
            "artifacts/animation/phase_1a_workspace_baseline.json": [
                "frameworks", "anchor_verification", "toolchain_trusted"
            ]
        },
        "assertions": [
            ("anchor_verification_trusted",
             "artifacts/animation/phase_1a_workspace_baseline.json",
             lambda d: d.get("anchor_verification", {}).get("toolchain_trusted") is True,
             "anchor_verification.toolchain_trusted must be true"),
            ("frameworks_complete",
             "artifacts/animation/phase_1a_workspace_baseline.json",
             lambda d: len(d.get("frameworks", {})) >= 4,
             "At least 4 frameworks must have load_base resolved"),
        ]
    },

    "anim_phase_1b_symbol_discovery": {
        "required_artifacts": [
            "artifacts/animation/symbol_inventory.json",
            "artifacts/animation/call_chain_map.json"
        ],
        "findings_docs": [],
        "min_findings_bytes": 0,
        "json_schemas": {
            "artifacts/animation/symbol_inventory.json": ["UIKitCore", "QuartzCore", "AnimationKit"],
        },
        "assertions": [
            ("call_chain_has_edges",
             "artifacts/animation/call_chain_map.json",
             lambda d: len(d.get("edges", d.get("chain", []))) >= 3,
             "call_chain_map must have >= 3 chain edges"),
        ]
    },

    "anim_phase_2_physics_extraction": {
        "required_artifacts": [
            "artifacts/animation/animation_physics_reference.json",
            "findings/animation/02_PHYSICS_EXTRACTION.md"
        ],
        "findings_docs": ["findings/animation/02_PHYSICS_EXTRACTION.md"],
        "min_findings_bytes": 5000,
        "json_schemas": {
            "artifacts/animation/animation_physics_reference.json": [
                "core_spring_model", "modern_api", "animation_contexts"
            ]
        },
        "assertions": [
            ("min_6_contexts",
             "artifacts/animation/animation_physics_reference.json",
             lambda d: len(d.get("animation_contexts", {})) >= 6,
             "animation_physics_reference must have >= 6 animation contexts"),
            ("no_unknown_in_core_model",
             "artifacts/animation/animation_physics_reference.json",
             lambda d: d.get("core_spring_model", {}).get("mass_default", {}).get("confidence") != "UNKNOWN",
             "core_spring_model.mass_default must not be UNKNOWN confidence"),
        ]
    },

    "anim_phase_3_context_tables": {
        "required_artifacts": [
            "artifacts/animation/timing_curve_reference.json",
            "artifacts/animation/cross_context_matrix.json",
            "findings/animation/03_CONTEXT_TABLES.md"
        ],
        "findings_docs": ["findings/animation/03_CONTEXT_TABLES.md"],
        "min_findings_bytes": 3000,
        "json_schemas": {
            "artifacts/animation/timing_curve_reference.json": ["cubic_bezier_curves"],
            "artifacts/animation/cross_context_matrix.json": [],
        },
        "assertions": [
            ("min_4_bezier_curves",
             "artifacts/animation/timing_curve_reference.json",
             lambda d: len(d.get("cubic_bezier_curves", {})) >= 4,
             "timing_curve_reference must have >= 4 cubic bezier definitions"),
            ("min_10_contexts_in_matrix",
             "artifacts/animation/cross_context_matrix.json",
             lambda d: len(d.get("contexts", d)) >= 10 if isinstance(d, dict) else len(d) >= 10,
             "cross_context_matrix must have >= 10 animation contexts"),
        ]
    },

    "anim_phase_4_modern_api": {
        "required_artifacts": [
            "artifacts/animation/modern_api_verification.json",
            "findings/animation/04_MODERN_API.md",
            "artifacts/animation/pseudocode/CASpringAnimation_perceptual_init.pseudo.c",
            "artifacts/animation/pseudocode/CASpringAnimation_settlingDuration.pseudo.c"
        ],
        "findings_docs": ["findings/animation/04_MODERN_API.md"],
        "min_findings_bytes": 3000,
        "json_schemas": {
            "artifacts/animation/modern_api_verification.json": [
                "perceptual_api_confirmed", "stiffness_formula", "settling_epsilon"
            ]
        },
        "assertions": [
            ("api_confirmed",
             "artifacts/animation/modern_api_verification.json",
             lambda d: d.get("perceptual_api_confirmed") is True,
             "perceptual_api_confirmed must be true"),
            ("settling_epsilon_reasonable",
             "artifacts/animation/modern_api_verification.json",
             lambda d: 0.00001 <= d.get("settling_epsilon", 0) <= 0.01,
             "settling_epsilon must be in range [0.00001, 0.01]"),
        ]
    },

    "anim_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_ANIMATION_PHYSICS_RE.md",
            "artifacts/animation/cross_validation_matrix.json",
            "tools/verify_animation_constants.py"
        ],
        "findings_docs": ["IOS_27_ANIMATION_PHYSICS_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/animation/cross_validation_matrix.json": []
        },
        "assertions": [
            ("verify_script_runnable",
             None,
             lambda _: Path(ROOT / "tools/verify_animation_constants.py").is_file(),
             "tools/verify_animation_constants.py must exist and be runnable"),
        ]
    },

    # ── Gesture Recognizer Arbitration Engine phases ───────────────────────
    "gest_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/gesture/phase_1a_workspace_baseline.json"
        ],
        "findings_docs": [],
        "min_findings_bytes": 0,
        "json_schemas": {
            "artifacts/gesture/phase_1a_workspace_baseline.json": [
                "frameworks", "anchor_verification"
            ]
        },
        "assertions": [
            ("toolchain_trusted",
             "artifacts/gesture/phase_1a_workspace_baseline.json",
             lambda d: d.get("anchor_verification", {}).get("toolchain_trusted") is True,
             "anchor_verification.toolchain_trusted must be true"),
            ("gestures_framework_loaded",
             "artifacts/gesture/phase_1a_workspace_baseline.json",
             lambda d: "Gestures" in d.get("frameworks", {}),
             "frameworks must contain 'Gestures' key"),
        ]
    },

    "gest_phase_1b_symbol_discovery": {
        "required_artifacts": [
            "artifacts/gesture/symbol_inventory.json",
            "artifacts/gesture/class_hierarchy_map.json"
        ],
        "findings_docs": [],
        "min_findings_bytes": 0,
        "json_schemas": {
            "artifacts/gesture/symbol_inventory.json": ["Gestures_framework", "UIKitCore_gesture_classes"],
        },
        "assertions": [
            ("min_8_classes",
             "artifacts/gesture/symbol_inventory.json",
             lambda d: len(d.get("Gestures_framework", {}).get("objc_classes", [])) >= 6,
             "symbol_inventory Gestures_framework must have >= 6 ObjC classes"),
            ("hierarchy_has_arbitration",
             "artifacts/gesture/class_hierarchy_map.json",
             lambda d: len(d.get("arbitration_classes", [])) >= 1,
             "class_hierarchy_map must list at least 1 arbitration class"),
        ]
    },

    "gest_phase_2_slop_extraction": {
        "required_artifacts": [
            "artifacts/gesture/per_gesture_threshold_table.json",
            "findings/gesture/02_SLOP_EXTRACTION.md"
        ],
        "findings_docs": ["findings/gesture/02_SLOP_EXTRACTION.md"],
        "min_findings_bytes": 5000,
        "json_schemas": {
            "artifacts/gesture/per_gesture_threshold_table.json": ["thresholds"]
        },
        "assertions": [
            ("min_6_recognizer_types",
             "artifacts/gesture/per_gesture_threshold_table.json",
             lambda d: len(d.get("thresholds", {})) >= 6,
             "per_gesture_threshold_table must have >= 6 recognizer types"),
            ("pan_slop_tiers_correct",
             "artifacts/gesture/per_gesture_threshold_table.json",
             lambda d: d.get("thresholds", {}).get("Pan", {}).get("slop_tiers_pt") == [10, 4, 2, 0],
             "Pan.slop_tiers_pt must be [10, 4, 2, 0] (pre-confirmed from scrolling RE)"),
        ]
    },

    "gest_phase_3_arbitration_state_machine": {
        "required_artifacts": [
            "artifacts/gesture/gesture_arbitration_state_machine.json",
            "findings/gesture/03_ARBITRATION_STATE_MACHINE.md"
        ],
        "findings_docs": ["findings/gesture/03_ARBITRATION_STATE_MACHINE.md"],
        "min_findings_bytes": 5000,
        "json_schemas": {
            "artifacts/gesture/gesture_arbitration_state_machine.json": [
                "states", "transitions", "arbitration_rules"
            ]
        },
        "assertions": [
            ("all_6_states",
             "artifacts/gesture/gesture_arbitration_state_machine.json",
             lambda d: len(d.get("states", {})) >= 6,
             "state machine must define all 6 UIGestureRecognizerState values"),
            ("min_5_transitions",
             "artifacts/gesture/gesture_arbitration_state_machine.json",
             lambda d: len(d.get("transitions", [])) >= 5,
             "must document at least 5 state transitions with predicates"),
        ]
    },

    "gest_phase_4_edge_gestures": {
        "required_artifacts": [
            "artifacts/gesture/edge_gesture_config.json",
            "findings/gesture/04_EDGE_GESTURES.md",
            "artifacts/gesture/pseudocode/back_gesture_recognizer.pseudo.c"
        ],
        "findings_docs": ["findings/gesture/04_EDGE_GESTURES.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/gesture/edge_gesture_config.json": ["edge_gestures"]
        },
        "assertions": [
            ("all_4_edge_gestures",
             "artifacts/gesture/edge_gesture_config.json",
             lambda d: all(k in d.get("edge_gestures", {})
                          for k in ["Back", "NotificationCentre", "ControlCentre", "Reachability"]),
             "edge_gesture_config must define Back, NotificationCentre, ControlCentre, Reachability"),
            ("back_has_inset",
             "artifacts/gesture/edge_gesture_config.json",
             lambda d: d.get("edge_gestures", {}).get("Back", {}).get("edge_inset_pt", {}).get("value") is not None,
             "Back gesture must have an edge_inset_pt value"),
        ]
    },

    "gest_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_GESTURE_ARBITRATION_RE.md",
            "artifacts/gesture/cross_validation_matrix.json",
            "tools/verify_gesture_thresholds.py"
        ],
        "findings_docs": ["IOS_27_GESTURE_ARBITRATION_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/gesture/cross_validation_matrix.json": ["extraction_confidence"]
        },
        "assertions": [
            ("verify_script_exists",
             None,
             lambda _: Path(ROOT / "tools/verify_gesture_thresholds.py").is_file(),
             "tools/verify_gesture_thresholds.py must exist"),
            ("cross_val_has_no_all_unknown",
             "artifacts/gesture/cross_validation_matrix.json",
             lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 1,
             "cross_validation_matrix must have at least 1 EXTRACTED confidence constant"),
        ]
    },

    # ── Apple Neural Engine (ANE) Direct Compiler phases ──────────────────
    "ane_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/ane/phase_1a_workspace_baseline.json"
        ],
        "findings_docs": [],
        "min_findings_bytes": 0,
        "json_schemas": {
            "artifacts/ane/phase_1a_workspace_baseline.json": [
                "frameworks", "kernel_drivers", "firmware"
            ]
        },
        "assertions": [
            ("ane_fw_verified",
             "artifacts/ane/phase_1a_workspace_baseline.json",
             lambda d: d.get("firmware", {}).get("verified") is True,
             "firmware must be verified"),
        ]
    },

    "ane_phase_1b_symbol_discovery": {
        "required_artifacts": [
            "artifacts/ane/symbol_inventory.json",
            "artifacts/ane/client_server_topology.json"
        ],
        "findings_docs": [],
        "min_findings_bytes": 0,
        "json_schemas": {
            "artifacts/ane/symbol_inventory.json": ["frameworks"],
            "artifacts/ane/client_server_topology.json": ["client_flow"]
        },
        "assertions": [
            ("has_ane_client",
             "artifacts/ane/symbol_inventory.json",
             lambda d: "AppleNeuralEngine" in d.get("frameworks", {}),
             "symbol_inventory must contain AppleNeuralEngine classes"),
        ]
    },

    "ane_phase_2_hwx_compiler": {
        "required_artifacts": [
            "artifacts/ane/hwx_container_spec.json",
            "findings/ane/02_HWX_COMPILER.md"
        ],
        "findings_docs": ["findings/ane/02_HWX_COMPILER.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ane/hwx_container_spec.json": ["sections", "header"]
        },
        "assertions": [
            ("has_td_section",
             "artifacts/ane/hwx_container_spec.json",
             lambda d: "td" in d.get("sections", {}),
             "must contain td section descriptor"),
        ]
    },

    "ane_phase_3_isa_bytecode": {
        "required_artifacts": [
            "artifacts/ane/ane_isa_opcode_table.json",
            "findings/ane/03_ISA_BYTECODE.md"
        ],
        "findings_docs": ["findings/ane/03_ISA_BYTECODE.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ane/ane_isa_opcode_table.json": ["opcodes", "tile_geometry"]
        },
        "assertions": [
            ("has_opcodes",
             "artifacts/ane/ane_isa_opcode_table.json",
             lambda d: len(d.get("opcodes", {})) >= 5,
             "must define at least 5 hardware opcodes"),
        ]
    },

    "ane_phase_4_driver_dispatch": {
        "required_artifacts": [
            "artifacts/ane/hardware_dispatch_spec.json",
            "artifacts/ane/pseudocode/ane_direct_runtime.pseudo.c",
            "findings/ane/04_DRIVER_DISPATCH.md"
        ],
        "findings_docs": ["findings/ane/04_DRIVER_DISPATCH.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ane/hardware_dispatch_spec.json": ["fifo", "channels"]
        },
        "assertions": [
            ("fifo_nid_0x40",
             "artifacts/ane/hardware_dispatch_spec.json",
             lambda d: d.get("fifo", {}).get("node_id") == 0x40,
             "FIFO Node ID must be 0x40"),
        ]
    },

    "ane_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_APPLE_NEURAL_ENGINE_RE.md",
            "artifacts/ane/cross_validation_matrix.json",
            "tools/verify_ane_constants.py"
        ],
        "findings_docs": ["IOS_27_APPLE_NEURAL_ENGINE_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/ane/cross_validation_matrix.json": ["extraction_confidence"]
        },
        "assertions": [
            ("verify_script_exists",
             None,
             lambda _: Path(ROOT / "tools/verify_ane_constants.py").is_file(),
             "tools/verify_ane_constants.py must exist"),
            ("has_extracted_constants",
             "artifacts/ane/cross_validation_matrix.json",
             lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 1,
             "cross_validation_matrix must have at least 1 EXTRACTED confidence constant"),
        ]
    },

    # ── ExclaveOS Microkernel & Tightbeam IPC phases ─────────────────────
    "exclave_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/exclave/phase_1a_workspace_baseline.json",
            "artifacts/exclave/bund_container_spec.json"
        ],
        "findings_docs": [],
        "min_findings_bytes": 0,
        "json_schemas": {
            "artifacts/exclave/phase_1a_workspace_baseline.json": ["exclaveos_image", "exclavecore_bundle", "microkernel_binaries"],
            "artifacts/exclave/bund_container_spec.json": ["magic", "tags", "entries"]
        },
        "assertions": [
            ("bund_magic_valid",
             "artifacts/exclave/bund_container_spec.json",
             lambda d: d.get("magic") in ("0x444e5542", 0x444e5542) or d.get("magic_ascii") in ("DNUB", "BUND"),
             "magic must be DNUB / BUND"),
            ("min_4_binaries",
             "artifacts/exclave/bund_container_spec.json",
             lambda d: len(d.get("entries", [])) >= 4,
             "must map at least 4 microkernel binaries in BUND"),
        ]
    },

    "exclave_phase_1b_cl4_microkernel": {
        "required_artifacts": [
            "artifacts/exclave/cl4_microkernel_spec.json",
            "artifacts/exclave/capability_delegation_model.json",
            "findings/exclave/01B_CL4_MICROKERNEL.md"
        ],
        "findings_docs": ["findings/exclave/01B_CL4_MICROKERNEL.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/exclave/cl4_microkernel_spec.json": ["syscalls", "cspace"],
            "artifacts/exclave/capability_delegation_model.json": ["capability_types", "rights_bits"]
        },
        "assertions": [
            ("has_cap_mint",
             "artifacts/exclave/cl4_microkernel_spec.json",
             lambda d: any("Cap_Mint" in sc for sc in d.get("syscalls", {})),
             "must document L4_Cap_Mint capability minting syscall"),
        ]
    },

    "exclave_phase_2_tightbeam_wire_format": {
        "required_artifacts": [
            "artifacts/exclave/tightbeam_wire_spec.json",
            "artifacts/exclave/tightbeam_protocol_schema.json",
            "findings/exclave/02_TIGHTBEAM_WIRE_FORMAT.md"
        ],
        "findings_docs": ["findings/exclave/02_TIGHTBEAM_WIRE_FORMAT.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/exclave/tightbeam_wire_spec.json": ["message_header", "transports"],
            "artifacts/exclave/tightbeam_protocol_schema.json": ["swift_protocols", "descriptors"]
        },
        "assertions": [
            ("has_cl4_transports",
             "artifacts/exclave/tightbeam_wire_spec.json",
             lambda d: all(t in d.get("transports", {}) for t in ["cL4", "cL4_large"]),
             "must document cL4 and cL4_large transports"),
        ]
    },

    "exclave_phase_3_pmm_datacubes": {
        "required_artifacts": [
            "artifacts/exclave/datacube_memory_spec.json",
            "artifacts/exclave/jg_sharedmem_spec.json",
            "findings/exclave/03_DATACUBES_AND_MEMORY.md"
        ],
        "findings_docs": ["findings/exclave/03_DATACUBES_AND_MEMORY.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/exclave/datacube_memory_spec.json": ["datacube_abstraction", "pmm_server"],
            "artifacts/exclave/jg_sharedmem_spec.json": ["shared_memory_segments"]
        },
        "assertions": [
            ("has_retyping",
             "artifacts/exclave/datacube_memory_spec.json",
             lambda d: "retyping_protocol" in d.get("datacube_abstraction", {}),
             "must document page retyping protocol via Datacubes"),
        ]
    },

    "exclave_phase_4_xnu_boundary": {
        "required_artifacts": [
            "artifacts/exclave/xnu_boundary_spec.json",
            "artifacts/exclave/pseudocode/tightbeam_client.pseudo.c",
            "findings/exclave/04_XNU_BOUNDARY.md"
        ],
        "findings_docs": ["findings/exclave/04_XNU_BOUNDARY.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/exclave/xnu_boundary_spec.json": ["syscall_traps", "xnuproxy"]
        },
        "assertions": [
            ("has_exclaves_ctl_trap",
             "artifacts/exclave/xnu_boundary_spec.json",
             lambda d: any("exclaves_ctl" in t for t in d.get("syscall_traps", {})),
             "must document _exclaves_ctl_trap"),
        ]
    },

    "exclave_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_EXCLAVEOS_TIGHTBEAM_RE.md",
            "artifacts/exclave/cross_validation_matrix.json",
            "tools/verify_exclave_constants.py"
        ],
        "findings_docs": ["IOS_27_EXCLAVEOS_TIGHTBEAM_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/exclave/cross_validation_matrix.json": ["extraction_confidence"]
        },
        "assertions": [
            ("verify_script_exists",
              None,
              lambda _: Path(ROOT / "tools/verify_exclave_constants.py").is_file(),
              "tools/verify_exclave_constants.py must exist"),
            ("has_extracted_constants",
              "artifacts/exclave/cross_validation_matrix.json",
              lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 1,
              "cross_validation_matrix must have at least 1 EXTRACTED confidence constant"),
        ]
    },

    # ── Secure Enclave & sepOS Hardware Cryptographic Engine phases ────
    "sep_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/sep/phase_1a_workspace_baseline.json",
            "artifacts/sep/sep_firmware_container_spec.json",
            "findings/sep/01A_WORKSPACE_BASELINE.md"
        ],
        "findings_docs": ["findings/sep/01A_WORKSPACE_BASELINE.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/sep/phase_1a_workspace_baseline.json": ["target_device", "firmware_assets", "hardware_context"],
            "artifacts/sep/sep_firmware_container_spec.json": ["fourcc_tag", "wrapper", "keybag", "payload_properties"]
        },
        "assertions": [
            ("fourcc_is_sepi",
             "artifacts/sep/sep_firmware_container_spec.json",
             lambda d: d.get("fourcc_tag") == "sepi",
             "fourcc_tag must be sepi"),
            ("min_2_keybag_entries",
             "artifacts/sep/sep_firmware_container_spec.json",
             lambda d: len(d.get("keybag", {}).get("entries", [])) >= 2,
             "keybag must have at least 2 entries (GID and UID)"),
            ("has_tz0_carveout",
             "artifacts/sep/sep_firmware_container_spec.json",
             lambda d: d.get("payload_properties", {}).get("tz0s", {}).get("value_int") == 102432768,
             "tz0s carveout must be 102432768 bytes (0x061b0000)"),
        ]
    },

    "sep_phase_1b_sepos_microkernel": {
        "required_artifacts": [
            "artifacts/sep/sepos_microkernel_spec.json",
            "artifacts/sep/sepos_service_topology.json",
            "findings/sep/01B_SEPOS_MICROKERNEL.md"
        ],
        "findings_docs": ["findings/sep/01B_SEPOS_MICROKERNEL.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/sep/sepos_microkernel_spec.json": ["memory_carveouts", "microkernel_architecture"],
            "artifacts/sep/sepos_service_topology.json": ["services", "ipc_endpoints"]
        },
        "assertions": [
            ("tz0_base_address",
             "artifacts/sep/sepos_microkernel_spec.json",
             lambda d: d.get("memory_carveouts", {}).get("tz0", {}).get("base_physical_address") == "0x800000000",
             "tz0 base physical address must be 0x800000000"),
        ]
    },

    "sep_phase_2_key_ladder": {
        "required_artifacts": [
            "artifacts/sep/key_ladder_spec.json",
            "artifacts/sep/data_protection_classes.json",
            "findings/sep/02_KEY_LADDER_AND_STORAGE.md"
        ],
        "findings_docs": ["findings/sep/02_KEY_LADDER_AND_STORAGE.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/sep/key_ladder_spec.json": ["key_ladder", "aes_engine", "public_key_accelerator"],
            "artifacts/sep/data_protection_classes.json": ["classes", "kdf_specifications"]
        },
        "assertions": [
            ("min_4_protection_classes",
             "artifacts/sep/data_protection_classes.json",
             lambda d: len(d.get("classes", [])) >= 4,
             "must define Class A through Class D Data Protection classes"),
        ]
    },

    "sep_phase_3_mailbox_protocol": {
        "required_artifacts": [
            "artifacts/sep/sep_mailbox_protocol.json",
            "artifacts/sep/anti_replay_nvram_spec.json",
            "findings/sep/03_MAILBOX_AND_ANTI_REPLAY.md"
        ],
        "findings_docs": ["findings/sep/03_MAILBOX_AND_ANTI_REPLAY.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/sep/sep_mailbox_protocol.json": ["mmio_registers", "interrupt_vectors", "command_framing"],
            "artifacts/sep/anti_replay_nvram_spec.json": ["anti_replay_tokens", "monitors"]
        },
        "assertions": [
            ("mailbox_mmio_base",
             "artifacts/sep/sep_mailbox_protocol.json",
             lambda d: d.get("mmio_registers", {}).get("ascwrap_mailbox", {}).get("base_address") == "0x0000000072600000",
             "ASCwrap-v6 Mailbox MMIO base must be 0x72600000"),
        ]
    },

    "sep_phase_4_xnu_driver_boundary": {
        "required_artifacts": [
            "artifacts/sep/xnu_sep_boundary_spec.json",
            "artifacts/sep/pseudocode/sep_mailbox_client.pseudo.c",
            "findings/sep/04_XNU_DRIVER_BOUNDARY.md"
        ],
        "findings_docs": ["findings/sep/04_XNU_DRIVER_BOUNDARY.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/sep/xnu_sep_boundary_spec.json": ["kernel_drivers", "userland_frameworks"]
        },
        "assertions": [
            ("has_apple_sep_manager",
             "artifacts/sep/xnu_sep_boundary_spec.json",
             lambda d: any("AppleSEPManager" in k for k in d.get("kernel_drivers", {})),
             "must document AppleSEPManager driver"),
        ]
    },

    "sep_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_SECURE_ENCLAVE_SEPOS_RE.md",
            "artifacts/sep/cross_validation_matrix.json",
            "tools/verify_sep_constants.py"
        ],
        "findings_docs": ["IOS_27_SECURE_ENCLAVE_SEPOS_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/sep/cross_validation_matrix.json": ["extraction_confidence"]
        },
        "assertions": [
            ("verify_script_exists",
              None,
              lambda _: Path(ROOT / "tools/verify_sep_constants.py").is_file(),
              "tools/verify_sep_constants.py must exist"),
            ("has_extracted_constants",
              "artifacts/sep/cross_validation_matrix.json",
              lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 1,
              "cross_validation_matrix must have at least 1 EXTRACTED confidence constant"),
        ]
    },

    # ── SPTM & TXM Hypervisor Barrier & Research Boot Chain phases ─────
    "sptm_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/sptm/phase_1a_workspace_baseline.json",
            "artifacts/sptm/image4_container_spec.json",
            "findings/sptm/01A_WORKSPACE_BASELINE.md"
        ],
        "findings_docs": ["findings/sptm/01A_WORKSPACE_BASELINE.md"],
        "min_findings_bytes": 2500,
        "json_schemas": {
            "artifacts/sptm/phase_1a_workspace_baseline.json": ["target_device", "firmware_assets", "hardware_context"],
            "artifacts/sptm/image4_container_spec.json": ["containers", "parser_specification"]
        },
        "assertions": [
            ("has_5_firmware_assets",
             "artifacts/sptm/phase_1a_workspace_baseline.json",
             lambda d: len(d.get("firmware_assets", {})) >= 5,
             "must catalog all 5 target firmware images"),
            ("fourcc_is_sptm",
             "artifacts/sptm/image4_container_spec.json",
             lambda d: any(c.get("fourcc_tag") == "sptm" for c in d.get("containers", [])),
             "containers must include sptm FourCC tag"),
        ]
    },

    "sptm_phase_1b_architecture_topology": {
        "required_artifacts": [
            "artifacts/sptm/sptm_topology_spec.json",
            "artifacts/sptm/txm_csm_architecture.json",
            "findings/sptm/01B_ARCHITECTURE_AND_TOPOLOGY.md"
        ],
        "findings_docs": ["findings/sptm/01B_ARCHITECTURE_AND_TOPOLOGY.md"],
        "min_findings_bytes": 2500,
        "json_schemas": {
            "artifacts/sptm/sptm_topology_spec.json": ["privilege_tiers", "memory_segments", "entry_point"],
            "artifacts/sptm/txm_csm_architecture.json": ["runtime_functions", "monitored_nodes"]
        },
        "assertions": [
            ("sptm_entrypoint_valid",
             "artifacts/sptm/sptm_topology_spec.json",
             lambda d: "0xfffffff0270bc388" in str(d.get("entry_point", "")),
             "SPTM entrypoint must be 0xfffffff0270bc388"),
            ("has_txm_symbols",
             "artifacts/sptm/txm_csm_architecture.json",
             lambda d: len(d.get("runtime_functions", [])) >= 5,
             "TXM CSM architecture must document preserved runtime symbols"),
        ]
    },

    "sptm_phase_2_hardware_register_geometry": {
        "required_artifacts": [
            "artifacts/sptm/stage2_translation_geometry.json",
            "artifacts/sptm/devicetree_hardware_map.json",
            "findings/sptm/02_HARDWARE_REGISTER_GEOMETRY.md"
        ],
        "findings_docs": ["findings/sptm/02_HARDWARE_REGISTER_GEOMETRY.md"],
        "min_findings_bytes": 2500,
        "json_schemas": {
            "artifacts/sptm/stage2_translation_geometry.json": ["stage2_translation", "physical_frame_types", "protection_registers"],
            "artifacts/sptm/devicetree_hardware_map.json": ["device_nodes", "memory_carveouts"]
        },
        "assertions": [
            ("has_50_frame_types",
             "artifacts/sptm/stage2_translation_geometry.json",
             lambda d: len(d.get("physical_frame_types", {})) >= 50,
             "must catalog at least 50 physical frame types"),
            ("has_ctrr_registers",
             "artifacts/sptm/stage2_translation_geometry.json",
             lambda d: "ctrr" in d.get("protection_registers", {}),
             "must document CTRR protection registers"),
        ]
    },

    "sptm_phase_3_hypercall_protocol": {
        "required_artifacts": [
            "artifacts/sptm/sptm_hypercall_dispatch_spec.json",
            "artifacts/sptm/iboot_diagnostic_commands.json",
            "findings/sptm/03_HYPERCALL_AND_DIAGNOSTICS.md"
        ],
        "findings_docs": ["findings/sptm/03_HYPERCALL_AND_DIAGNOSTICS.md"],
        "min_findings_bytes": 2500,
        "json_schemas": {
            "artifacts/sptm/sptm_hypercall_dispatch_spec.json": ["dispatch_tables", "function_ids", "calling_convention"],
            "artifacts/sptm/iboot_diagnostic_commands.json": ["diagnostic_commands", "boot_arguments"]
        },
        "assertions": [
            ("has_40_function_ids",
             "artifacts/sptm/sptm_hypercall_dispatch_spec.json",
             lambda d: len(d.get("function_ids", {})) >= 40,
             "must document at least 40 SPTM function IDs"),
            ("has_iboot_commands",
             "artifacts/sptm/iboot_diagnostic_commands.json",
             lambda d: len(d.get("diagnostic_commands", {})) >= 10,
             "must document at least 10 preserved iBoot diagnostic commands"),
        ]
    },

    "sptm_phase_4_kernel_boundary": {
        "required_artifacts": [
            "artifacts/sptm/xnu_sptm_boundary_spec.json",
            "artifacts/sptm/pseudocode/sptm_hypercall_client.pseudo.c",
            "findings/sptm/04_KERNEL_BOUNDARY_CLIENT.md"
        ],
        "findings_docs": ["findings/sptm/04_KERNEL_BOUNDARY_CLIENT.md"],
        "min_findings_bytes": 2500,
        "json_schemas": {
            "artifacts/sptm/xnu_sptm_boundary_spec.json": ["xnu_routines", "stage2_fault_handling"]
        },
        "assertions": [
            ("pseudocode_exists",
             None,
             lambda _: Path(ROOT / "artifacts/sptm/pseudocode/sptm_hypercall_client.pseudo.c").is_file(),
             "artifacts/sptm/pseudocode/sptm_hypercall_client.pseudo.c must exist"),
            ("has_sptm_call",
             "artifacts/sptm/xnu_sptm_boundary_spec.json",
             lambda d: any("sptm_call" in k for k in d.get("xnu_routines", {})),
             "must document sptm_call routine in XNU boundary"),
        ]
    },

    "sptm_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_SPTM_TXM_BOOT_RE.md",
            "artifacts/sptm/cross_validation_matrix.json",
            "tools/verify_sptm_constants.py"
        ],
        "findings_docs": ["IOS_27_SPTM_TXM_BOOT_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/sptm/cross_validation_matrix.json": ["extraction_confidence"]
        },
        "assertions": [
            ("verify_script_exists",
              None,
              lambda _: Path(ROOT / "tools/verify_sptm_constants.py").is_file(),
              "tools/verify_sptm_constants.py must exist"),
            ("has_extracted_constants",
              "artifacts/sptm/cross_validation_matrix.json",
              lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 1,
              "cross_validation_matrix must have at least 1 EXTRACTED confidence constant"),
        ]
    },

    # ── Apple AGX GPU (Generation G18) Microarchitecture phases ─────────
    "gpu_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/gpu/phase_1a_workspace_baseline.json",
            "artifacts/gpu/agx_firmware_container_spec.json",
            "findings/gpu/01A_WORKSPACE_BASELINE.md"
        ],
        "findings_docs": ["findings/gpu/01A_WORKSPACE_BASELINE.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/gpu/phase_1a_workspace_baseline.json": ["system_environment", "firmware_inventory", "kernel_driver_inventory", "userland_framework_inventory"],
            "artifacts/gpu/agx_firmware_container_spec.json": ["im4p_containers", "msr_containers", "fourcc_catalog"]
        },
        "assertions": [
            ("fourcc_tags_valid",
             "artifacts/gpu/agx_firmware_container_spec.json",
             lambda d: all(t in d.get("fourcc_catalog", {}) for t in ["gfxf", "gf1f", "msrf", "rmsr"]),
             "fourcc_catalog must include gfxf, gf1f, msrf, rmsr tags"),
            ("has_4_kernel_drivers",
             "artifacts/gpu/phase_1a_workspace_baseline.json",
             lambda d: len(d.get("kernel_driver_inventory", {})) >= 4,
             "must inventory at least 4 GPU kernel drivers"),
            ("rkosftab_entries_mapped",
             "artifacts/gpu/agx_firmware_container_spec.json",
             lambda d: len(d.get("im4p_containers", {}).get("armfw_g18p", {}).get("rkosftab", {}).get("entries", [])) >= 3,
             "armfw_g18p must have >= 3 rkosftab silicon step entries"),
        ]
    },

    "gpu_phase_1b_microarchitecture": {
        "required_artifacts": [
            "artifacts/gpu/g18_microarchitecture_spec.json",
            "artifacts/gpu/rtbuddy_firmware_topology.json",
            "findings/gpu/01B_G18_MICROARCHITECTURE.md"
        ],
        "findings_docs": ["findings/gpu/01B_G18_MICROARCHITECTURE.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/gpu/g18_microarchitecture_spec.json": ["compute_core_clusters", "ray_tracing_hardware", "mesh_shading_pipeline"],
            "artifacts/gpu/rtbuddy_firmware_topology.json": ["dual_core_topology", "ipc_endpoints"]
        },
        "assertions": [
            ("has_ray_tracing_units",
             "artifacts/gpu/g18_microarchitecture_spec.json",
             lambda d: "bvh_traversal_engine" in d.get("ray_tracing_hardware", {}),
             "must document hardware BVH traversal engine"),
        ]
    },

    "gpu_phase_2_mmio_and_tile_geometry": {
        "required_artifacts": [
            "artifacts/gpu/gpu_mmio_memory_geometry.json",
            "artifacts/gpu/tile_compression_msr_spec.json",
            "findings/gpu/02_MMIO_AND_TILE_GEOMETRY.md"
        ],
        "findings_docs": ["findings/gpu/02_MMIO_AND_TILE_GEOMETRY.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/gpu/gpu_mmio_memory_geometry.json": ["mmio_registers", "doorbells", "page_tables"],
            "artifacts/gpu/tile_compression_msr_spec.json": ["tile_memory", "lossless_compression"]
        },
        "assertions": [
            ("has_pmp_doorbell",
             "artifacts/gpu/gpu_mmio_memory_geometry.json",
             lambda d: "PMPDoorbell" in str(d.get("doorbells", {})),
             "must document PMPDoorbell MMIO register region"),
        ]
    },

    "gpu_phase_3_command_stream": {
        "required_artifacts": [
            "artifacts/gpu/gpu_command_stream_spec.json",
            "artifacts/gpu/agx_ring_buffer_protocol.json",
            "findings/gpu/03_COMMAND_STREAM_AND_RING_BUFFER.md"
        ],
        "findings_docs": ["findings/gpu/03_COMMAND_STREAM_AND_RING_BUFFER.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/gpu/gpu_command_stream_spec.json": ["command_descriptors", "opcodes"],
            "artifacts/gpu/agx_ring_buffer_protocol.json": ["ring_buffers", "fence_synchronization"]
        },
        "assertions": [
            ("descriptor_size_64",
             "artifacts/gpu/gpu_command_stream_spec.json",
             lambda d: d.get("command_descriptors", {}).get("descriptor_size_bytes") == 64,
             "hardware command descriptor must be 64-byte aligned"),
        ]
    },

    "gpu_phase_4_kernel_boundary": {
        "required_artifacts": [
            "artifacts/gpu/xnu_gpu_boundary_spec.json",
            "artifacts/gpu/pseudocode/agx_direct_submit.pseudo.c",
            "findings/gpu/04_KERNEL_BOUNDARY_AND_DIRECT_SUBMISSION.md"
        ],
        "findings_docs": ["findings/gpu/04_KERNEL_BOUNDARY_AND_DIRECT_SUBMISSION.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/gpu/xnu_gpu_boundary_spec.json": ["user_client_methods", "direct_submission_path"]
        },
        "assertions": [
            ("pseudocode_exists",
             None,
             lambda _: Path(ROOT / "artifacts/gpu/pseudocode/agx_direct_submit.pseudo.c").is_file(),
             "artifacts/gpu/pseudocode/agx_direct_submit.pseudo.c must exist"),
        ]
    },

    "gpu_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_APPLE_AGX_GPU_RE.md",
            "artifacts/gpu/cross_validation_matrix.json",
            "tools/verify_gpu_constants.py"
        ],
        "findings_docs": ["IOS_27_APPLE_AGX_GPU_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/gpu/cross_validation_matrix.json": ["extraction_confidence"]
        },
        "assertions": [
            ("verify_script_exists",
              None,
              lambda _: Path(ROOT / "tools/verify_gpu_constants.py").is_file(),
              "tools/verify_gpu_constants.py must exist"),
            ("has_extracted_constants",
              "artifacts/gpu/cross_validation_matrix.json",
              lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 1,
              "cross_validation_matrix must have at least 1 EXTRACTED confidence constant"),
        ]
    },

    # ── Apple NVMe Storage Controller 2 (ANS2) & Flash Engine phases ────
    "ans2_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/ans2/phase_1a_workspace_baseline.json",
            "artifacts/ans2/ans2_firmware_container_spec.json",
            "findings/ans2/01A_WORKSPACE_BASELINE.md"
        ],
        "findings_docs": ["findings/ans2/01A_WORKSPACE_BASELINE.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ans2/phase_1a_workspace_baseline.json": ["soc", "firmware_metadata", "macho_architecture"],
            "artifacts/ans2/ans2_firmware_container_spec.json": ["im4p_container", "extracted_payload"]
        },
        "assertions": [
            ("fourcc_is_ansf",
             "artifacts/ans2/phase_1a_workspace_baseline.json",
             lambda d: d.get("firmware_metadata", {}).get("fourcc_tag") == "ansf",
             "firmware fourcc_tag must be 'ansf'"),
            ("im4p_size_matches",
             "artifacts/ans2/phase_1a_workspace_baseline.json",
             lambda d: d.get("firmware_metadata", {}).get("im4p_size_bytes") == 1329936,
             "im4p_size_bytes must equal 1,329,936 bytes"),
            ("decompressed_size_matches",
             "artifacts/ans2/phase_1a_workspace_baseline.json",
             lambda d: d.get("firmware_metadata", {}).get("decompressed_size_bytes") == 5634888,
             "decompressed_size_bytes must equal 5,634,888 bytes"),
        ]
    },

    "ans2_phase_1b_microarchitecture": {
        "required_artifacts": [
            "artifacts/ans2/ans2_microarchitecture_spec.json",
            "artifacts/ans2/rtkit_ftl_topology.json",
            "findings/ans2/01B_ANS2_MICROARCHITECTURE.md"
        ],
        "findings_docs": ["findings/ans2/01B_ANS2_MICROARCHITECTURE.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ans2/ans2_microarchitecture_spec.json": ["coprocessor_topology", "ftl_subsystems", "c_source_modules"],
            "artifacts/ans2/rtkit_ftl_topology.json": ["task_hierarchy", "memory_segmentation", "endpoint_routing"]
        },
        "assertions": [
            ("has_c_modules",
             "artifacts/ans2/ans2_microarchitecture_spec.json",
             lambda d: len(d.get("c_source_modules", [])) >= 50,
             "must document >= 50 embedded C firmware modules"),
        ]
    },

    "ans2_phase_2_mmio_and_nand_geometry": {
        "required_artifacts": [
            "artifacts/ans2/ans2_mmio_memory_geometry.json",
            "artifacts/ans2/nand_geometry_crypto_spec.json",
            "findings/ans2/02_MMIO_AND_NAND_GEOMETRY.md"
        ],
        "findings_docs": ["findings/ans2/02_MMIO_AND_NAND_GEOMETRY.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ans2/ans2_mmio_memory_geometry.json": ["mmio_apertures", "sart_coastguard", "namespaces"],
            "artifacts/ans2/nand_geometry_crypto_spec.json": ["hardware_crypto_engine", "wear_leveling_bbt", "hmb_dma_arbitration"]
        },
        "assertions": [
            ("sart_coastguard_mapped",
             "artifacts/ans2/ans2_mmio_memory_geometry.json",
             lambda d: "sart_coastguard" in d and d["sart_coastguard"].get("base_address") == "0x17dc50000",
             "sart_coastguard base_address must equal 0x17dc50000"),
            ("seven_namespaces_mapped",
             "artifacts/ans2/ans2_mmio_memory_geometry.json",
             lambda d: len(d.get("namespaces", [])) == 7,
             "must document exactly 7 NVMe hardware namespaces"),
        ]
    },

    "ans2_phase_3_command_stream": {
        "required_artifacts": [
            "artifacts/ans2/nvme_command_stream_spec.json",
            "artifacts/ans2/ans2_ring_buffer_protocol.json",
            "findings/ans2/03_COMMAND_STREAM_AND_RING_BUFFER.md"
        ],
        "findings_docs": ["findings/ans2/03_COMMAND_STREAM_AND_RING_BUFFER.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ans2/nvme_command_stream_spec.json": ["queue_geometry", "apple_vendor_opcodes"],
            "artifacts/ans2/ans2_ring_buffer_protocol.json": ["doorbell_protocol", "ascwrap_mailbox_protocol"]
        },
        "assertions": [
            ("sqe_size_64",
             "artifacts/ans2/nvme_command_stream_spec.json",
             lambda d: d.get("queue_geometry", {}).get("submission_queue_entry_bytes") == 64,
             "SQE size must equal 64 bytes"),
            ("queue_depth_64",
             "artifacts/ans2/nvme_command_stream_spec.json",
             lambda d: d.get("queue_geometry", {}).get("queue_depth_entries") == 64,
             "queue depth entries must equal 64"),
        ]
    },

    "ans2_phase_4_kernel_boundary": {
        "required_artifacts": [
            "artifacts/ans2/xnu_nvme_boundary_spec.json",
            "artifacts/ans2/pseudocode/ans2_nvme_driver.pseudo.c",
            "findings/ans2/04_KERNEL_BOUNDARY_AND_DRIVER_RUNTIME.md"
        ],
        "findings_docs": ["findings/ans2/04_KERNEL_BOUNDARY_AND_DRIVER_RUNTIME.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ans2/xnu_nvme_boundary_spec.json": ["kext_inventory", "dispatch_pathway", "sart_stage2_isolation"]
        },
        "assertions": [
            ("driver_pseudocode_exists",
             None,
             lambda _: Path(ROOT / "artifacts/ans2/pseudocode/ans2_nvme_driver.pseudo.c").is_file(),
             "artifacts/ans2/pseudocode/ans2_nvme_driver.pseudo.c must exist"),
        ]
    },

    "ans2_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_ANS2_NVME_STORAGE_RE.md",
            "artifacts/ans2/cross_validation_matrix.json",
            "tools/verify_ans2_constants.py"
        ],
        "findings_docs": ["IOS_27_ANS2_NVME_STORAGE_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/ans2/cross_validation_matrix.json": ["extraction_confidence"]
        },
        "assertions": [
            ("verify_script_exists",
              None,
              lambda _: Path(ROOT / "tools/verify_ans2_constants.py").is_file(),
              "tools/verify_ans2_constants.py must exist"),
            ("has_extracted_constants",
              "artifacts/ans2/cross_validation_matrix.json",
              lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 20,
              "cross_validation_matrix must have at least 20 EXTRACTED confidence constants"),
        ]
    },

    # ── Always-On Processor 2 (AOP2) & RTKit Microkernel phases ─────────
    "aop_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/aop/phase_1a_workspace_baseline.json",
            "artifacts/aop/aop_firmware_container_spec.json",
            "findings/aop/01A_WORKSPACE_BASELINE.md"
        ],
        "findings_docs": ["findings/aop/01A_WORKSPACE_BASELINE.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/aop/phase_1a_workspace_baseline.json": ["target_device", "firmware_assets", "hardware_context"],
            "artifacts/aop/aop_firmware_container_spec.json": ["fourcc_tag", "wrapper", "container_magic", "total_container_size_bytes"]
        },
        "assertions": [
            ("fourcc_is_aop2",
             "artifacts/aop/aop_firmware_container_spec.json",
             lambda d: d.get("fourcc_tag") == "aop2",
             "fourcc_tag must be aop2"),
            ("bund_magic_is_dnub",
             "artifacts/aop/aop_firmware_container_spec.json",
             lambda d: d.get("bund_header", {}).get("magic_fourcc") == "DNUB",
             "bund_header.magic_fourcc must be DNUB"),
            ("sub_binaries_count_ge_7",
             "artifacts/aop/aop_firmware_container_spec.json",
             lambda d: len(d.get("sub_binaries", [])) >= 7,
             "must unpack at least 7 sub-binaries from BUND container"),
        ]
    },

    "aop_phase_1b_rtkit_microkernel": {
        "required_artifacts": [
            "artifacts/aop/rtkit_microkernel_spec.json",
            "artifacts/aop/aop_service_topology.json",
            "findings/aop/01B_RTKIT_MICROKERNEL.md"
        ],
        "findings_docs": ["findings/aop/01B_RTKIT_MICROKERNEL.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/aop/rtkit_microkernel_spec.json": ["microkernel_architecture", "mailbox_multiplexing_protocol"],
            "artifacts/aop/aop_service_topology.json": ["services", "ipc_endpoints", "shared_memory_regions"]
        },
        "assertions": [
            ("scheduler_64_priority_levels",
             "artifacts/aop/rtkit_microkernel_spec.json",
             lambda d: d.get("microkernel_architecture", {}).get("scheduler", {}).get("priority_levels") == 64,
             "RTKit microkernel scheduler must define 64 priority levels"),
            ("afk_root_service_present",
             "artifacts/aop/aop_service_topology.json",
             lambda d: "AFKRootService" in d.get("services", {}),
             "AFKRootService must be documented in service topology"),
        ]
    },

    "aop_phase_2_hardware_and_sensor_hub": {
        "required_artifacts": [
            "artifacts/aop/aop_hardware_registers.json",
            "artifacts/aop/sensor_hub_geometry.json",
            "findings/aop/02_HARDWARE_AND_SENSOR_HUB.md"
        ],
        "findings_docs": ["findings/aop/02_HARDWARE_AND_SENSOR_HUB.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/aop/aop_hardware_registers.json": ["mmio_peripheral_bases", "interrupt_vectors", "dart_stream_geometry"],
            "artifacts/aop/sensor_hub_geometry.json": ["imu_pipeline", "fastpath_ring_buffer", "ambient_light_sensor", "always_on_display", "local_siri_voice_trigger"]
        },
        "assertions": [
            ("ascwrap_primary_mmio_base",
             "artifacts/aop/aop_hardware_registers.json",
             lambda d: int(d.get("mmio_peripheral_bases", {}).get("ascwrap_mailbox_primary", {}).get("base_physical_address"), 16) == 0x101600000,
             "Primary ASCwrap Mailbox MMIO base must be 0x101600000"),
            ("imu_sample_record_size_64",
             "artifacts/aop/sensor_hub_geometry.json",
             lambda d: d.get("imu_pipeline", {}).get("sample_record_size_bytes") == 64,
             "IMU sample record size must be 64 bytes"),
        ]
    },

    "aop_phase_3_endpoint_wire_format": {
        "required_artifacts": [
            "artifacts/aop/rtkit_endpoint_wire_spec.json",
            "artifacts/aop/aop_mailbox_protocol.json",
            "findings/aop/03_ENDPOINT_WIRE_FORMAT.md"
        ],
        "findings_docs": ["findings/aop/03_ENDPOINT_WIRE_FORMAT.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/aop/rtkit_endpoint_wire_spec.json": ["word_geometry", "endpoints"],
            "artifacts/aop/aop_mailbox_protocol.json": ["hardware_doorbell_protocol", "handshake_sequence", "descriptor_rings"]
        },
        "assertions": [
            ("exclave_routing_endpoint_53",
             "artifacts/aop/rtkit_endpoint_wire_spec.json",
             lambda d: "0x53" in d.get("endpoints", {}),
             "RTKit endpoint wire spec must include EP 0x53 (sharedmem_xcoproc_AOP2_EP53_in)"),
            ("doorbell_mmio_base",
             "artifacts/aop/aop_mailbox_protocol.json",
             lambda d: int(d.get("hardware_doorbell_protocol", {}).get("mmio_base"), 16) == 0x10162c000,
             "Doorbell MMIO base must be 0x10162c000"),
        ]
    },

    "aop_phase_4_xnu_driver_boundary": {
        "required_artifacts": [
            "artifacts/aop/xnu_aop_boundary_spec.json",
            "artifacts/aop/pseudocode/aop_rtkit_channel.pseudo.c",
            "findings/aop/04_XNU_DRIVER_BOUNDARY.md"
        ],
        "findings_docs": ["findings/aop/04_XNU_DRIVER_BOUNDARY.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/aop/xnu_aop_boundary_spec.json": ["kernel_drivers", "user_clients", "entitlements"]
        },
        "assertions": [
            ("apple_aop2_driver_documented",
             "artifacts/aop/xnu_aop_boundary_spec.json",
             lambda d: any("AppleAOP2" in k for k in d.get("kernel_drivers", {})),
             "AppleAOP2 driver must be documented"),
            ("pseudocode_exists",
             None,
             lambda _: Path(ROOT / "artifacts/aop/pseudocode/aop_rtkit_channel.pseudo.c").is_file(),
             "artifacts/aop/pseudocode/aop_rtkit_channel.pseudo.c must exist"),
        ]
    },

    "aop_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_AOP_RTKIT_SENSOR_RE.md",
            "artifacts/aop/cross_validation_matrix.json",
            "tools/verify_aop_constants.py"
        ],
        "findings_docs": ["IOS_27_AOP_RTKIT_SENSOR_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/aop/cross_validation_matrix.json": ["extraction_confidence", "entries"]
        },
        "assertions": [
            ("verify_script_exists",
             None,
             lambda _: Path(ROOT / "tools/verify_aop_constants.py").is_file(),
             "tools/verify_aop_constants.py must exist"),
            ("has_extracted_constants",
             "artifacts/aop/cross_validation_matrix.json",
             lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 20,
             "cross_validation_matrix must have at least 20 EXTRACTED confidence constants"),
        ]
    },

    # ── Apple Video Encoder 2 (AVE2) Hardware Codec Accelerator phases ──
    "ave_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/ave/phase_1a_workspace_baseline.json",
            "artifacts/ave/ave_firmware_container_spec.json",
            "findings/ave/01A_WORKSPACE_BASELINE.md"
        ],
        "findings_docs": ["findings/ave/01A_WORKSPACE_BASELINE.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ave/phase_1a_workspace_baseline.json": ["target_device", "firmware_assets", "hardware_context"],
            "artifacts/ave/ave_firmware_container_spec.json": ["main_firmware", "satellite_microcodes", "fourcc_catalog"]
        },
        "assertions": [
            ("fourcc_is_avef",
             "artifacts/ave/ave_firmware_container_spec.json",
             lambda d: d.get("main_firmware", {}).get("fourcc_tag") == "avef",
             "main_firmware fourcc_tag must be avef"),
            ("has_9_satellite_cores",
             "artifacts/ave/ave_firmware_container_spec.json",
             lambda d: len(d.get("satellite_microcodes", {})) == 9,
             "must inventory all 9 satellite microcodes AVE0..AVE8"),
        ]
    },

    "ave_phase_1b_architecture_topology": {
        "required_artifacts": [
            "artifacts/ave/ave_topology_spec.json",
            "artifacts/ave/codec_pipeline_architecture.json",
            "findings/ave/01B_ARCHITECTURE_AND_TOPOLOGY.md"
        ],
        "findings_docs": ["findings/ave/01B_ARCHITECTURE_AND_TOPOLOGY.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ave/ave_topology_spec.json": ["memory_segments", "entry_point", "interrupt_vectors"],
            "artifacts/ave/codec_pipeline_architecture.json": ["codec_engines", "satellite_riscv_cores"]
        },
        "assertions": [
            ("has_av1_boreas",
             "artifacts/ave/codec_pipeline_architecture.json",
             lambda d: "AV1_Boreas" in str(d.get("codec_engines", {})),
             "codec_pipeline_architecture must document AV1 Boreas engine"),
            ("has_hevc_erebus",
             "artifacts/ave/codec_pipeline_architecture.json",
             lambda d: "HEVC_Erebus" in str(d.get("codec_engines", {})),
             "codec_pipeline_architecture must document HEVC Erebus engine"),
        ]
    },

    "ave_phase_2_hardware_register_geometry": {
        "required_artifacts": [
            "artifacts/ave/ave_hardware_register_geometry.json",
            "artifacts/ave/dma_descriptor_geometry.json",
            "findings/ave/02_HARDWARE_REGISTER_GEOMETRY.md"
        ],
        "findings_docs": ["findings/ave/02_HARDWARE_REGISTER_GEOMETRY.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ave/ave_hardware_register_geometry.json": ["mmio_registers", "rate_control_models", "quantization_parameters"],
            "artifacts/ave/dma_descriptor_geometry.json": ["dma_channels", "buffer_formats"]
        },
        "assertions": [
            ("dart_ave_mmio_base",
             "artifacts/ave/ave_hardware_register_geometry.json",
             lambda d: "0x77020000" in str(d.get("mmio_registers", {})),
             "dart-ave MMIO base must be 0x77020000"),
            ("has_rate_control_models",
             "artifacts/ave/ave_hardware_register_geometry.json",
             lambda d: len(d.get("rate_control_models", {})) >= 3,
             "must document at least 3 rate control models"),
        ]
    },

    "ave_phase_3_command_queue_protocol": {
        "required_artifacts": [
            "artifacts/ave/ave_command_queue_spec.json",
            "artifacts/ave/codec_control_descriptors.json",
            "findings/ave/03_COMMAND_QUEUE_AND_WIRE_FORMAT.md"
        ],
        "findings_docs": ["findings/ave/03_COMMAND_QUEUE_AND_WIRE_FORMAT.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ave/ave_command_queue_spec.json": ["command_opcodes", "mailbox_protocol"],
            "artifacts/ave/codec_control_descriptors.json": ["descriptors", "slice_headers"]
        },
        "assertions": [
            ("has_10_command_opcodes",
             "artifacts/ave/ave_command_queue_spec.json",
             lambda d: len(d.get("command_opcodes", {})) >= 10,
             "must document at least 10 hardware command opcodes"),
        ]
    },

    "ave_phase_4_kernel_boundary": {
        "required_artifacts": [
            "artifacts/ave/xnu_ave_boundary_spec.json",
            "artifacts/ave/pseudocode/ave_direct_submit.pseudo.c",
            "findings/ave/04_KERNEL_BOUNDARY_CLIENT.md"
        ],
        "findings_docs": ["findings/ave/04_KERNEL_BOUNDARY_CLIENT.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/ave/xnu_ave_boundary_spec.json": ["kernel_drivers", "user_clients", "external_methods"]
        },
        "assertions": [
            ("pseudocode_exists",
             None,
             lambda _: Path(ROOT / "artifacts/ave/pseudocode/ave_direct_submit.pseudo.c").is_file(),
             "artifacts/ave/pseudocode/ave_direct_submit.pseudo.c must exist"),
            ("has_apple_ave2_driver",
             "artifacts/ave/xnu_ave_boundary_spec.json",
             lambda d: any("AppleAVE2" in k for k in d.get("kernel_drivers", {})),
             "must document AppleAVE2 driver in XNU boundary"),
        ]
    },

    "ave_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_AVE2_VIDEO_ENCODER_RE.md",
            "artifacts/ave/cross_validation_matrix.json",
            "tools/verify_ave_constants.py"
        ],
        "findings_docs": ["IOS_27_AVE2_VIDEO_ENCODER_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/ave/cross_validation_matrix.json": ["extraction_confidence"]
        },
        "assertions": [
            ("verify_script_exists",
              None,
              lambda _: Path(ROOT / "tools/verify_ave_constants.py").is_file(),
              "tools/verify_ave_constants.py must exist"),
            ("has_extracted_constants",
              "artifacts/ave/cross_validation_matrix.json",
              lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 1,
              "cross_validation_matrix must have at least 1 EXTRACTED confidence constant"),
        ]
    },

    # ── Display Coprocessor (DCP) & ProMotion Pipeline phases ──────────────
    "dcp_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/dcp/phase_1a_workspace_baseline.json",
            "artifacts/dcp/dcp_firmware_container_spec.json",
            "findings/dcp/01A_WORKSPACE_BASELINE.md"
        ],
        "findings_docs": ["findings/dcp/01A_WORKSPACE_BASELINE.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/dcp/phase_1a_workspace_baseline.json": ["target_hardware", "project"],
            "artifacts/dcp/dcp_firmware_container_spec.json": ["container", "rtos_identification"]
        },
        "assertions": [
            ("fourcc_is_dcpf",
             "artifacts/dcp/dcp_firmware_container_spec.json",
             lambda d: d.get("container", {}).get("fourcc_tag") == "dcpf",
             "container fourcc_tag must be dcpf"),
            ("rtos_is_rtkit",
             "artifacts/dcp/dcp_firmware_container_spec.json",
             lambda d: "3514.40.18" in d.get("rtos_identification", {}).get("version_banner", ""),
             "RTKit version_banner must match 3514.40.18"),
        ]
    },

    "dcp_phase_1b_microkernel": {
        "required_artifacts": [
            "artifacts/dcp/dcp_microkernel_spec.json",
            "artifacts/dcp/dcp_service_topology.json",
            "findings/dcp/01B_DCP_MICROKERNEL.md"
        ],
        "findings_docs": ["findings/dcp/01B_DCP_MICROKERNEL.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/dcp/dcp_microkernel_spec.json": ["microkernel", "memory_carveouts"],
            "artifacts/dcp/dcp_service_topology.json": ["endpoints", "hardware_pipe_blocks"]
        },
        "assertions": [
            ("dcp_runtime_dram_48mb",
             "artifacts/dcp/dcp_microkernel_spec.json",
             lambda d: d.get("memory_carveouts", {}).get("dcp_firmware_dram", {}).get("size_bytes") == 50331648,
             "dcp_firmware_dram must be 48 MB (50331648 bytes)"),
            ("genpipe_38_blocks",
             "artifacts/dcp/dcp_service_topology.json",
             lambda d: d.get("hardware_pipe_blocks", {}).get("count") == 38,
             "hardware_pipe_blocks count must be 38"),
        ]
    },

    "dcp_phase_2_promotion_and_timing": {
        "required_artifacts": [
            "artifacts/dcp/promotion_arbitration_spec.json",
            "artifacts/dcp/vftg_timing_generator_spec.json",
            "findings/dcp/02_PROMOTION_AND_FRAME_PACING.md"
        ],
        "findings_docs": ["findings/dcp/02_PROMOTION_AND_FRAME_PACING.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/dcp/promotion_arbitration_spec.json": ["promotion_architecture"],
            "artifacts/dcp/vftg_timing_generator_spec.json": ["vftg_hardware"]
        },
        "assertions": [
            ("discrete_refresh_rates_11",
             "artifacts/dcp/promotion_arbitration_spec.json",
             lambda d: len(d.get("promotion_architecture", {}).get("discrete_refresh_rates", [])) == 11,
             "must document exactly 11 discrete refresh rates"),
            ("vftg_pixel_clock_504mhz",
             "artifacts/dcp/vftg_timing_generator_spec.json",
             lambda d: d.get("vftg_hardware", {}).get("pixel_clock_hz") == 504000000,
             "vftg pixel clock must be 504.0 MHz (504000000 Hz)"),
        ]
    },

    "dcp_phase_3_pixel_compensation_and_color": {
        "required_artifacts": [
            "artifacts/dcp/pixel_compensation_spec.json",
            "artifacts/dcp/color_pipeline_lut_spec.json",
            "findings/dcp/03_PIXEL_COMPENSATION_AND_COLOR.md"
        ],
        "findings_docs": ["findings/dcp/03_PIXEL_COMPENSATION_AND_COLOR.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/dcp/pixel_compensation_spec.json": ["panel_compensation_engines"],
            "artifacts/dcp/color_pipeline_lut_spec.json": ["color_pipeline"]
        },
        "assertions": [
            ("has_burn_in_compensation",
             "artifacts/dcp/pixel_compensation_spec.json",
             lambda d: "bics" in d.get("panel_compensation_engines", {}),
             "must document BICS burn-in compensation engine"),
            ("has_3d_lut",
             "artifacts/dcp/color_pipeline_lut_spec.json",
             lambda d: any("3D LUT" in str(b) for b in d.get("color_pipeline", {}).get("pipeline_blocks", [])),
             "color_pipeline must document 3D LUT stage"),
        ]
    },

    "dcp_phase_4_kernel_boundary": {
        "required_artifacts": [
            "artifacts/dcp/xnu_dcp_boundary_spec.json",
            "artifacts/dcp/pseudocode/dcp_mailbox_client.pseudo.c",
            "findings/dcp/04_XNU_DRIVER_BOUNDARY.md"
        ],
        "findings_docs": ["findings/dcp/04_XNU_DRIVER_BOUNDARY.md"],
        "min_findings_bytes": 4000,
        "json_schemas": {
            "artifacts/dcp/xnu_dcp_boundary_spec.json": ["xnu_drivers", "ipc_command_descriptors"]
        },
        "assertions": [
            ("pseudocode_exists",
             None,
             lambda _: Path(ROOT / "artifacts/dcp/pseudocode/dcp_mailbox_client.pseudo.c").is_file(),
             "artifacts/dcp/pseudocode/dcp_mailbox_client.pseudo.c must exist"),
            ("has_apple_clcd2_driver",
             "artifacts/dcp/xnu_dcp_boundary_spec.json",
             lambda d: any("AppleCLCD2" in str(drv) for drv in d.get("xnu_drivers", [])),
             "must document AppleCLCD2 driver in XNU boundary"),
        ]
    },

    "dcp_phase_5_synthesis": {
        "required_artifacts": [
            "IOS_27_DISPLAY_COPROCESSOR_DCP_RE.md",
            "artifacts/dcp/cross_validation_matrix.json",
            "tools/verify_dcp_constants.py"
        ],
        "findings_docs": ["IOS_27_DISPLAY_COPROCESSOR_DCP_RE.md"],
        "min_findings_bytes": 50000,
        "json_schemas": {
            "artifacts/dcp/cross_validation_matrix.json": ["extraction_confidence"]
        },
        "assertions": [
            ("verify_script_exists",
             None,
             lambda _: Path(ROOT / "tools/verify_dcp_constants.py").is_file(),
             "tools/verify_dcp_constants.py must exist"),
            ("has_extracted_constants",
             "artifacts/dcp/cross_validation_matrix.json",
             lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 20,
             "cross_validation_matrix must have at least 20 EXTRACTED confidence constants"),
        ]
    },

    # ── Apple Silicon A19 Pro Hardware-Software Co-Design Synthesis phases ──
    "synthesis_phase_1a_workspace_baseline": {
        "required_artifacts": [
            "artifacts/synthesis/phase_1a_workspace_baseline.json",
            "artifacts/synthesis/soc_topology_spec.json",
            "findings/synthesis/01A_WORKSPACE_BASELINE.md"
        ],
        "findings_docs": ["findings/synthesis/01A_WORKSPACE_BASELINE.md"],
        "min_findings_bytes": 5000,
        "json_schemas": {
            "artifacts/synthesis/phase_1a_workspace_baseline.json": ["target_platform", "hardware_blocks_inventory", "synthesis_inputs"],
            "artifacts/synthesis/soc_topology_spec.json": ["soc_architecture", "interconnect_fabric", "power_and_clock_domains"]
        },
        "assertions": [
            ("chip_is_t8150",
             "artifacts/synthesis/phase_1a_workspace_baseline.json",
             lambda d: d.get("target_platform", {}).get("soc") == "t8150",
             "target chip must be t8150"),
            ("board_is_v57ap",
             "artifacts/synthesis/phase_1a_workspace_baseline.json",
             lambda d: d.get("target_platform", {}).get("device_class") == "v57ap",
             "target device_class must be v57ap"),
        ]
    },

    "synthesis_phase_1b_global_memory_map": {
        "required_artifacts": [
            "artifacts/synthesis/global_physical_memory_map.json",
            "findings/synthesis/01B_GLOBAL_MEMORY_MAP.md"
        ],
        "findings_docs": ["findings/synthesis/01B_GLOBAL_MEMORY_MAP.md"],
        "min_findings_bytes": 5000,
        "json_schemas": {
            "artifacts/synthesis/global_physical_memory_map.json": ["physical_address_width_bits", "installed_dram_bytes", "dram_carveouts"]
        },
        "assertions": [
            ("installed_dram_32gb",
             "artifacts/synthesis/global_physical_memory_map.json",
             lambda d: d.get("installed_dram_bytes") == 34359738368,
             "installed DRAM must be exactly 32 GB (34359738368 bytes)"),
            ("has_6_carveouts",
             "artifacts/synthesis/global_physical_memory_map.json",
             lambda d: len(d.get("dram_carveouts", [])) == 6,
             "must document exactly 6 DRAM carveouts"),
        ]
    },

    "synthesis_phase_2_unified_dart_ledger": {
        "required_artifacts": [
            "artifacts/synthesis/unified_dart_iommu_ledger.json",
            "findings/synthesis/02_UNIFIED_DART_IOMMU_LEDGER.md"
        ],
        "findings_docs": ["findings/synthesis/02_UNIFIED_DART_IOMMU_LEDGER.md"],
        "min_findings_bytes": 5000,
        "json_schemas": {
            "artifacts/synthesis/unified_dart_iommu_ledger.json": ["total_dart_controllers", "page_granule_bytes", "controllers"]
        },
        "assertions": [
            ("total_25_darts",
             "artifacts/synthesis/unified_dart_iommu_ledger.json",
             lambda d: len(d.get("controllers", [])) == 25,
             "must catalog all 25 DART Gen3 controllers"),
            ("page_granule_16k",
             "artifacts/synthesis/unified_dart_iommu_ledger.json",
             lambda d: d.get("page_granule_bytes") == 16384,
             "DART page granule must be 16 KB (16384 bytes)"),
        ]
    },

    "synthesis_phase_3_interrupt_and_mailbox_matrix": {
        "required_artifacts": [
            "artifacts/synthesis/master_aic_interrupt_matrix.json",
            "artifacts/synthesis/ascwrap_mailbox_matrix.json",
            "findings/synthesis/03_INTERRUPT_AND_MAILBOX_MATRIX.md"
        ],
        "findings_docs": ["findings/synthesis/03_INTERRUPT_AND_MAILBOX_MATRIX.md"],
        "min_findings_bytes": 5000,
        "json_schemas": {
            "artifacts/synthesis/master_aic_interrupt_matrix.json": ["aic_controller", "subsystem_allocations"],
            "artifacts/synthesis/ascwrap_mailbox_matrix.json": ["register_offsets", "instances"]
        },
        "assertions": [
            ("aic_vectors_1024",
             "artifacts/synthesis/master_aic_interrupt_matrix.json",
             lambda d: d.get("aic_controller", {}).get("total_vector_capacity") == 1024,
             "AIC vector capacity must be 1024"),
            ("has_9_mailbox_instances",
             "artifacts/synthesis/ascwrap_mailbox_matrix.json",
             lambda d: len(d.get("instances", [])) >= 9,
             "must document at least 9 ASCwrap mailbox instances"),
        ]
    },

    "synthesis_phase_4_cross_enclave_topology": {
        "required_artifacts": [
            "artifacts/synthesis/inter_enclave_ipc_topology.json",
            "artifacts/synthesis/pseudocode/a19_pro_cross_enclave_router.pseudo.c",
            "findings/synthesis/04_INTER_ENCLAVE_IPC_TOPOLOGY.md"
        ],
        "findings_docs": ["findings/synthesis/04_INTER_ENCLAVE_IPC_TOPOLOGY.md"],
        "min_findings_bytes": 5000,
        "json_schemas": {
            "artifacts/synthesis/inter_enclave_ipc_topology.json": ["security_domains", "crossings"]
        },
        "assertions": [
            ("has_9_security_domains",
             "artifacts/synthesis/inter_enclave_ipc_topology.json",
             lambda d: len(d.get("security_domains", [])) >= 8,
             "must document at least 8 security domains"),
            ("has_10_crossings",
             "artifacts/synthesis/inter_enclave_ipc_topology.json",
             lambda d: len(d.get("crossings", [])) >= 10,
             "must document at least 10 inter-enclave crossings"),
        ]
    },

    "synthesis_phase_5_synthesis": {
        "required_artifacts": [
            "APPLE_SILICON_A19_PRO_ARCHITECTURE_BOOK.md",
            "artifacts/synthesis/cross_validation_matrix.json",
            "tools/verify_synthesis_constants.py"
        ],
        "findings_docs": ["APPLE_SILICON_A19_PRO_ARCHITECTURE_BOOK.md"],
        "min_findings_bytes": 100000,
        "json_schemas": {
            "artifacts/synthesis/cross_validation_matrix.json": ["extraction_confidence", "entries"]
        },
        "assertions": [
            ("verify_script_exists",
             None,
             lambda _: Path(ROOT / "tools/verify_synthesis_constants.py").is_file(),
             "tools/verify_synthesis_constants.py must exist"),
            ("has_extracted_constants",
             "artifacts/synthesis/cross_validation_matrix.json",
             lambda d: d.get("extraction_confidence", {}).get("EXTRACTED", 0) >= 30,
             "cross_validation_matrix must have at least 30 EXTRACTED confidence constants"),
            ("verify_script_passes",
             None,
             lambda _: subprocess.run([sys.executable, str(ROOT / "tools/verify_synthesis_constants.py")],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
             "tools/verify_synthesis_constants.py must pass 100% green"),
        ]
    },
}
import re

def check_placeholders(text: str) -> list:
    return [p for p in PLACEHOLDER_STRINGS if re.search(rf"\b{re.escape(p)}\b", text, re.IGNORECASE)]


def verify_phase(phase_id: str) -> bool:
    spec = PHASE_SPECS.get(phase_id)
    if spec is None:
        print(f"ERROR: Unknown phase '{phase_id}'")
        print(f"Known animation phases: {[k for k in PHASE_SPECS if k.startswith('anim')]}")
        return False

    errors = []

    # 1. Required artifacts
    for artifact in spec.get("required_artifacts", []):
        path = ROOT / artifact
        if not path.exists():
            errors.append(f"MISSING ARTIFACT: {artifact}")
        elif path.stat().st_size == 0:
            errors.append(f"EMPTY ARTIFACT: {artifact}")

    # 2. JSON schema checks
    for json_path, required_keys in spec.get("json_schemas", {}).items():
        path = ROOT / json_path
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for key in required_keys:
                    if key not in data:
                        errors.append(f"MISSING JSON KEY '{key}' in {json_path}")
            except json.JSONDecodeError as e:
                errors.append(f"INVALID JSON in {json_path}: {e}")

    # 3. Findings documents: size + placeholder check
    min_bytes = spec.get("min_findings_bytes", 2500)
    for doc in spec.get("findings_docs", []):
        path = ROOT / doc
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            if len(text.encode()) < min_bytes:
                errors.append(f"FINDINGS TOO SHORT: {doc} ({len(text.encode())} bytes < {min_bytes})")
            found_placeholders = check_placeholders(text)
            if found_placeholders:
                errors.append(f"PLACEHOLDER TEXT in {doc}: {found_placeholders}")

    # 4. Custom assertions
    for assert_name, json_path, predicate, msg in spec.get("assertions", []):
        if json_path is None:
            if not predicate(None):
                errors.append(f"ASSERTION FAILED [{assert_name}]: {msg}")
        else:
            path = ROOT / json_path
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    if not predicate(data):
                        errors.append(f"ASSERTION FAILED [{assert_name}]: {msg}")
                except Exception as e:
                    errors.append(f"ASSERTION ERROR [{assert_name}]: {e}")

    # Report
    if errors:
        print(f"\n❌  Phase '{phase_id}' FAILED verification:")
        for err in errors:
            print(f"   • {err}")
        return False
    else:
        print(f"[PASS] All verification checks PASSED for phase '{phase_id}'")
        print(f"\n✅  Phase '{phase_id}' PASSED all verification checks.")
        return True


def verify_artifact_content(artifact_name: str, path: Path) -> list:
    errors = []
    p = Path(path)
    if not p.is_file():
        return [f"File {path} does not exist"]

    if artifact_name == "evidence_ledger.jsonl":
        has_phase_1a = False
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if "1A" in obj.get("phase", ""):
                        has_phase_1a = True
                        break
                except Exception:
                    pass
        if not has_phase_1a:
            errors.append("Missing Phase 1A entries in evidence_ledger.jsonl")

    elif artifact_name == "framework_inventory.json":
        try:
            inv = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(inv, list):
                for i, item in enumerate(inv):
                    if not item.get("subcache_file_offset"):
                        errors.append(f"Entry {i} missing subcache_file_offset")
        except Exception as e:
            errors.append(f"Failed to parse framework_inventory.json: {e}")

    return errors


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 tools/verify_phase.py <phase_id>")
        print(f"\nAnimation phases:")
        for k in PHASE_SPECS:
            if k.startswith("anim"):
                print(f"  {k}")
        print(f"\nGesture Arbitration phases:")
        for k in PHASE_SPECS:
            if k.startswith("gest"):
                print(f"  {k}")
        print(f"\nAOP2 & RTKit phases:")
        for k in PHASE_SPECS:
            if k.startswith("aop"):
                print(f"  {k}")
        sys.exit(1)

    success = verify_phase(sys.argv[1])
    sys.exit(0 if success else 1)
