/*
 * centauri_host_interface.h
 * Clean-Room Apple Silicon Centauri DriverKit & ACIPC Transport Interface
 * iOS 27.2 (24B119) / Apple Silicon A19 Pro (t8150 / v57ap)
 */

#ifndef CENTAURI_HOST_INTERFACE_H
#define CENTAURI_HOST_INTERFACE_H

#include <stdint.h>
#include <stdbool.h>

/* PCIe Platform Constants */
#define CENTAURI_PCI_BRIDGE_PATH        "/device-tree/arm-io/apcie/pci-bridge0"
#define CENTAURI_DART_BASE_PADDR        0x0000000180000000ULL
#define CENTAURI_DART_APERTURE_SIZE     0x0000000000020000ULL  /* 128 KB */
#define CENTAURI_AIC_INTERRUPT_VECTOR   22                     /* Level Sensitive */
#define CENTAURI_DART_AIC_INTERRUPT     1142
#define CENTAURI_MSI_VECTOR_COUNT       32

/* DART Stream IDs */
#define DART_SID_CENTAURI_CONTROL       0x10    /* Function 0 */
#define DART_SID_CENTAURI_ALPHA         0x11    /* Function 1 (Wi-Fi 7) */
#define DART_SID_CENTAURI_BETA          0x12    /* Function 2 (Bluetooth 5.4) */
#define DART_SID_CENTAURI_PIODMA        0x11

/* Bank 0 MMIO Register Offsets (Function 0: CentauriControl) */
#define REG_WINDOW_BASE_LO              0x4014
#define REG_WINDOW_BASE_HI              0x4018
#define REG_WINDOW_SIZE                 0x401C
#define REG_EXEC_STAGE                  0x8000
#define REG_DOMAIN_MODE                 0x8004
#define REG_CHIP_INFO                   0x8008
#define REG_ECID_LO                     0x800C
#define REG_ECID_HI                     0x8010
#define REG_BOOT_NONCE_HASH             0x8014  /* 32 Bytes */
#define REG_BOOT_NONCE                  0x8034  /* 8 Bytes */
#define REG_BOOT_MODE                   0x803C
#define REG_IMAGE_RESPONSE              0x8040
#define REG_IMAGE_ADDRESS_LO            0x8044
#define REG_IMAGE_ADDRESS_HI            0x8048
#define REG_IMAGE_SIZE                  0x804C
#define REG_IPC_STATUS                  0x8050
#define REG_CONTEXT_INFO_ADDR_LO        0x8054
#define REG_CONTEXT_INFO_ADDR_HI        0x8058
#define REG_SECONDARY_FTAB_HEADER       0x8074
#define REG_HOST_PLATFORM_SUB_VAR_ID    0x8078
#define REG_HOST_PLATFORM_ID            0x807C
#define REG_RINGDB_BASE                 0x9000  /* 13 Multi Vectors */
#define REG_BOOT_NONCE_DOORBELL         0x9004
#define REG_SYSTEM_EVENTS_DOORBELL      0x906C  /* Vector 27 */
#define REG_BOOT_IMAGE_DOORBELL         0x9070
#define REG_SLEEP_CONTROL               0x9078
#define REG_IPC_CONTROL                 0x907C

/* Execution Stages */
enum centauri_exec_stage {
    EXEC_STAGE_ROM      = 0,
    EXEC_STAGE_BOOT     = 1,
    EXEC_STAGE_OS       = 2,
    EXEC_STAGE_ABORT    = 3,
    EXEC_STAGE_PREBOOT  = 4,
    EXEC_STAGE_LPM_BOOT = 6,
    EXEC_STAGE_LPM_OS   = 7
};

/* ACIPC Protocol Version */
#define ACIPC_PROTOCOL_VERSION_3_0      0x00000300

/* ACIPC Context Base Header (120 Bytes) */
struct __attribute__((packed)) acipc_context_header {
    uint32_t protocol_version;
    uint32_t flags;
    uint16_t tr_index_count;
    uint16_t cr_index_count;
    uint32_t host_heartbeat;
    uint32_t device_heartbeat;
    uint64_t mtr_base_paddr;
    uint64_t mcr_base_paddr;
    uint16_t mtr_ring_size;
    uint16_t mcr_ring_size;
    uint16_t mtr_footer_size;
    uint16_t mcr_footer_size;
    uint8_t  reserved_padding[76];
};

/* ACIPC 32-Byte Transfer Descriptor */
struct __attribute__((packed, aligned(16))) acipc_tr_descriptor {
    uint64_t data_paddr;
    uint32_t data_length;
    uint16_t flags;
    uint16_t transfer_tag;
    uint32_t channel_id;
    uint32_t client_cookie;
    uint64_t timestamp_ptm;
    /* 16-Byte Transfer Footer */
    uint32_t checksum_offload;
    uint32_t priority_qos;
    uint64_t reserved_footer;
};

/* ACIPC 16-Byte Completion Descriptor */
struct __attribute__((packed, aligned(16))) acipc_cr_descriptor {
    uint16_t transfer_tag;
    uint16_t status_code;
    uint32_t bytes_transferred;
    uint32_t client_cookie;
    uint16_t channel_id;
    uint16_t rx_rssi_snr;
    /* 16-Byte Completion Footer */
    uint64_t rx_timestamp;
    uint32_t hardware_errors;
    uint32_t reserved_footer;
};

#endif /* CENTAURI_HOST_INTERFACE_H */
