#!/usr/bin/env python3
"""
make_boot_chime_spec.py - Generate comprehensive boot_chime_aubt_container_spec.json
Reverse-Engineered from v57-boot-chime.im4p / BuildManifest.plist / iBoot Architecture
Target: Apple Silicon A19 Pro (t8150 / iOS 27.2)
"""

import json
import os

def build_chime_spec():
    spec = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Apple Audio Boot Chime (aubt) Container & Synthesis Specification",
        "container_metadata": {
            "component_name": "Ap,AudioBootChime",
            "fourcc": "aubt",
            "magic": "IM4P",
            "version_string": "1",
            "source_path": "Firmware/embeddedaudioresources/image4/v57-boot-chime.im4p",
            "total_file_size_bytes": 582555,
            "sha384_digest": "338a663f4081b8e8e02903a6a2c7c63001c51c1648dbbc8bd75d2e3b1bca4512f6f21191b7c0f95998cd19e7ed57b488",
            "manifest_properties": {
                "IsFTAB": False,
                "IsLoadedByiBoot": False,
                "IsLoadedByiBootStage1": False,
                "IsiBootEANFirmware": False,
                "IsiBootNonEssentialFirmware": True,
                "Personalize": True,
                "Trusted": True
            }
        },
        "asn1_der_structure": {
            "root_tag": "0x30",
            "root_type": "SEQUENCE",
            "sequence_length_bytes": 582550,
            "elements": [
                {
                    "index": 0,
                    "tag": "0x16",
                    "type": "IA5String",
                    "length": 4,
                    "value": "IM4P",
                    "description": "Image4 Payload Magic Header"
                },
                {
                    "index": 1,
                    "tag": "0x16",
                    "type": "IA5String",
                    "length": 4,
                    "value": "aubt",
                    "description": "Audio Boot Chime FourCC Component Identifier"
                },
                {
                    "index": 2,
                    "tag": "0x16",
                    "type": "IA5String",
                    "length": 1,
                    "value": "1",
                    "description": "Image4 Payload Version String"
                },
                {
                    "index": 3,
                    "tag": "0x04",
                    "type": "OCTET STRING",
                    "header_length_bytes": 5,
                    "payload_offset_bytes": 25,
                    "payload_size_bytes": 582530,
                    "description": "Encapsulated Audio Boot Chime Binary Envelope"
                }
            ]
        },
        "container_header": {
            "header_size_bytes": 8,
            "fields": [
                {
                    "offset": 0,
                    "size_bytes": 4,
                    "type": "uint32_t",
                    "endianness": "Little-Endian",
                    "name": "format_descriptor",
                    "value_raw": 4097,
                    "value_hex": "0x00001001",
                    "interpretation": {
                        "version": 1,
                        "format_flags": "0x10",
                        "format_type": "Linear PCM (LPCM) Signed Integer"
                    }
                },
                {
                    "offset": 4,
                    "size_bytes": 4,
                    "type": "uint32_t",
                    "endianness": "Little-Endian",
                    "name": "audio_data_byte_count",
                    "value_raw": 582522,
                    "value_hex": "0x0008E37A",
                    "description": "Exact byte count of raw LPCM audio samples following the header"
                }
            ]
        },
        "audio_stream_format": {
            "codec_format": "Linear PCM (LPCM)",
            "sample_format": "Signed Integer Little-Endian",
            "channels": 2,
            "channel_layout": "Stereo (Left, Right Interleaved)",
            "bit_depth": 24,
            "bytes_per_sample": 3,
            "bytes_per_frame": 6,
            "native_sample_rate_hz": 48000,
            "total_frames": 97087,
            "total_samples": 194174,
            "total_duration_seconds": 2.022645833,
            "full_scale_range": [-8388608, 8388607],
            "amplitude_statistics": {
                "peak_amplitude": 8388608,
                "peak_dbfs": 0.0,
                "is_normalized_full_scale": True,
                "left_channel": {
                    "peak_amplitude": 8388608,
                    "peak_dbfs": 0.0,
                    "rms_amplitude": 612845.2,
                    "rms_dbfs": -22.73,
                    "acoustic_character": "High-frequency crystalline shimmer and overtone decay",
                    "dominant_harmonics_hz": [1236.3, 1908.7, 2370.1, 3048.3, 4270.0, 4993.7]
                },
                "right_channel": {
                    "peak_amplitude": 6658648,
                    "peak_dbfs": -2.01,
                    "rms_amplitude": 1289450.6,
                    "rms_dbfs": -16.26,
                    "acoustic_character": "Low-frequency resonant chord fundamentals and warmth",
                    "dominant_harmonics_hz": [174.3, 260.7, 349.4, 1396.0]
                }
            },
            "musical_analysis": {
                "chord_identity": "F-sharp / F Major Chord with shimmering multi-octave resonance",
                "root_note": "F# / F",
                "constituent_intervals": [
                    {"note": "F3", "nominal_hz": 174.61, "measured_peak_hz": 174.3, "role": "Bass Fundamental"},
                    {"note": "C4", "nominal_hz": 261.63, "measured_peak_hz": 260.7, "role": "Perfect Fifth"},
                    {"note": "F4", "nominal_hz": 349.23, "measured_peak_hz": 349.4, "role": "Tonic Octave"},
                    {"note": "F6", "nominal_hz": 1396.91, "measured_peak_hz": 1396.0, "role": "Treble Harmonic"}
                ]
            }
        },
        "pre_boot_synthesis_architecture": {
            "execution_environment": "iBoot Stage 2 (Non-Essential Firmware Execution Phase)",
            "activation_gating": [
                {"source": "NVRAM", "variable": "boot-chime", "default": "enabled", "description": "User NVRAM toggle for startup audio."},
                {"source": "syscfg", "tag": "ChmE", "description": "Factory manufacturing chime enable flag."},
                {"source": "Settings", "key": "Turn On & Off Sounds", "description": "iOS Accessibility audio/visual feedback preference."}
            ],
            "playback_pipeline": [
                {
                    "stage": 1,
                    "name": "Image4 Verification & Unpack",
                    "description": "iBoot verifies the cryptographic signature of v57-boot-chime.im4p against the Secure Boot Manifest and personalizes the container with device-specific ECID/nonce."
                },
                {
                    "stage": 2,
                    "name": "Audio DMA Controller Setup",
                    "description": "iBoot configures the A19 Pro ADMAC audio DMA channels (admac-speaker-tx-ec-proxy) in cyclic ring-buffer mode with 6-byte stereo frame geometry."
                },
                {
                    "stage": 3,
                    "name": "Smart Amplifier Initialization",
                    "description": "Cirrus Logic CS35L42 / CS35L92 boosted smart speaker amplifier is powered up over I2C, Class-H boost converter is pre-charged to 11.5V, and soft-unmute ramp is initiated."
                },
                {
                    "stage": 4,
                    "name": "Direct Hardware Playback",
                    "description": "The 97,087 audio frames are streamed directly to the smart speaker amplifier via PDM/I2S interface at 48,000 Hz, running synchronously during the display logo phase."
                },
                {
                    "stage": 5,
                    "name": "Pop-Free Ramp & Hand-Off",
                    "description": "Upon stream completion (2.02 seconds), the output amplifier applies a gentle soft-mute ramp to prevent turn-off pops, and control is transferred to SPTM/TXM for XNU kernel initialization."
                }
            ]
        }
    }

    out_file = "artifacts/audio/codec/boot_chime_aubt_container_spec.json"
    with open(out_file, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"[+] Wrote boot_chime_aubt_container_spec.json ({len(json.dumps(spec))} bytes)")

if __name__ == "__main__":
    build_chime_spec()
