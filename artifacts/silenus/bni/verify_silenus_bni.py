#!/usr/bin/env python3
"""
verify_silenus_bni.py - Standalone Verification Test Suite
Subsystem: Bayer Neural Interface (BNI) & Hardware Neural Accelerator Bridge
Silicon Target: Apple H18 ISP (Silenus v57)
Firmware Binary: artifacts/silenus/bni/adc-silenus-v57.macho
Dossier: findings/silenus/03_BAYER_NEURAL_INTERFACE_BNI.md
"""

import os
import sys
import json
import struct

def test_binary_integrity():
    print("[TEST 1/7] Validating Raw Mach-O Firmware Binary Integrity...")
    bin_path = "artifacts/silenus/bni/adc-silenus-v57.macho"
    assert os.path.exists(bin_path), f"Binary {bin_path} does not exist"
    size = os.path.getsize(bin_path)
    assert size == 29016064, f"Unexpected binary size: {size} (expected 29,016,064 bytes)"
    
    with open(bin_path, "rb") as f:
        header = f.read(32)
    magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, reserved = struct.unpack("<IIIIIIII", header)
    assert magic == 0xfeedfacf, f"Invalid Mach-O 64 magic: 0x{magic:x}"
    assert cputype == 0x100000c, f"Invalid CPU type ARM64: 0x{cputype:x}"
    assert filetype == 0x5, f"Expected MH_PRELOAD filetype (0x5), got 0x{filetype:x}"
    print(f"  --> Binary OK: 64-bit MH_PRELOAD ARM64e RTKit ({size:,} bytes, {ncmds} load commands)")

def test_bni_dma_architecture():
    print("[TEST 2/7] Validating BNI Direct DMA Channel Matrix & Tile Geometries...")
    spec_path = "artifacts/silenus/bni/bni_dma_architecture_spec.json"
    assert os.path.exists(spec_path), f"Spec {spec_path} missing"
    with open(spec_path, "r") as f:
        spec = json.load(f)
    
    matrix = spec["dma_channels_matrix"]
    assert len(matrix) == 249, f"Expected exactly 249 DMA channels, got {len(matrix)}"
    
    channel_lookup = {c["channel_id"]: c["name"] for c in matrix}
    assert channel_lookup[0] == "DeTilePipeDmaSrcLuma0"
    assert channel_lookup[1] == "DeTilePipeDmaSrcChroma0"
    assert channel_lookup[10] == "PatchWarperDmaSrc"
    assert channel_lookup[11] == "PatchWarperCoordDmaSrc"
    assert channel_lookup[12] == "NCCDmaSrc"
    assert channel_lookup[13] == "NCCFeatureDmaSrc"
    assert channel_lookup[50] == "PatchWarperDmaDst"
    assert channel_lookup[51] == "NCCMaxLocDmaDst"
    assert channel_lookup[52] == "NCCOutMapDmaDst"
    assert channel_lookup[165] == "SMGPipeInputDmaSrc"
    assert channel_lookup[168] == "BayerProcLSCDmaSrc"
    assert channel_lookup[169] == "BayerProcHRDmaSrc"
    assert channel_lookup[184] == "MsFeProcMeshDmaSrc"
    assert channel_lookup[224] == "SMGPipeDmaDst"
    assert channel_lookup[225] == "BayerProcHRDDmaDstGNU"
    assert channel_lookup[228] == "BayerProcDmaDstPlaEvenQuad"
    assert channel_lookup[229] == "BayerProcDmaDstPlaOddQuad"
    assert channel_lookup[230] == "PyrOutProcDmaDstA0"
    assert channel_lookup[248] == "MsBeProcFARDmaDstB"
    
    with open("artifacts/silenus/bni/adc-silenus-v57.macho", "rb") as f:
        data = f.read()
    
    start_off = 0x158c0cd
    for i in range(249):
        entry_off = start_off + i * 32
        name = data[entry_off:entry_off+32].split(b'\x00')[0].decode('ascii')
        assert name == channel_lookup[i], f"Mismatch at channel {i}: binary={name}, spec={channel_lookup[i]}"
        
    print(f"  --> BNI DMA OK: 249/249 channels match exact binary addresses and order")

def test_deep_fusion_alignment():
    print("[TEST 3/7] Validating Deep Fusion MSTF 6-Level Pyramid & Optical Flow Specs...")
    spec_path = "artifacts/silenus/bni/deep_fusion_alignment_spec.json"
    assert os.path.exists(spec_path), f"Spec {spec_path} missing"
    with open(spec_path, "r") as f:
        spec = json.load(f)
    
    hierarchy = spec["mstf_pipeline_architecture"]["pyramid_scale_hierarchy"]
    assert hierarchy["total_scales"] == 6, "Expected 6 pyramid scales"
    scales = hierarchy["scales"]
    assert len(scales) == 6
    assert scales[0]["level"].startswith("Scale A")
    assert scales[5]["level"].startswith("Scale F")
    
    with open("artifacts/silenus/bni/adc-silenus-v57.macho", "rb") as f:
        data = f.read()
    assert b"CmdStartMSTF: ch=%d,numOfScales=%d,bLumaOnly=%d,bComp=%d,bCTFCircularEn=%d" in data
    assert b"VFLOWH18_BUFFER_POOL_PYROUTPROC1_SCALE0" in data
    assert b"VFLOWH18_BUFFER_POOL_PYROUTPROC1_SCALE1" in data
    assert b"VFLOWH18_BUFFER_POOL_PYROUTPROC1_SCALE2TO5" in data
    assert b"MsFeProcMeshDmaSrc" in data
    assert b"PatchWarperCoordDmaSrc" in data
    assert b"NCCMaxLocDmaDst" in data
    print("  --> Deep Fusion MSTF OK: 6-level pyramid, patch warper, and NCC matching verified")

def test_semantic_segmentation():
    print("[TEST 4/7] Validating Real-Time 60fps Semantic Segmentation Masks & ANE Pipeline...")
    spec_path = "artifacts/silenus/bni/semantic_segmentation_spec.json"
    assert os.path.exists(spec_path), f"Spec {spec_path} missing"
    with open(spec_path, "r") as f:
        spec = json.load(f)
        
    masks = spec["eight_distinct_semantic_masks"]
    assert len(masks) == 8, f"Expected 8 semantic masks, got {len(masks)}"
    
    expected_mask_names = ["Skin", "Hair", "Eyes", "Teeth", "Clothes", "Sky", "Foliage", "Background / Depth"]
    for i, exp in enumerate(expected_mask_names):
        assert exp.split()[0].lower() in masks[i]["name"].lower(), f"Mask {i} name mismatch: {masks[i]['name']} vs {exp}"
        
    with open("artifacts/silenus/bni/adc-silenus-v57.macho", "rb") as f:
        data = f.read()
    assert b"ANE_Semantic_Video" in data
    assert b"ANE_Semantic_Video_CVPipe0" in data
    assert b"AICam can not keep up, drop semantic video and pyramid output" in data
    assert b"AICam drop-oldest recovery: drained=%d repost_rc=%d" in data
    assert b"SMV:ppl:%zu,hr:%zu,skin:%zu,sky:%zu" in data
    assert b"BPskinSMV" in data
    assert b"BPhairSMV" in data
    assert b"BPpeopleSMV" in data
    assert b"BPskySMV" in data
    assert b"AWBSemanticConfidenceMap2AWB" in data
    print("  --> Semantic Segmentation OK: 8/8 masks, ANE 60fps pipeline, and drop recovery verified")

def test_zsl_ring_buffer():
    print("[TEST 5/7] Validating Zero-Shutter-Lag (ZSL) Circular Ring Buffer Topography...")
    spec_path = "artifacts/silenus/bni/zsl_ring_buffer_spec.json"
    assert os.path.exists(spec_path), f"Spec {spec_path} missing"
    with open(spec_path, "r") as f:
        spec = json.load(f)
        
    zsl = spec["zsl_ring_buffer_architecture"]
    assert zsl["ring_buffer_core_class"] == "CIOPRingBuffer"
    assert zsl["replay_dma_architecture"]["command_name"] == "CISP_CMD_CH_REPLAY_SIFDMA_ENABLE"
    
    with open("artifacts/silenus/bni/adc-silenus-v57.macho", "rb") as f:
        data = f.read()
    assert b"./ffw64_rtxc/ffw/CIOPRingBuffer.cpp" in data
    assert b"((IOP_RINGBUFFER_VERSION_V2 == (pBuf->_header._version>>16))" in data
    assert b"pBuf->_header._rdptr + GET_CACHE_LINE_ALGIN_SIZE(sizeof(sIOPRingBufferMsgHeaderV2_t) + payloadSize) <= localCopyWrPtr" in data
    assert b"ISP_PROPERTY_CTF_CIRCULAR_BUFFER_ENABLE" in data
    assert b"CISP_CMD_CH_REPLAY_SIFDMA_ENABLE" in data
    print("  --> ZSL Ring Buffer OK: CIOPRingBuffer C++ logic, header structures, and replay DMA verified")

def test_master_dossier():
    print("[TEST 6/7] Validating Master Dossier 03_BAYER_NEURAL_INTERFACE_BNI.md...")
    dossier_path = "findings/silenus/03_BAYER_NEURAL_INTERFACE_BNI.md"
    assert os.path.exists(dossier_path), f"Master dossier {dossier_path} missing"
    size = os.path.getsize(dossier_path)
    assert size >= 40000, f"Dossier size {size} is less than required 40,000 bytes threshold"
    
    with open(dossier_path, "r") as f:
        text = f.read()
        
    required_sections = [
        "Executive Summary & Silicon Architecture Overview",
        "Phase 3A — Bayer Neural Interface (BNI) Direct DMA Architecture",
        "Phase 3B — Deep Fusion Multi-Frame Alignment",
        "Phase 3C — Real-Time Semantic Segmentation Mask Pipeline",
        "Phase 3D — Zero-Shutter-Lag (ZSL) Ring Buffer Topography",
        "Comprehensive C/C++ Header Definitions & Register Map",
        "Verification Matrix & Reproduction Protocol"
    ]
    for sec in required_sections:
        assert sec in text, f"Missing required dossier section: '{sec}'"
        
    print(f"  --> Master Dossier OK: {size:,} bytes (exceeds 40KB minimum), all 7 core sections present")

def test_field_completeness():
    print("[TEST 7/7] Enforcing Field Completeness Across All Deliverables...")
    placeholder_tokens = ["TODO", "TBD", "placeholder", "WIP", "coming soon"]
    target_files = [
        "artifacts/silenus/bni/bni_dma_architecture_spec.json",
        "artifacts/silenus/bni/deep_fusion_alignment_spec.json",
        "artifacts/silenus/bni/semantic_segmentation_spec.json",
        "artifacts/silenus/bni/zsl_ring_buffer_spec.json",
        "findings/silenus/03_BAYER_NEURAL_INTERFACE_BNI.md"
    ]
    for p in target_files:
        with open(p, "r") as f:
            content = f.read()
        for token in placeholder_tokens:
            assert token not in content, f"Found placeholder '{token}' in {p}"
            assert token.lower() not in content.lower(), f"Found placeholder case-insensitive '{token}' in {p}"
    print("  --> Field Completeness OK: 100% concrete values across all deliverables")

if __name__ == "__main__":
    print("=== STARTING SILENUS BNI REVERSE ENGINEERING VERIFICATION SUITE ===")
    test_binary_integrity()
    test_bni_dma_architecture()
    test_deep_fusion_alignment()
    test_semantic_segmentation()
    test_zsl_ring_buffer()
    test_master_dossier()
    test_field_completeness()
    print("=== ALL 7/7 TESTS PASSED WITH 100% SUCCESS ===")
