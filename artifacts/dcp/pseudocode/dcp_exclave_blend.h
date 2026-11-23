/*
 * Apple Display Co-Processor (DCP) — DART-DCP Stream ID & Exclave Secure Compositor
 * Target Platform: iOS 27.2 / Darwin 24.2.0 (Build 24B119)
 * Hardware Target: Apple Silicon A19 Pro (t8150) — iPhone 18,3 (v57ap)
 * Subsystems: DART-DCP, mapper-dcp-exclave, RTKExclaveTBEndpoint, SecureBlendHandler
 */

#ifndef DCP_EXCLAVE_BLEND_H
#define DCP_EXCLAVE_BLEND_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * 1. DART IOMMU Physical MMIO Mapping
 * ========================================================================= */

#define DART_DCP_EXCLAVE_BASE         0x00000001fa340000ULL /* mapper-dcp-exclave MMIO base */
#define DART_DISP0_HOST_BASE          0x00000001fa300000ULL /* mapper-disp0 MMIO base */
#define DART_PAGE_SIZE                16384U                /* 16 KB hardware translation pages */

/* Hardware DART Stream Identifiers */
#define DCP_STREAM_ID_HOST_UI         0x01U                 /* Untrusted Host AP / WindowServer */
#define DCP_STREAM_ID_EXCLAVE_SECURE  0x02U                 /* ExclaveOS Secure Surface / SIL */
#define DCP_STREAM_ID_CURSOR          0x03U                 /* Hardware Cursor Plane */

/* =========================================================================
 * 2. Secure Indicator Light (SIL) & Nits Capping
 * ========================================================================= */

#define SIL_MAX_NITS_CAP              2000U                 /* Maximum permissible indicator nits */
#define SIL_DEFAULT_NITS              1200U                 /* Nominal daylight indicator nits */

typedef enum {
    SIL_INDICATOR_NONE                = 0,
    SIL_INDICATOR_CAMERA              = 1, /* Green privacy dot (0, 255, 0) */
    SIL_INDICATOR_MICROPHONE          = 2, /* Orange privacy dot (255, 140, 0) */
    SIL_INDICATOR_APPLE_PAY           = 3, /* Biometric confirmation card */
    SIL_INDICATOR_PASSCODE            = 4  /* Secure PIN entry field */
} sil_indicator_type_t;

typedef struct {
    uint32_t x;
    uint32_t y;
    uint32_t width;
    uint32_t height;
} sil_rect_t;

typedef struct {
    sil_indicator_type_t type;
    sil_rect_t           bounding_box;
    uint32_t             requested_nits;
    uint32_t             hardware_cap_nits;
    uint8_t              color_r;
    uint8_t              color_g;
    uint8_t              color_b;
    uint8_t              alpha;
    bool                 hardware_clamped;
} sil_configuration_t;

/* =========================================================================
 * 3. RTKit Tightbeam Exclave Endpoint (RTKExclaveTBEndpoint)
 * ========================================================================= */

typedef struct {
    uint64_t client_id;
    uint32_t message_id;
    uint32_t payload_size;
    uint8_t  payload[256];
} tightbeam_msg_t;

typedef struct {
    uint64_t exclave_dart_base;
    uint32_t stream_id;
    bool     endpoint_ready;
    uint32_t messages_received;
} rtk_exclave_endpoint_t;

/* =========================================================================
 * 4. Secure Blend Handler (SecureBlendHandler.cpp)
 * ========================================================================= */

typedef struct {
    uint32_t stream_id;
    uint64_t surface_physical_addr;
    uint32_t width;
    uint32_t height;
    uint32_t pixel_format;
    bool     has_alpha;
    uint8_t  z_order;
} blend_layer_descriptor_t;

typedef struct {
    blend_layer_descriptor_t layers[3]; /* Layer 0: Host (0x01), Layer 1: Cursor (0x03), Layer 2: Exclave (0x02) */
    sil_configuration_t      sil_config;
    bool                     host_read_isolated;
    bool                     zero_writeback_enforced;
} secure_blend_handler_t;

static inline bool secure_blend_validate_nits(sil_configuration_t *sil) {
    if (!sil) return false;
    if (sil->requested_nits > sil->hardware_cap_nits) {
        /* Firmware log: "IOMFB: Secure indicator nits (0x%x) above Indicator nits cap (0x%x)\n" */
        sil->requested_nits = sil->hardware_cap_nits;
        sil->hardware_clamped = true;
        return false;
    }
    sil->hardware_clamped = false;
    return true;
}

static inline void secure_blend_init_hierarchy(secure_blend_handler_t *handler) {
    if (!handler) return;

    /* Layer 0: Host OS (WindowServer) */
    handler->layers[0].stream_id = DCP_STREAM_ID_HOST_UI;
    handler->layers[0].z_order = 0;
    handler->layers[0].has_alpha = false;

    /* Layer 1: Cursor Plane */
    handler->layers[1].stream_id = DCP_STREAM_ID_CURSOR;
    handler->layers[1].z_order = 1;
    handler->layers[1].has_alpha = true;

    /* Layer 2: Exclave Secure Overlay */
    handler->layers[2].stream_id = DCP_STREAM_ID_EXCLAVE_SECURE;
    handler->layers[2].z_order = 2;
    handler->layers[2].has_alpha = true;

    handler->sil_config.hardware_cap_nits = SIL_MAX_NITS_CAP;
    handler->sil_config.requested_nits = SIL_DEFAULT_NITS;
    handler->host_read_isolated = true;
    handler->zero_writeback_enforced = true;
}

static inline void secure_blend_execute_scanout_pixel(
    const secure_blend_handler_t *handler,
    uint32_t x, uint32_t y,
    uint32_t host_rgb,
    uint32_t cursor_rgba,
    uint32_t exclave_rgba,
    uint32_t *out_final_rgb)
{
    if (!out_final_rgb || !handler) return;

    uint32_t current_pixel = host_rgb;

    /* Blend Layer 1 (Cursor) if alpha > 0 */
    uint8_t cursor_alpha = (cursor_rgba >> 24) & 0xFF;
    if (cursor_alpha > 0) {
        float ca = (float)cursor_alpha / 255.0f;
        uint8_t cr = (cursor_rgba >> 16) & 0xFF;
        uint8_t cg = (cursor_rgba >> 8) & 0xFF;
        uint8_t cb = cursor_rgba & 0xFF;

        uint8_t hr = (current_pixel >> 16) & 0xFF;
        uint8_t hg = (current_pixel >> 8) & 0xFF;
        uint8_t hb = current_pixel & 0xFF;

        uint8_t fr = (uint8_t)(cr * ca + hr * (1.0f - ca));
        uint8_t fg = (uint8_t)(cg * ca + hg * (1.0f - ca));
        uint8_t fb = (uint8_t)(cb * ca + hb * (1.0f - ca));
        current_pixel = ((uint32_t)fr << 16) | ((uint32_t)fg << 8) | fb;
    }

    /* Blend Layer 2 (Exclave Secure Plane) with absolute priority */
    uint8_t exclave_alpha = (exclave_rgba >> 24) & 0xFF;
    if (exclave_alpha > 0) {
        float ea = (float)exclave_alpha / 255.0f;
        uint8_t er = (exclave_rgba >> 16) & 0xFF;
        uint8_t eg = (exclave_rgba >> 8) & 0xFF;
        uint8_t eb = exclave_rgba & 0xFF;

        uint8_t br = (current_pixel >> 16) & 0xFF;
        uint8_t bg = (current_pixel >> 8) & 0xFF;
        uint8_t bb = current_pixel & 0xFF;

        uint8_t fr = (uint8_t)(er * ea + br * (1.0f - ea));
        uint8_t fg = (uint8_t)(eg * ea + bg * (1.0f - ea));
        uint8_t fb = (uint8_t)(eb * ea + bb * (1.0f - ea));
        current_pixel = ((uint32_t)fr << 16) | ((uint32_t)fg << 8) | fb;
    }

    /* Composited directly onto scanout FIFO without DRAM writeback */
    *out_final_rgb = current_pixel;
}

#ifdef __cplusplus
}
#endif

#endif /* DCP_EXCLAVE_BLEND_H */
