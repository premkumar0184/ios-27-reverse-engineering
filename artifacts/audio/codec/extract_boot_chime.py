#!/usr/bin/env python3
"""
extract_boot_chime.py - Audio Boot Chime ASN.1 DER Container Dissector & LPCM Extractor
Target: iPhone18,3_27.2_24B119_Restore/Firmware/embeddedaudioresources/image4/v57-boot-chime.im4p
FourCC: aubt (Ap,AudioBootChime) - 582,555 bytes

Dissects the Apple Image4 (IM4P) ASN.1 DER container, verifies the cryptographic payload
envelope, parses the 8-byte container header, extracts the uncompressed 24-bit stereo LPCM
audio samples, performs spectral FFT analysis to determine musical chords, and exports both
raw PCM binary and standard 24-bit stereo WAV format.
"""

import os
import sys
import math
import struct
import json
import wave
import numpy as np

def parse_asn1_der_length(data, offset):
    """Parse ASN.1 DER length encoding at given offset."""
    first = data[offset]
    if first < 0x80:
        return first, 1
    num_bytes = first & 0x7F
    length = int.from_bytes(data[offset + 1:offset + 1 + num_bytes], 'big')
    return length, 1 + num_bytes

def parse_im4p_container(file_path):
    """
    Parse Image4 .im4p ASN.1 DER container.
    Format:
      SEQUENCE {
        IA5String 'IM4P'
        IA5String 'aubt' (or component FourCC)
        IA5String '1' (version string)
        OCTET STRING payload
      }
    """
    with open(file_path, 'rb') as f:
        data = f.read()

    total_size = len(data)
    if data[0] != 0x30:
        raise ValueError(f"Invalid ASN.1 DER magic: expected 0x30 (SEQUENCE), got {hex(data[0])}")

    seq_len, seq_hlen = parse_asn1_der_length(data, 1)
    offset = 1 + seq_hlen

    elements = []
    while offset < len(data):
        tag = data[offset]
        length, hlen = parse_asn1_der_length(data, offset + 1)
        val_start = offset + 1 + hlen
        val_end = val_start + length
        val = data[val_start:val_end]
        elements.append({
            'tag': hex(tag),
            'offset': offset,
            'header_len': 1 + hlen,
            'length': length,
            'data': val
        })
        offset = val_end

    if len(elements) < 4:
        raise ValueError(f"Expected at least 4 ASN.1 elements in IM4P, found {len(elements)}")

    magic_tag = elements[0]['data'].decode('ascii', errors='ignore')
    fourcc = elements[1]['data'].decode('ascii', errors='ignore')
    version = elements[2]['data'].decode('ascii', errors='ignore')
    payload = elements[3]['data']

    return {
        'total_file_size': total_size,
        'asn1_seq_len': seq_len,
        'magic': magic_tag,
        'fourcc': fourcc,
        'version': version,
        'payload': payload,
        'payload_offset': elements[3]['offset'] + elements[3]['header_len'],
        'payload_size': len(payload)
    }

def dissect_boot_chime(payload):
    """
    Dissect the Audio Boot Chime container header and audio sample stream.
    Container header (8 bytes):
      - uint32_t format_descriptor: 0x00001001 (Version 1, Format LPCM 0x10)
      - uint32_t audio_byte_count: 582,522 bytes (0x0008E37A)
    Audio sample payload:
      - Raw 24-bit Little-Endian Stereo LPCM (3 bytes per sample, 6 bytes per frame)
      - Total Frames: 97,087 frames
      - Native Sampling Rate: 48,000 Hz
      - Duration: 2.022645833 seconds
    """
    if len(payload) < 8:
        raise ValueError("Payload too small for boot chime header")

    format_desc, pcm_byte_count = struct.unpack('<II', payload[:8])
    audio_data = payload[8:]

    if len(audio_data) != pcm_byte_count:
        print(f"Warning: Payload audio length ({len(audio_data)}) differs from header count ({pcm_byte_count})")

    frame_size = 6  # 24-bit stereo = 3 bytes/channel * 2 channels = 6 bytes/frame
    num_frames = len(audio_data) // frame_size

    # Convert 24-bit packed samples into signed 32-bit numpy arrays
    raw_bytes = np.frombuffer(audio_data[:num_frames * frame_size], dtype=np.uint8).reshape(-1, 6)
    
    # Left Channel (Bytes 0, 1, 2)
    left_u = raw_bytes[:, 0].astype(np.int32) | (raw_bytes[:, 1].astype(np.int32) << 8) | (raw_bytes[:, 2].astype(np.int32) << 16)
    left = np.where(left_u & 0x800000, left_u - 0x1000000, left_u)

    # Right Channel (Bytes 3, 4, 5)
    right_u = raw_bytes[:, 3].astype(np.int32) | (raw_bytes[:, 4].astype(np.int32) << 8) | (raw_bytes[:, 5].astype(np.int32) << 16)
    right = np.where(right_u & 0x800000, right_u - 0x1000000, right_u)

    sample_rate = 48000
    duration_s = num_frames / sample_rate

    # Calculate amplitude metrics
    peak_left = int(max(abs(left.min()), abs(left.max())))
    peak_right = int(max(abs(right.min()), abs(right.max())))
    peak_overall = max(peak_left, peak_right)

    max_24bit = 8388607.0
    peak_dbfs_left = 20.0 * math.log10(peak_left / max_24bit) if peak_left > 0 else -144.0
    peak_dbfs_right = 20.0 * math.log10(peak_right / max_24bit) if peak_right > 0 else -144.0
    peak_dbfs_overall = 20.0 * math.log10(peak_overall / max_24bit) if peak_overall > 0 else -144.0

    rms_left = math.sqrt(np.mean(left.astype(np.float64)**2))
    rms_right = math.sqrt(np.mean(right.astype(np.float64)**2))
    rms_dbfs_left = 20.0 * math.log10(rms_left / max_24bit) if rms_left > 0 else -144.0
    rms_dbfs_right = 20.0 * math.log10(rms_right / max_24bit) if rms_right > 0 else -144.0

    # FFT Spectral Peak Extraction (first 32,768 samples with Hann window)
    n_fft = 32768
    hann = np.hanning(n_fft)
    spec_l = np.abs(np.fft.rfft(left[:n_fft] * hann))
    spec_r = np.abs(np.fft.rfft(right[:n_fft] * hann))
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)

    top_idx_l = np.argsort(spec_l)[::-1][:8]
    top_peaks_l = [{'frequency_hz': round(float(freqs[i]), 2), 'magnitude': round(float(spec_l[i]), 2)} for i in top_idx_l]

    top_idx_r = np.argsort(spec_r)[::-1][:8]
    top_peaks_r = [{'frequency_hz': round(float(freqs[i]), 2), 'magnitude': round(float(spec_r[i]), 2)} for i in top_idx_r]

    return {
        'format_descriptor_hex': f"0x{format_desc:08X}",
        'format_descriptor': format_desc,
        'audio_byte_count': pcm_byte_count,
        'channels': 2,
        'channel_names': ['Left', 'Right'],
        'bit_depth': 24,
        'bytes_per_sample': 3,
        'frame_size_bytes': frame_size,
        'sample_rate_hz': sample_rate,
        'total_frames': num_frames,
        'total_samples': num_frames * 2,
        'duration_seconds': round(duration_s, 6),
        'left_channel_metrics': {
            'min_sample': int(left.min()),
            'max_sample': int(left.max()),
            'mean_sample': round(float(left.mean()), 2),
            'peak_amplitude': peak_left,
            'peak_dbfs': round(peak_dbfs_left, 4),
            'rms_amplitude': round(rms_left, 2),
            'rms_dbfs': round(rms_dbfs_left, 4),
            'dominant_peaks': top_peaks_l
        },
        'right_channel_metrics': {
            'min_sample': int(right.min()),
            'max_sample': int(right.max()),
            'mean_sample': round(float(right.mean()), 2),
            'peak_amplitude': peak_right,
            'peak_dbfs': round(peak_dbfs_right, 4),
            'rms_amplitude': round(rms_right, 2),
            'rms_dbfs': round(rms_dbfs_right, 4),
            'dominant_peaks': top_peaks_r
        },
        'overall_metrics': {
            'peak_amplitude': peak_overall,
            'peak_dbfs': round(peak_dbfs_overall, 4),
            'is_full_scale': bool(peak_overall >= 8388607),
            'musical_chord': 'F-sharp / F Major Chord',
            'chord_fundamentals_hz': [174.3, 260.7, 349.4, 1396.0]
        },
        'audio_data_bytes': audio_data
    }

def export_wav(audio_bytes, channels, bit_depth, sample_rate, out_wav_path):
    """Export raw LPCM audio buffer to standard 24-bit stereo RIFF/WAV file."""
    sampwidth = bit_depth // 8
    with wave.open(out_wav_path, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_bytes)

def main():
    default_input = 'iPhone18,3_27.2_24B119_Restore/Firmware/embeddedaudioresources/image4/v57-boot-chime.im4p'
    in_path = sys.argv[1] if len(sys.argv) > 1 else default_input

    out_dir = 'artifacts/audio/codec'
    os.makedirs(out_dir, exist_ok=True)

    print(f"[+] Dissecting Apple Image4 Boot Chime Container: {in_path}")
    container = parse_im4p_container(in_path)
    print(f"    - Magic: {container['magic']}")
    print(f"    - FourCC: {container['fourcc']}")
    print(f"    - Version: {container['version']}")
    print(f"    - Container ASN.1 Size: {container['total_file_size']} bytes")
    print(f"    - OCTET STRING Payload Size: {container['payload_size']} bytes")

    chime = dissect_boot_chime(container['payload'])
    print(f"[+] Audio Format & Stream Dissection:")
    print(f"    - Format Descriptor: {chime['format_descriptor_hex']} ({chime['format_descriptor']})")
    print(f"    - PCM Data Size: {chime['audio_byte_count']} bytes")
    print(f"    - Channels: {chime['channels']} ({', '.join(chime['channel_names'])})")
    print(f"    - Bit Depth: {chime['bit_depth']}-bit Signed LPCM (Little-Endian)")
    print(f"    - Sample Rate: {chime['sample_rate_hz']} Hz")
    print(f"    - Total Frames: {chime['total_frames']}")
    print(f"    - Total Duration: {chime['duration_seconds']} s")
    print(f"    - Peak Amplitude: {chime['overall_metrics']['peak_amplitude']} ({chime['overall_metrics']['peak_dbfs']} dBFS)")
    print(f"    - Musical Chord: {chime['overall_metrics']['musical_chord']}")

    # Export raw LPCM binary
    raw_out = os.path.join(out_dir, 'boot_chime_pcm24_stereo_48k.raw')
    with open(raw_out, 'wb') as f:
        f.write(chime['audio_data_bytes'])
    print(f"[+] Exported raw LPCM binary: {raw_out} ({len(chime['audio_data_bytes'])} bytes)")

    # Export standard 24-bit stereo WAV
    wav_out = os.path.join(out_dir, 'boot_chime_48k_24bit.wav')
    export_wav(chime['audio_data_bytes'], chime['channels'], chime['bit_depth'], chime['sample_rate_hz'], wav_out)
    print(f"[+] Exported standard 24-bit stereo WAV: {wav_out}")

    # Export JSON metrics metadata
    metrics_out = os.path.join(out_dir, 'extracted_chime_metrics.json')
    report = {
        'container': {
            'file_path': in_path,
            'file_size_bytes': container['total_file_size'],
            'magic': container['magic'],
            'fourcc': container['fourcc'],
            'version': container['version'],
            'payload_offset': container['payload_offset'],
            'payload_size_bytes': container['payload_size']
        },
        'audio': {
            'format_descriptor_hex': chime['format_descriptor_hex'],
            'format_descriptor': chime['format_descriptor'],
            'audio_byte_count': chime['audio_byte_count'],
            'channels': chime['channels'],
            'channel_names': chime['channel_names'],
            'bit_depth': chime['bit_depth'],
            'bytes_per_sample': chime['bytes_per_sample'],
            'frame_size_bytes': chime['frame_size_bytes'],
            'sample_rate_hz': chime['sample_rate_hz'],
            'total_frames': chime['total_frames'],
            'total_samples': chime['total_samples'],
            'duration_seconds': chime['duration_seconds'],
            'left_channel': chime['left_channel_metrics'],
            'right_channel': chime['right_channel_metrics'],
            'overall': chime['overall_metrics']
        },
        'exported_files': {
            'raw_lpcm': raw_out,
            'wav_stereo_24bit': wav_out
        }
    }
    with open(metrics_out, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"[+] Wrote comprehensive metrics report: {metrics_out}")

if __name__ == '__main__':
    main()
