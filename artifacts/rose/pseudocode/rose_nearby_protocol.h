/*
 * Apple U2 / U3 Ultra-Wideband (UWB) — Nearby Interaction Protocol Stack
 * Target Platform: iOS 27.2 / Darwin 24.2.0 (Build 24B119)
 * Hardware Target: Apple Rose 2 (r2p1 / hammerfest) — iPhone 18,3 (v57ap)
 * Subsystems: FiRa MAC Layer, nearbyd IPC, NINearbyObject Vector Engine
 */

#ifndef ROSE_NEARBY_PROTOCOL_H
#define ROSE_NEARBY_PROTOCOL_H

#include <stdint.h>
#include <stdbool.h>
#include <math.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * 1. Protocol Opcodes & Frame Types
 * ========================================================================= */

#define ROSE_MAC_FRAME_CONTROL_DATA    0x8841U /* Data frame, PAN ID compression */

typedef enum {
    ROSE_PKT_TYPE_PPOLL                = 0x01, /* Pre-Poll Frame */
    ROSE_PKT_TYPE_POLL                 = 0x02, /* Ranging Poll */
    ROSE_PKT_TYPE_RESP                 = 0x03, /* Ranging Response */
    ROSE_PKT_TYPE_FDATA                = 0x04, /* Final Data Frame */
    ROSE_PKT_TYPE_RRRM                 = 0x05  /* Round-Robin Ranging Mode */
} rose_packet_type_t;

/* =========================================================================
 * 2. Packet Wire Descriptors
 * ========================================================================= */

typedef struct __attribute__((packed)) {
    uint16_t frame_control;
    uint8_t  seq_num;
    uint16_t pan_id;
    uint64_t dest_addr;
    uint64_t src_addr;
    uint32_t session_id;
    uint16_t block_index;
    uint8_t  round_index;
} rose_ppoll_frame_t;

typedef struct __attribute__((packed)) {
    uint16_t frame_control;
    uint8_t  seq_num;
    uint32_t session_id;
    uint64_t tx_timestamp_t1_ps;
} rose_poll_frame_t;

typedef struct __attribute__((packed)) {
    uint16_t frame_control;
    uint8_t  seq_num;
    uint32_t session_id;
    uint64_t rx_timestamp_t2_ps;
    uint64_t tx_timestamp_t3_ps;
} rose_resp_frame_t;

typedef struct __attribute__((packed)) {
    uint16_t frame_control;
    uint8_t  seq_num;
    uint32_t session_id;
    uint64_t t1_t4_delta_ps;
    uint64_t t2_t3_delta_ps;
    int16_t  azimuth_centideg;
    int16_t  elevation_centideg;
    uint8_t  tof_fom;
} rose_fdata_frame_t;

/* =========================================================================
 * 3. Session Lifecycle State Machine
 * ========================================================================= */

typedef enum {
    ROSE_NI_STATE_IDLE                 = 0,
    ROSE_NI_STATE_DISCOVERY            = 1,
    ROSE_NI_STATE_RANGING_ACTIVE       = 2,
    ROSE_NI_STATE_SUSPENDED            = 3,
    ROSE_NI_STATE_TERMINATED           = 4
} rose_ni_session_state_t;

typedef struct {
    uint32_t                session_id;
    rose_ni_session_state_t state;
    bool                    is_initiator;
    uint8_t                 channel;
    uint32_t                ranging_interval_ms;
    uint64_t                peer_address;
    uint32_t                completed_rounds;
    uint32_t                failed_rounds;
} rose_ni_session_context_t;

/* =========================================================================
 * 4. Host NINearbyObject 3D Vector Synthesis
 * ========================================================================= */

typedef struct {
    float x;
    float y;
    float z;
} rose_simd_float3_t;

typedef struct {
    float              distance_meters;
    rose_simd_float3_t direction_vector;
    float              azimuth_rad;
    float              elevation_rad;
    uint8_t            confidence_fom;
} rose_nearby_object_report_t;

static inline void rose_synthesize_nearby_object(
    float distance_m,
    float azimuth_deg,
    float elevation_deg,
    uint8_t fom,
    rose_nearby_object_report_t *out)
{
    if (!out) return;
    out->distance_meters = distance_m;
    out->confidence_fom  = fom;

    float theta_rad = azimuth_deg   * (3.14159265f / 180.0f);
    float phi_rad   = elevation_deg * (3.14159265f / 180.0f);

    out->azimuth_rad   = theta_rad;
    out->elevation_rad = phi_rad;

    /* Spherical to Cartesian 3D unit direction vector */
    out->direction_vector.x = cosf(phi_rad) * sinf(theta_rad);
    out->direction_vector.y = sinf(phi_rad);
    out->direction_vector.z = cosf(phi_rad) * cosf(theta_rad);
}

#ifdef __cplusplus
}
#endif

#endif /* ROSE_NEARBY_PROTOCOL_H */
