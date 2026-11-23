/**
 * @file wireless_power_ftab.h
 * @brief Clean-room C definitions for MagSafe & Qi2 Wireless Power FTAB.
 *
 * Extracted from Apple Silicon A19 Pro (t8150) / iPhone 18,3 (v57ap).
 * Binary Provenance: Firmware/WirelessPower/WirelessPower.d23_v5z.im4p
 */

#ifndef WIRELESS_POWER_FTAB_H
#define WIRELESS_POWER_FTAB_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define WIPW_FTAB_MAGIC         0x736f6b7262617466ULL /* 'rkosftab' */
#define WIPW_FTAB_OFFSET        0x3b
#define WIPW_PARTITION_COUNT    3

#define WIPW_TAG_DORX           0x58524f44  /* 'DORX' */
#define WIPW_TAG_BOOT           0x544f4f42  /* 'BOOT' */
#define WIPW_TAG_DOTX           0x58544f44  /* 'DOTX' */

/* Wireless Power State Machine */
typedef enum {
    WIPW_STATE_OFF              = 0x00,
    WIPW_STATE_PING             = 0x01,  /* Digital ping for receiver detection */
    WIPW_STATE_IDENTIFICATION   = 0x02,  /* Qi2 / MagSafe handshake */
    WIPW_STATE_CONFIGURATION    = 0x03,  /* Power contract negotiation (15W/25W) */
    WIPW_STATE_POWER_TRANSFER   = 0x04,  /* Continuous active power transfer */
    WIPW_STATE_FAULT            = 0x05,  /* Over-temp, FOD, or misalignment */
    WIPW_STATE_REVERSE_TX       = 0x06   /* Reverse charging accessory */
} wipw_power_state_t;

/* FTAB Header */
typedef struct __attribute__((packed)) {
    uint8_t  magic[8];                  /* 'rkosftab' */
    uint32_t num_entries;               /* 3 */
    uint32_t flags;
} wipw_ftab_header_t;

/* FTAB Partition Entry */
typedef struct __attribute__((packed)) {
    uint32_t tag;                       /* 'DORX', 'BOOT', 'DOTX' */
    uint32_t offset;
    uint32_t size;
    uint32_t flags;
} wipw_ftab_entry_t;

/* MagSafe Power Contract Descriptor */
typedef struct __attribute__((packed)) {
    uint16_t target_voltage_mv;         /* 9000 mV, 12000 mV, 15000 mV */
    uint16_t max_current_ma;            /* up to 2200 mA */
    uint8_t  foreign_object_det_passed;
    uint8_t  alignment_efficiency_pct;  /* 0 - 100% magnetic alignment */
    uint16_t coil_temperature_c_q8;    /* Temperature in Q8.8 fixed-point */
} wipw_power_contract_t;

static inline bool wipw_is_valid_tag(uint32_t tag) {
    return (tag == WIPW_TAG_DORX) || (tag == WIPW_TAG_BOOT) || (tag == WIPW_TAG_DOTX);
}

#ifdef __cplusplus
}
#endif

#endif /* WIRELESS_POWER_FTAB_H */
