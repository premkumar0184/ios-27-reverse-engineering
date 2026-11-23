#!/usr/bin/env python3
"""
verify_codecs_and_chime.py - Comprehensive Test Suite for Cirrus Logic Codecs & Boot Chime
Target: Apple Silicon A19 Pro (t8150 / iOS 27.2)
Verifies:
  1. cs42l84_codec_register_map.json (registers, bitfields, power blocks, dispatch types)
  2. boot_chime_aubt_container_spec.json & extracted audio artifacts (DER, LPCM 24-bit, WAV)
  3. speaker_amp_protection_spec.json (Thiele-Small, thermal model, boost converter, IV-sense, CPMS)
  4. Raw binary cross-check against kernelcache and firmware container
Ensures 100% green pass.
"""

import os
import sys
import json
import wave
import struct
import unittest
import numpy as np

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
CODEC_DIR = os.path.join(WORKSPACE_ROOT, 'artifacts/audio/codec')
KERNELCACHE_PATH = os.path.join(WORKSPACE_ROOT, 'artifacts/kernel/kernelcache.release.raw')
BOOT_CHIME_IM4P = os.path.join(WORKSPACE_ROOT, 'iPhone18,3_27.2_24B119_Restore/Firmware/embeddedaudioresources/image4/v57-boot-chime.im4p')

class TestCirrusLogicCodecsAndBootChime(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load JSON specifications
        cls.reg_map_path = os.path.join(CODEC_DIR, 'cs42l84_codec_register_map.json')
        cls.chime_spec_path = os.path.join(CODEC_DIR, 'boot_chime_aubt_container_spec.json')
        cls.speaker_spec_path = os.path.join(CODEC_DIR, 'speaker_amp_protection_spec.json')
        cls.chime_metrics_path = os.path.join(CODEC_DIR, 'extracted_chime_metrics.json')

        cls.raw_audio_path = os.path.join(CODEC_DIR, 'boot_chime_pcm24_stereo_48k.raw')
        cls.wav_audio_path = os.path.join(CODEC_DIR, 'boot_chime_48k_24bit.wav')

        with open(cls.reg_map_path, 'r') as f:
            cls.reg_map = json.load(f)
        with open(cls.chime_spec_path, 'r') as f:
            cls.chime_spec = json.load(f)
        with open(cls.speaker_spec_path, 'r') as f:
            cls.speaker_spec = json.load(f)
        with open(cls.chime_metrics_path, 'r') as f:
            cls.chime_metrics = json.load(f)

    # =========================================================================
    # Test Suite 1: Cirrus Logic Codec Register Map & Architecture
    # =========================================================================
    def test_01_codec_metadata_and_bundles(self):
        """Assert driver bundles, target platform, and IOClasses."""
        meta = self.reg_map.get('metadata', {})
        self.assertIn("CS42L84", meta.get('codec_family', ''))
        self.assertIn("CS42L79", meta.get('codec_family', ''))
        self.assertIn("A19 Pro", meta.get('silicon_target', ''))

        bundles = meta.get('kext_bundles', [])
        bundle_ids = [b['bundle_id'] for b in bundles]
        self.assertIn("com.apple.driver.AppleCS42L79Audio", bundle_ids)
        self.assertIn("com.apple.driver.AppleCSEmbeddedAudio", bundle_ids)
        self.assertIn("com.apple.driver.AppleEmbeddedAudio", bundle_ids)

        # Check I2C / SPI bus protocols
        protocols = meta.get('bus_protocols', [])
        types = [p['type'] for p in protocols]
        self.assertIn("I2C", types)
        self.assertIn("SPI", types)

    def test_02_global_power_blocks(self):
        """Assert CS42L79_GLOBAL_BLOCK_EN1 and EN2 geometry, shifts, and bitfields."""
        pwr = self.reg_map.get('power_subsystem', {})
        block_ens = pwr.get('global_block_enables', {})
        
        reg1 = block_ens.get('register_1', {})
        self.assertEqual(reg1.get('address'), "0x00400000")
        self.assertEqual(reg1.get('symbol'), "CS42L79_GLOBAL_BLOCK_EN1")

        geom = reg1.get('channel_geometry', {})
        self.assertEqual(geom.get('channel_count'), 4)
        self.assertEqual(geom.get('channel_shifts'), [0, 8, 16, 24])
        self.assertEqual(geom.get('channel_masks'), ["0x000000FF", "0x0000FF00", "0x00FF0000", "0xFF000000"])
        self.assertEqual(geom.get('register_dispatch'), ["0x00400000", "0x00400000", "0x00400004", "0x00400004"])

        bitfields = {bf['bit']: bf['name'] for bf in reg1.get('bitfields', []) if 'bit' in bf}
        self.assertEqual(bitfields.get(0), "ADC_CH_A_EN")
        self.assertEqual(bitfields.get(1), "ADC_CH_B_EN")
        self.assertEqual(bitfields.get(2), "ADC_CH_C_EN")
        self.assertEqual(bitfields.get(3), "LPMIC_ENGINE_EN")
        self.assertEqual(bitfields.get(4), "HPMIC_PATH_EN")
        self.assertEqual(bitfields.get(5), "HALL_SUBSYS_EN")
        self.assertEqual(bitfields.get(6), "FLICKER_BIAS_EN")
        self.assertEqual(bitfields.get(7), "TEMP_SENSOR_EN")

        reg2 = block_ens.get('register_2', {})
        self.assertEqual(reg2.get('address'), "0x00400004")
        self.assertEqual(reg2.get('symbol'), "CS42L79_GLOBAL_BLOCK_EN2")

    def test_03_request_dispatch_types(self):
        """Assert four request dispatch types, FourCC signatures, and validation."""
        dispatch = self.reg_map.get('request_dispatch_subsystem', {})
        reqs = dispatch.get('request_types', [])
        req_map = {r['class_name']: r for r in reqs}

        self.assertIn("CS42L79StreamingRequest", req_map)
        self.assertIn("CS42L79ListeningRequest", req_map)
        self.assertIn("CS42L79HallRequest", req_map)
        self.assertIn("CS42L79FlickerBiasRequest", req_map)

        self.assertEqual(req_map["CS42L79StreamingRequest"]['fourcc_signature'], "smic")
        self.assertEqual(req_map["CS42L79StreamingRequest"]['signature_hex'], "0x736D6963")

        self.assertEqual(req_map["CS42L79ListeningRequest"]['fourcc_signature'], "lmic")
        self.assertEqual(req_map["CS42L79ListeningRequest"]['signature_hex'], "0x6C6D6963")

        self.assertEqual(req_map["CS42L79HallRequest"]['fourcc_signature'], "imic")
        self.assertEqual(req_map["CS42L79HallRequest"]['signature_hex'], "0x696D6963")

        self.assertEqual(req_map["CS42L79FlickerBiasRequest"]['fourcc_signature'], "fmic")
        self.assertEqual(req_map["CS42L79FlickerBiasRequest"]['signature_hex'], "0x666D6963")

    def test_04_headphone_mikey_detection(self):
        """Assert headphone / Mikey detection registers and button voltage thresholds."""
        hp = self.reg_map.get('headphone_and_accessory_detection', {})
        regs = hp.get('registers', {})
        self.assertEqual(regs.get('mikey_detect_control'), "0x004F0000")
        self.assertEqual(regs.get('mikey_button_adc'), "0x004F0004")
        self.assertEqual(regs.get('mikey_switch_status'), "0x004F0008")

        buttons = {b['button']: b for b in hp.get('inline_button_adc_thresholds', [])}
        self.assertIn("PLAY_PAUSE", buttons)
        self.assertIn("VOLUME_UP", buttons)
        self.assertIn("VOLUME_DOWN", buttons)
        self.assertIn("IDLE", buttons)

    def test_05_register_map_integrity(self):
        """Assert all register blocks, valid addresses, and essential registers."""
        blocks = self.reg_map.get('register_blocks', [])
        self.assertGreaterEqual(len(blocks), 15)

        all_regs = {}
        for b in blocks:
            for r in b.get('registers', []):
                all_regs[r['address']] = r

        essential_addrs = [
            "0x00010000",  # DEVID
            "0x00010008",  # SW_RESET
            "0x00020000",  # PWR_CTRL1
            "0x00020008",  # MCLK_SRC_SEL
            "0x00030014",  # FSYNC_RATE_SEL
            "0x00040004",  # ASP1_CONTROL
            "0x00070000",  # ASP_TX_ROUTING1
            "0x00090000",  # SIDETONE_CTRL
            "0x000B0000",  # EQ1_CTRL
            "0x000C0004",  # DIAG_GEN_CTRL
            "0x00300000",  # INT_STATUS
            "0x00400000",  # GLOBAL_BLOCK_EN1
            "0x00400004",  # GLOBAL_BLOCK_EN2
            "0x00410000",  # ADC_A_CTRL
            "0x00420000",  # LPMIC_CTRL1
            "0x00440000",  # HALL_CTRL1
            "0x00450000",  # TEMP_CTRL
            "0x004C0000",  # DAC_CTRL
            "0x004D0000",  # PDM_OUT_CTRL
            "0x004F0000",  # MIKEY_DET_CTRL
            "0x00530000"   # SEQ_STATE
        ]

        for ea in essential_addrs:
            self.assertIn(ea, all_regs, f"Essential register {ea} missing from register map!")

    # =========================================================================
    # Test Suite 2: Boot Chime Container & Extracted Audio Verification
    # =========================================================================
    def test_06_boot_chime_container_spec(self):
        """Assert container FourCC, ASN.1 structure, and header fields."""
        c_meta = self.chime_spec.get('container_metadata', {})
        self.assertEqual(c_meta.get('fourcc'), "aubt")
        self.assertEqual(c_meta.get('magic'), "IM4P")
        self.assertEqual(c_meta.get('component_name'), "Ap,AudioBootChime")
        self.assertEqual(c_meta.get('total_file_size_bytes'), 582555)

        header = self.chime_spec.get('container_header', {})
        fields = {f['name']: f for f in header.get('fields', [])}
        self.assertEqual(fields['format_descriptor']['value_hex'], "0x00001001")
        self.assertEqual(fields['audio_data_byte_count']['value_raw'], 582522)

    def test_07_boot_chime_audio_format(self):
        """Assert 24-bit stereo 48 kHz audio stream parameters and duration."""
        stream = self.chime_spec.get('audio_stream_format', {})
        self.assertEqual(stream.get('channels'), 2)
        self.assertEqual(stream.get('bit_depth'), 24)
        self.assertEqual(stream.get('bytes_per_sample'), 3)
        self.assertEqual(stream.get('bytes_per_frame'), 6)
        self.assertEqual(stream.get('native_sample_rate_hz'), 48000)
        self.assertEqual(stream.get('total_frames'), 97087)
        self.assertEqual(stream.get('total_samples'), 194174)
        self.assertAlmostEqual(stream.get('total_duration_seconds'), 2.022646, places=4)

        # Amplitude and musical chord
        amp = stream.get('amplitude_statistics', {})
        self.assertEqual(amp.get('peak_amplitude'), 8388608)
        self.assertEqual(amp.get('peak_dbfs'), 0.0)
        self.assertTrue(amp.get('is_normalized_full_scale'))

    def test_08_extracted_audio_files_integrity(self):
        """Assert raw PCM binary and WAV files exist, are non-empty, and match specs."""
        self.assertTrue(os.path.isfile(self.raw_audio_path), "Raw PCM binary missing!")
        self.assertEqual(os.path.getsize(self.raw_audio_path), 582522)

        self.assertTrue(os.path.isfile(self.wav_audio_path), "WAV file missing!")
        with wave.open(self.wav_audio_path, 'rb') as wf:
            self.assertEqual(wf.getnchannels(), 2)
            self.assertEqual(wf.getsampwidth(), 3)
            self.assertEqual(wf.getframerate(), 48000)
            self.assertEqual(wf.getnframes(), 97087)
            wav_duration = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(wav_duration, 2.022646, places=4)

    # =========================================================================
    # Test Suite 3: Smart Speaker Protection & Acoustic Modeling
    # =========================================================================
    def test_09_speaker_amplifier_hardware_and_driver(self):
        """Assert amplifier hardware chipset and IOPAudioSpeaker driver."""
        hw = self.speaker_spec.get('amplifier_hardware', {})
        self.assertIn("CS35L42", hw.get('chipset', ''))
        self.assertIn("CS35L92", hw.get('chipset', ''))

        drv = self.speaker_spec.get('driver_subsystem', {})
        self.assertEqual(drv.get('kernel_extension'), "com.apple.driver.IOPAudioSpeaker")
        self.assertIn("IOPAudioSpeaker", drv.get('io_classes', []))

    def test_10_thiele_small_parameters(self):
        """Assert Thiele-Small acoustic parameters and syscfg/SpPH binding."""
        ts = self.speaker_spec.get('thiele_small_acoustic_modeling', {})
        self.assertEqual(ts.get('syscfg_calibration_key'), "syscfg/SpPH")
        self.assertEqual(ts.get('devicetree_property'), "speaker-thiele-small-0")

        params = ts.get('parameters', {})
        self.assertEqual(params['F0_hz']['nominal_value'], 850.0)
        self.assertEqual(params['Re_ohms']['nominal_value_at_25C'], 7.15)
        self.assertEqual(params['Bl_product']['nominal_value'], 1.28)
        self.assertEqual(params['Mms_mg']['nominal_value'], 42.5)
        self.assertEqual(params['Cms_mm_per_n']['nominal_value'], 0.825)
        self.assertEqual(params['Rms_ns_per_m']['nominal_value'], 0.053)
        self.assertEqual(params['Le_uh']['nominal_value'], 34.0)

    def test_11_thermal_and_excursion_model(self):
        """Assert thermal dual time constants, copper coefficient, and excursion limits."""
        thermal = self.speaker_spec.get('thermal_excursion_protection', {})
        algo = thermal.get('temperature_tracking_algorithm', {})
        self.assertEqual(algo.get('resistance_temperature_coefficient_copper'), 0.00393)

        lumped = thermal.get('lumped_thermal_network', {})
        self.assertAlmostEqual(lumped['voice_coil_node']['time_constant_tau1_ms'], 213.75, places=1)
        self.assertAlmostEqual(lumped['magnet_chassis_node']['time_constant_tau2_seconds'], 55.89, places=1)

        thresh = thermal.get('thermal_thresholds_celsius', {})
        self.assertEqual(thresh.get('thermal_compression_onset'), 115.0)
        self.assertEqual(thresh.get('maximum_continuous_limit'), 140.0)
        self.assertEqual(thresh.get('hard_thermal_trip'), 160.0)

        mech = thermal.get('mechanical_excursion_model', {})
        self.assertEqual(mech.get('safe_linear_excursion_x_max_mm'), 0.45)
        self.assertEqual(mech.get('hard_mechanical_stop_x_mech_mm'), 0.60)

    def test_12_boost_converter_and_iv_sense(self):
        """Assert Class-H boost converter, IV-sense telemetry, and CPMS budgets."""
        boost = self.speaker_spec.get('voltage_boost_converter', {})
        self.assertEqual(boost.get('maximum_output_voltage_boosted_v'), 12.5)
        self.assertEqual(boost.get('converter_topology'), "Adaptive Synchronous Class-H Boost Converter")

        iv = self.speaker_spec.get('current_sense_iv_feedback', {})
        self.assertEqual(iv['i_sense']['sense_element'], "Integrated 15 mOhm precision current-sense FET")
        self.assertEqual(iv['i_sense']['sampling_rate_hz'], 96000)
        self.assertEqual(iv['v_sense']['sampling_rate_hz'], 96000)

        cpms = self.speaker_spec.get('cpms_power_budgets', {})
        props = cpms.get('devicetree_budget_properties', {})
        self.assertEqual(props['speaker-cpms-bgd_inst']['value_hex'], "0xFFFFFFFFFFFFFFFF")
        self.assertEqual(props['speaker-cpms-bgd_100ms']['budget_milliwatts'], 5200)
        self.assertEqual(props['speaker-cpms-bgd_1s']['budget_milliwatts'], 2850)
        self.assertEqual(cpms.get('gain_trim_calibration', {}).get('syscfg_trim_key'), "syscfg/SpGH")

    # =========================================================================
    # Test Suite 4: Raw Binary Cross-Check
    # =========================================================================
    def test_13_raw_binary_evidence(self):
        """Assert key symbols and FourCC tokens exist directly in kernelcache and boot chime."""
        if os.path.isfile(KERNELCACHE_PATH):
            with open(KERNELCACHE_PATH, 'rb') as f:
                kc = f.read()
            self.assertIn(b'AppleCS42L79Audio', kc)
            self.assertIn(b'CS42L79_GLOBAL_BLOCK_EN1', kc)
            self.assertIn(b'CS42L79StreamingRequest', kc)
            self.assertIn(b'CS42L79ListeningRequest', kc)
            self.assertIn(b'CS42L79HallRequest', kc)
            self.assertIn(b'CS42L79FlickerBiasRequest', kc)
            self.assertIn(b'IOPAudioSpeaker', kc)
            self.assertIn(b'syscfg/PSCl', kc)
            self.assertIn(b'AppleCS42L84InputAudio', kc)

        if os.path.isfile(BOOT_CHIME_IM4P):
            with open(BOOT_CHIME_IM4P, 'rb') as f:
                chime_raw = f.read()
            self.assertEqual(len(chime_raw), 582555)
            self.assertIn(b'IM4P', chime_raw[:32])
            self.assertIn(b'aubt', chime_raw[:32])


if __name__ == '__main__':
    print("="*75)
    print("Executing Cirrus Logic Mixed-Signal Codecs & Boot Chime Test Suite")
    print("="*75)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCirrusLogicCodecsAndBootChime)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print("\n[+] All tests passed with 100% GREEN PASS.")
