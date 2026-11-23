/*
 * apple_brooklands_pmic.h - Clean-Room Register Definitions & Telemetry Interface
 * Apple Silicon A19 Pro (t8150 / Apple H18) - Dialog/Apple Custom PMIC ("Brooklands")
 *
 * Grounded in DeviceTree: /device-tree/arm-io/nub-spmi0/pmu-main
 * Kernelcache: com.apple.driver.AppleSPMIPMU, com.apple.driver.AppleDialogPMU
 * Operating System: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 */

#ifndef APPLE_BROOKLANDS_PMIC_H
#define APPLE_BROOKLANDS_PMIC_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * ============================================================================
 * 1. PMIC SPMI SLAVE ADDRESSING
 * ============================================================================
 */
#define APPLE_SPMI_SLAVE_SHAMISEN       0x0C /* Sub-PMIC: RF/Cellular */
#define APPLE_SPMI_SLAVE_BROOKLANDS     0x0E /* Primary PMIC: Core System PMU */
#define APPLE_SPMI_SLAVE_STONEHENGE     0x0F /* Sub-PMIC: Camera/Display */

/*
 * ============================================================================
 * 2. IDENTIFICATION REGISTERS (Aperture: 0x0000, Size: 10 bytes)
 * ============================================================================
 */
#define BROOKLANDS_REG_DEV_ID_0         0x0000 /* Vendor ID Byte 0 (Dialog/Apple 0x44) */
#define BROOKLANDS_REG_DEV_ID_1         0x0001 /* Silicon Family ID (Brooklands 0x58) */
#define BROOKLANDS_REG_REV_ID_MAJOR     0x0002 /* Major Revision (0x01 = Rev A0) */
#define BROOKLANDS_REG_REV_ID_MINOR     0x0003 /* Minor Revision (0x00 = Subrev 0) */
#define BROOKLANDS_REG_DIE_ID_0         0x0004 /* Wafer Lot Identifier Byte 0 */
#define BROOKLANDS_REG_DIE_ID_1         0x0005 /* Wafer Lot Identifier Byte 1 */
#define BROOKLANDS_REG_WAFER_X          0x0006 /* Die X Coordinate on Wafer */
#define BROOKLANDS_REG_WAFER_Y          0x0007 /* Die Y Coordinate on Wafer */
#define BROOKLANDS_REG_FUSE_REV         0x0008 /* OTP Fuse Map Revision */
#define BROOKLANDS_REG_SEC_STATE        0x0009 /* Silicon Security State (Fused) */

/*
 * ============================================================================
 * 3. HARDWARE FAULT LOG REGISTERS (Aperture: 0x0010, Size: 9 bytes, 72 channels)
 * ============================================================================
 */
#define BROOKLANDS_REG_FAULT_BASE       0x0010
#define BROOKLANDS_FAULT_BANKS          9
#define BROOKLANDS_TOTAL_FAULT_CHANNELS 72

/* Fault Bank 0 (Registers 0x0010) */
#define BROOKLANDS_FAULT_0_UV_VDDMAIN_UVLO      (1U << 3)  /* Fault 3: Under-voltage lockout */
#define BROOKLANDS_FAULT_0_UV_VDD_BOOST_UVLO    (1U << 5)  /* Fault 5: Boost under-voltage */
#define BROOKLANDS_FAULT_0_OV_VDD_BOOST_OVLO    (1U << 6)  /* Fault 6: Boost over-voltage */

/* Fault Bank 1 (Registers 0x0011) */
#define BROOKLANDS_FAULT_1_POR                  (1U << 0)  /* Fault 8: Power-On Reset */
#define BROOKLANDS_FAULT_1_RST                  (1U << 1)  /* Fault 9: Reset pin triggered */
#define BROOKLANDS_FAULT_1_OT_OVERTEMP          (1U << 2)  /* Fault 10: Global Over-temp (>125C) */
#define BROOKLANDS_FAULT_1_OV_VDDMAIN_OVLO      (1U << 3)  /* Fault 11: VDD_MAIN over-voltage */

/* Fault Bank 2 (Registers 0x0012) */
#define BROOKLANDS_FAULT_2_BTN_TWO_FINGER_RST   (1U << 0)  /* Fault 16: Hardware force restart */
#define BROOKLANDS_FAULT_2_CRASH0_IN            (1U << 1)  /* Fault 17: AP Crash0 asserted */
#define BROOKLANDS_FAULT_2_BTN_SEQ_RESET        (1U << 2)  /* Fault 18: Button sequence reset */
#define BROOKLANDS_FAULT_2_SEC_BTN_SEQ          (1U << 3)  /* Fault 19: Secondary button seq */
#define BROOKLANDS_FAULT_2_WDOG_RESET_IN_1      (1U << 4)  /* Fault 20: Reset-In 1 watchdog */
#define BROOKLANDS_FAULT_2_DBG_RESET_IN_2       (1U << 5)  /* Fault 21: Reset-In 2 debug probe */
#define BROOKLANDS_FAULT_2_SOCHOT_RESET_IN_3    (1U << 6)  /* Fault 22: SoCHot thermal reset */
#define BROOKLANDS_FAULT_2_RST_IN_1_DEASSERT    (1U << 7)  /* Fault 23: Reset-In 1 de-assertion */

/* Fault Bank 3 (Registers 0x0013) */
#define BROOKLANDS_FAULT_3_SPMI_FAULT           (1U << 0)  /* Fault 24: SPMI bus protocol error */
#define BROOKLANDS_FAULT_3_NTC_SHDN             (1U << 1)  /* Fault 25: NTC thermal trip */
#define BROOKLANDS_FAULT_3_TIMEOUT_DBLCLICK     (1U << 2)  /* Fault 26: Double-click window exp */
#define BROOKLANDS_FAULT_3_TIMEOUT_WATCHDOG     (1U << 4)  /* Fault 28: PMIC internal watchdog */
#define BROOKLANDS_FAULT_3_BUTTON_DFU_RECOVER   (1U << 5)  /* Fault 29: Button DFU recover */
#define BROOKLANDS_FAULT_3_DFU_BTN_SEQ_RESET    (1U << 6)  /* Fault 30: DFU button sequence */

/* Fault Bank 4 (Registers 0x0014) */
#define BROOKLANDS_FAULT_4_OTP_CRC              (1U << 3)  /* Fault 35: OTP CRC checksum fail */
#define BROOKLANDS_FAULT_4_SGPIO                (1U << 4)  /* Fault 36: SGPIO fault interrupt */
#define BROOKLANDS_FAULT_4_BTN_SHDN             (1U << 5)  /* Fault 37: Power button shutdown */
#define BROOKLANDS_FAULT_4_XTAL_WDOG_EXPIRY     (1U << 6)  /* Fault 38: 32K crystal failure */
#define BROOKLANDS_FAULT_4_MFSM_SGPIO           (1U << 7)  /* Fault 39: MFSM SGPIO error */

/* Fault Bank 5 (Registers 0x0015) */
#define BROOKLANDS_FAULT_5_CRASH_HYP_FW_CRASH   (1U << 0)  /* Fault 40: Hypervisor FW crash */
#define BROOKLANDS_FAULT_5_CRASH_HYP_HW_CRASH   (1U << 1)  /* Fault 41: Hypervisor HW crash */
#define BROOKLANDS_FAULT_5_TARGET_ST_WDOG       (1U << 2)  /* Fault 42: Target state watchdog */
#define BROOKLANDS_FAULT_5_WDOG_FW_TIMEOUT      (1U << 3)  /* Fault 43: Firmware watchdog */
#define BROOKLANDS_FAULT_5_EMERG_SHDN           (1U << 4)  /* Fault 44: Emergency shutdown */
#define BROOKLANDS_FAULT_5_TARGET_OFF_RESTART   (1U << 2)  /* Fault 50 (remapped): Restart */
#define BROOKLANDS_FAULT_5_TARGET_OFF_SHUTDOWN  (1U << 3)  /* Fault 51 (remapped): Graceful off */
#define BROOKLANDS_FAULT_5_TARGET_OFF_CONFLICT  (1U << 4)  /* Fault 52 (remapped): Conflict */

/* Fault Bank 6 (Registers 0x0016) */
#define BROOKLANDS_FAULT_6_OT_TDIE_IDX0         (1U << 0)  /* Fault 56: Die Zone 0 (>105C) */
#define BROOKLANDS_FAULT_6_OT_TDIE_IDX1         (1U << 1)  /* Fault 57: Die Zone 1 (>110C) */
#define BROOKLANDS_FAULT_6_OT_TDIE_IDX2         (1U << 2)  /* Fault 58: Die Zone 2 (>115C) */
#define BROOKLANDS_FAULT_6_OT_TDIE_IDX3         (1U << 3)  /* Fault 59: Die Zone 3 (>120C) */
#define BROOKLANDS_FAULT_6_OT_TDIE_IDX4         (1U << 4)  /* Fault 60: Die Zone 4 (>125C) */
#define BROOKLANDS_FAULT_6_OT_TDIE_AGGREGATE    (1U << 5)  /* Fault 61: Aggregate die trip */

/* Fault Bank 7 (Registers 0x0017) */
#define BROOKLANDS_FAULT_7_UV_CP_UVLO           (1U << 0)  /* Fault 64: Charge Pump UVLO */
#define BROOKLANDS_FAULT_7_OV_CP_OVLO           (1U << 1)  /* Fault 65: Charge Pump OVLO */
#define BROOKLANDS_FAULT_7_CP_WDOG_EXPIRY       (1U << 2)  /* Fault 66: Charge Pump watchdog */

/* Fault Bank 8 (Registers 0x0018) */
#define BROOKLANDS_FAULT_8_UV_LDO9_UV           (1U << 4)  /* Fault 68: LDO9 under-voltage */
#define BROOKLANDS_FAULT_8_OV_LDO9_OV           (1U << 5)  /* Fault 69: LDO9 over-voltage */
#define BROOKLANDS_FAULT_8_UV_LDO9B_UV          (1U << 6)  /* Fault 70: LDO9b under-voltage */
#define BROOKLANDS_FAULT_8_OV_LDO9B_OV          (1U << 7)  /* Fault 71: LDO9b over-voltage */

/*
 * ============================================================================
 * 4. REAL-TIME CLOCK & ALARM REGISTERS (Aperture: 0x2000, Size: 16 bytes)
 * ============================================================================
 */
#define BROOKLANDS_REG_RTC_ALARM_CTRL   0x2000
#define BROOKLANDS_RTC_CTRL_EN_MASK     0x40   /* Bit 6: Enable Alarm */

#define BROOKLANDS_REG_RTC_COUNTER_0    0x2002 /* 48-bit 32.768kHz counter byte 0 */
#define BROOKLANDS_REG_RTC_COUNTER_1    0x2003
#define BROOKLANDS_REG_RTC_COUNTER_2    0x2004
#define BROOKLANDS_REG_RTC_COUNTER_3    0x2005
#define BROOKLANDS_REG_RTC_COUNTER_4    0x2006
#define BROOKLANDS_REG_RTC_COUNTER_5    0x2007

#define BROOKLANDS_REG_RTC_ALARM_0      0x2008 /* 48-bit alarm target byte 0 */
#define BROOKLANDS_REG_RTC_ALARM_1      0x2009
#define BROOKLANDS_REG_RTC_ALARM_2      0x200A
#define BROOKLANDS_REG_RTC_ALARM_3      0x200B
#define BROOKLANDS_REG_RTC_ALARM_4      0x200C
#define BROOKLANDS_REG_RTC_ALARM_5      0x200D

#define BROOKLANDS_REG_RTC_IRQ_MASK     0x200E
#define BROOKLANDS_RTC_ALARM_MASK       0x01   /* Bit 0: Alarm IRQ mask */
#define BROOKLANDS_RTC_EVENT_MASK       0x02   /* Bit 1: Alarm Event mask */

#define BROOKLANDS_REG_RTC_SCRPAD_0     0x2100 /* 6 bytes clock / calibration scratchpad */

/*
 * ============================================================================
 * 5. OFF-TO-WAKE SOURCE REGISTERS (Aperture: 0x2813, Size: 2 bytes)
 * ============================================================================
 */
#define BROOKLANDS_REG_OFF2WAKE_L       0x2813
#define BROOKLANDS_REG_OFF2WAKE_H       0x2814

#define BROOKLANDS_O2WS_FW_NONSEC_OFF_CSR   (1U << 0)  /* Source 0 */
#define BROOKLANDS_O2WS_GCB_OFF_WAKEUP      (1U << 1)  /* Source 1 */
#define BROOKLANDS_O2WS_GCB_WAKEUP          (1U << 2)  /* Source 2 */
#define BROOKLANDS_O2WS_RTC_ALARM_WAKEUP    (1U << 3)  /* Source 3 */
#define BROOKLANDS_O2WS_AUTO_WAKEUP         (1U << 4)  /* Source 4: VBUS / Charger */
#define BROOKLANDS_O2WS_GCB_CRASH_WAKEUP    (1U << 5)  /* Source 5 */
#define BROOKLANDS_O2WS_HW_WDOG_WAKEUP      (1U << 6)  /* Source 6 */
#define BROOKLANDS_O2WS_FW_WDOG_WAKEUP      (1U << 7)  /* Source 7 */
#define BROOKLANDS_O2WS_DFT_CTRL2_WAKEUP    (1U << 8)  /* Source 8 */
#define BROOKLANDS_O2WS_TARGET_STATE_WDOG   (1U << 10) /* Source 10 */
#define BROOKLANDS_O2WS_FW_NONSEC_WDOG      (1U << 13) /* Source 13 */
#define BROOKLANDS_O2WS_FW_REQ_AUTO_WAKEUP  (1U << 14) /* Source 14 */

/*
 * ============================================================================
 * 6. FIRMWARE MAILBOX INTERFACES
 * ============================================================================
 */
#define BROOKLANDS_REG_FW_HOST_IRQ      0x2B08 /* Host Interrupt Trigger Register */
#define BROOKLANDS_REG_FW_MCOM          0x2B60 /* Micro-Communications Mailbox */
#define BROOKLANDS_MCOM_INT_INDEX       1

/*
 * ============================================================================
 * 7. PTMU REGION GEOMETRY (Standard: 0x6000..0x7000, Secure: 0x7000..0x8000)
 * ============================================================================
 */
#define BROOKLANDS_PTMU_REGION_0_START  0x6000
#define BROOKLANDS_PTMU_REGION_0_SIZE   0x0040
#define BROOKLANDS_PTMU_REGION_1_START  0x6040
#define BROOKLANDS_PTMU_REGION_1_SIZE   0x0040
#define BROOKLANDS_PTMU_REGION_2_START  0x6080
#define BROOKLANDS_PTMU_REGION_2_SIZE   0x0040
#define BROOKLANDS_PTMU_REGION_3_START  0x60C0
#define BROOKLANDS_PTMU_REGION_3_SIZE   0x0040
#define BROOKLANDS_PTMU_REGION_4_START  0x6100
#define BROOKLANDS_PTMU_REGION_4_SIZE   0x0040
#define BROOKLANDS_PTMU_REGION_5_START  0x6140
#define BROOKLANDS_PTMU_REGION_5_SIZE   0x0040
#define BROOKLANDS_PTMU_REGION_6_START  0x6180
#define BROOKLANDS_PTMU_REGION_6_SIZE   0x0040
#define BROOKLANDS_PTMU_REGION_7_START  0x61C0
#define BROOKLANDS_PTMU_REGION_7_SIZE   0x0040
#define BROOKLANDS_PTMU_REGION_8_START  0x6200
#define BROOKLANDS_PTMU_REGION_8_SIZE   0x0080
#define BROOKLANDS_PTMU_REGION_9_START  0x6280
#define BROOKLANDS_PTMU_REGION_9_SIZE   0x0080
#define BROOKLANDS_PTMU_REGION_10_START 0x6300
#define BROOKLANDS_PTMU_REGION_10_SIZE  0x0080
#define BROOKLANDS_PTMU_REGION_11_START 0x6380
#define BROOKLANDS_PTMU_REGION_11_SIZE  0x0080
#define BROOKLANDS_PTMU_REGION_12_START 0x6400
#define BROOKLANDS_PTMU_REGION_12_SIZE  0x0200
#define BROOKLANDS_PTMU_REGION_13_START 0x6600
#define BROOKLANDS_PTMU_REGION_13_SIZE  0x0200
#define BROOKLANDS_PTMU_REGION_14_START 0x6800
#define BROOKLANDS_PTMU_REGION_14_SIZE  0x0400
#define BROOKLANDS_PTMU_REGION_15_START 0x6C00
#define BROOKLANDS_PTMU_REGION_15_SIZE  0x0400

/* Secure PTMU Regions (Accessible only from Secure Enclave / PTMU-Secure) */
#define BROOKLANDS_PTMU_SECURE_0_START  0x7000
#define BROOKLANDS_PTMU_SECURE_0_SIZE   0x0400
#define BROOKLANDS_PTMU_SECURE_1_START  0x7400
#define BROOKLANDS_PTMU_SECURE_1_SIZE   0x0400
#define BROOKLANDS_PTMU_SECURE_2_START  0x7800
#define BROOKLANDS_PTMU_SECURE_2_SIZE   0x0400
#define BROOKLANDS_PTMU_SECURE_3_START  0x7C00
#define BROOKLANDS_PTMU_SECURE_3_SIZE   0x0200
#define BROOKLANDS_PTMU_SECURE_4_START  0x7E00
#define BROOKLANDS_PTMU_SECURE_4_SIZE   0x0200

/*
 * ============================================================================
 * 8. SCRATCHPAD MEMORY APERTURES
 * ============================================================================
 */
#define BROOKLANDS_SCRPAD_BASE          0x8000
#define BROOKLANDS_SCRPAD_SIZE          0x2800 /* 10 KB general scratchpad */

#define BROOKLANDS_SCRPAD_SOCD_BASE     0x8B00
#define BROOKLANDS_SCRPAD_SOCD_SIZE     0x1800 /* 6 KB SOCD panic/crash log */

#define BROOKLANDS_SCRPAD_LPM_LOG_BASE  0xA780
#define BROOKLANDS_SCRPAD_LPM_LOG_SIZE  0x005C /* LPM Log buffer */

#define BROOKLANDS_SCRPAD_LPM_CTRL_BASE 0xA7DC
#define BROOKLANDS_SCRPAD_LPM_CTRL_SIZE 0x0004 /* LPM Control word */

#define BROOKLANDS_LEGACY_SCRPAD_BASE   0xF800
#define BROOKLANDS_LEGACY_SCRPAD_SIZE   0x0800 /* Legacy iBoot mailbox */

/*
 * ============================================================================
 * 9. HARDWARE DATA STRUCTURES
 * ============================================================================
 */

/* Snapshot of all 9 fault register banks */
typedef struct __attribute__((packed)) {
    uint8_t bank[BROOKLANDS_FAULT_BANKS];
} brooklands_fault_snapshot_t;

/* PMIC Telemetry Sample Frame */
typedef struct __attribute__((packed)) {
    uint64_t timestamp_ticks;
    uint16_t vdd_main_mv;
    uint16_t vdd_boost_mv;
    int16_t  die_temp_deci_celsius[5];
    uint16_t off2wake_status;
    uint8_t  active_fault_count;
    uint8_t  reserved;
} brooklands_telemetry_frame_t;

#ifdef __cplusplus
}
#endif

#endif /* APPLE_BROOKLANDS_PMIC_H */
