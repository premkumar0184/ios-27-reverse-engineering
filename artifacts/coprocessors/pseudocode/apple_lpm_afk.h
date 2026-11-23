/**
 * @file apple_lpm_afk.h
 * @brief Clean-room C definitions for Apple Low Power Monitor (ALPM) & AFK IPC.
 *
 * Extracted from Apple Silicon A19 Pro (t8150) / iPhone 18,3 (v57ap).
 * Binary Provenance: Firmware/AppleLPM/AppleLPM.v57.release.im4p
 * RTKit Build: RTKit_armv8_chinook_Oz_flto_pac-3514.40.18.release
 */

#ifndef APPLE_LPM_AFK_H
#define APPLE_LPM_AFK_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ALPM_TAIL_MAGIC         0x67737766  /* 'fwsg' in little-endian */
#define ALPM_SCRPAD_LPM_CTRL    0x0000a7dc  /* DeviceTree info-scrpad_lpm_ctrl */
#define ALPM_SCRPAD_LPM_LOG     0x0000a780  /* DeviceTree info-scrpad_lpm_log */
#define ALPM_PKG_POWER_TARGET   0x00000002  /* DeviceTree pkg-lpm-power-target */
#define ALPM_FRAME_DURATION_TICKS 0x00044f10/* DeviceTree frame-duration-lpm-nclks (282,384 ticks @ 24MHz) */

/* Packet types for Apple Firmware Kit (afklib) */
typedef enum {
    kAFKPacketType_OpenInterface        = 0x01,
    kAFKPacketType_CloseInterface       = 0x02,
    kAFKPacketType_SendCommand          = 0x03,
    kAFKPacketType_CommandReply         = 0x04,
    kAFKPacketType_RingBufferAssume     = 0x05,
    kAFKPacketType_RingBufferRelease    = 0x06,
    kAFKPacketType_PowerStateChange     = 0x07
} afk_packet_type_t;

/* ALPM Low Power State FSM */
typedef enum {
    ALPM_STATE_ACTIVE_RUN               = 0x00,
    ALPM_STATE_AOD_STANDBY              = 0x01,  /* 1 Hz display refresh */
    ALPM_STATE_MAGSAFE_CHARGING         = 0x02,  /* Battery animation active */
    ALPM_STATE_POCKET_DARK              = 0x03,  /* Proximity sensor covered */
    ALPM_STATE_DEEP_SLEEP_PROXY         = 0x04,  /* Full AP powergated */
    ALPM_STATE_SHUTDOWN                 = 0x05
} alpm_power_state_t;

/* Tail Segment Descriptor Table ('fwsg') */
typedef struct __attribute__((packed)) {
    uint32_t magic;                     /* 'fwsg' (0x67737766) */
    uint32_t version;                   /* 0x00000001 */
    uint32_t table_offset;              /* 0x00136020 */
    uint32_t segment_count;             /* 2 */
} alpm_fwsg_header_t;

typedef struct __attribute__((packed)) {
    uint8_t  reserved[8];
    uint64_t vm_address;
    uint32_t vm_size;
    uint8_t  flag;
    char     segname[8];
} alpm_segment_descriptor_t;

/* AFK IPC Command Header */
typedef struct __attribute__((packed)) {
    uint32_t packet_type;
    uint32_t sequence_id;
    uint32_t payload_length;
    uint32_t channel_id;
} afk_msg_header_t;

/* Always-On Display Low-Power Frame Request */
typedef struct __attribute__((packed)) {
    uint32_t frame_index;
    uint16_t width;
    uint16_t height;
    uint8_t  bpp;
    uint8_t  flags;
    uint64_t framebuffer_dma_addr;
} alpm_disp_frame_req_t;

static inline bool alpm_verify_tail_magic(uint32_t val) {
    return val == ALPM_TAIL_MAGIC;
}

#ifdef __cplusplus
}
#endif

#endif /* APPLE_LPM_AFK_H */
