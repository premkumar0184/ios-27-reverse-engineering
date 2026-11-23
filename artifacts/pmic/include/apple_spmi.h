/*
 * apple_spmi.h - Clean-Room MIPI SPMI v2.0 Controller & Wire Protocol Interface
 * Apple Silicon A19 Pro (t8150 / Apple H18) - AppleSPMI Hardware Driver
 *
 * Grounded in DeviceTree: /device-tree/arm-io/nub-spmi* / aop-spmi*
 * Kernelcache: com.apple.driver.AppleSPMI (Generation 4)
 * Operating System: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 */

#ifndef APPLE_SPMI_H
#define APPLE_SPMI_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * ============================================================================
 * 1. MIPI SPMI v2.0 COMMAND OPCODES
 * ============================================================================
 */
#define SPMI_CMD_REG_0_WR       0x00 /* Register 0 Write (Zero-payload write) */
#define SPMI_CMD_REG_WR         0x10 /* Standard Register Write (8-bit address) */
#define SPMI_CMD_REG_RD         0x20 /* Standard Register Read (8-bit address) */
#define SPMI_CMD_EXT_REG_WR     0x30 /* Extended Register Write (16-bit address, 1..16 B) */
#define SPMI_CMD_EXT_REG_RD     0x38 /* Extended Register Read (16-bit address, 1..16 B) */
#define SPMI_CMD_EXT_REG_WRL    0x3A /* Extended Register Write Long (16-bit address, 1..32 B) */
#define SPMI_CMD_EXT_REG_RDL    0x3E /* Extended Register Read Long (16-bit address, 1..32 B) */

/*
 * ============================================================================
 * 2. SPMI HARDWARE CONTROLLER BASE PHYSICAL ADDRESSES (Apertures 0, 1, 2)
 * ============================================================================
 */
/* Controller 0: nub-spmi0 (Primary System PMIC / Brooklands + BTM) */
#define APPLE_SPMI0_CMD_BASE            0x00F8714000ULL /* Aperture 0: 16 KB */
#define APPLE_SPMI0_BUS_BASE            0x00F8704000ULL /* Aperture 1: 16 KB */
#define APPLE_SPMI0_IES_BASE            0x00F8700000ULL /* Aperture 2: 16 KB */

/* Controller 1: nub-spmi1 (Companion Sub-PMICs: Shamisen 0x0C, Stonehenge 0x0F) */
#define APPLE_SPMI1_CMD_BASE            0x00F8614000ULL
#define APPLE_SPMI1_BUS_BASE            0x00F8604000ULL
#define APPLE_SPMI1_IES_BASE            0x00F8600000ULL

/* Controller 2: aop-spmi0 (Always-On Processor: NFC Stockholm 0x02, Hammerfest 0x03) */
#define APPLE_AOP_SPMI0_CMD_BASE        0x0100914000ULL
#define APPLE_AOP_SPMI0_BUS_BASE        0x0100904000ULL
#define APPLE_AOP_SPMI0_IES_BASE        0x0100900000ULL

/* Controller 3: aop-spmi1 (Always-On Processor: UWB / WLAN-IDC / Baseband-IDC) */
#define APPLE_AOP_SPMI1_CMD_BASE        0x0100B14000ULL
#define APPLE_AOP_SPMI1_BUS_BASE        0x0100B04000ULL
#define APPLE_AOP_SPMI1_IES_BASE        0x0100B00000ULL

/* Controller 4: nub-spmi-a0 (Type-C Power Delivery CBTL1702) */
#define APPLE_SPMI_A0_CMD_BASE          0x00F8908000ULL
#define APPLE_SPMI_A0_BUS_BASE          0x00F8904000ULL
#define APPLE_SPMI_A0_IES_BASE          0x00F8900000ULL

#define APPLE_SPMI_APERTURE_SIZE        0x4000 /* 16 KB per aperture */

/*
 * ============================================================================
 * 3. CONTROLLER REGISTER OFFSETS (Aperture 0: Command & Queue Engine)
 * ============================================================================
 */
#define SPMI_REG_CTRL                   0x0000 /* Master Control: Enable, Reset, Clock Div */
#define SPMI_REG_STATUS                 0x0004 /* Raw Status Flags & Busy bit */
#define SPMI_REG_CMD_RING_BASE_L        0x0008 /* Command Ring Buffer Physical Addr Low */
#define SPMI_REG_CMD_RING_BASE_H        0x000C /* Command Ring Buffer Physical Addr High */
#define SPMI_REG_CMD_PROD_IDX           0x0010 /* Command Ring Producer Index (0..255) */
#define SPMI_REG_CMD_CONS_IDX           0x0014 /* Command Ring Consumer Index (0..255) */
#define SPMI_REG_RSP_RING_BASE_L        0x0018 /* Response Ring Buffer Physical Addr Low */
#define SPMI_REG_RSP_RING_BASE_H        0x001C /* Response Ring Buffer Physical Addr High */
#define SPMI_REG_RSP_PROD_IDX           0x0020 /* Response Ring Producer Index (0..255) */
#define SPMI_REG_RSP_CONS_IDX           0x0024 /* Response Ring Consumer Index (0..255) */
#define SPMI_REG_FIFO_STATUS            0x0030 /* Hardware FIFO Fill Level & Empty flags */
#define SPMI_REG_QUEUE_RESET            0x0034 /* Queue Invalidate & Flush Register */

/* Control register bitfields */
#define SPMI_CTRL_ENABLE                (1U << 0)
#define SPMI_CTRL_RESET                 (1U << 1)
#define SPMI_CTRL_BURST_EN              (1U << 2)
#define SPMI_CTRL_CLK_19_2MHZ           (0U << 4)
#define SPMI_CTRL_CLK_24_0MHZ           (1U << 4)
#define SPMI_CTRL_CLK_26_0MHZ           (2U << 4)

/*
 * ============================================================================
 * 4. CONTROLLER REGISTER OFFSETS (Aperture 2: Interrupt Event Service / IES)
 * ============================================================================
 */
#define SPMI_REG_IES_STATUS             0x0000 /* Interrupt Event Service Status */
#define SPMI_REG_IES_MASK               0x0004 /* Interrupt Event Service Mask */
#define SPMI_REG_IES_CLEAR              0x0008 /* Interrupt Event Service Clear */
#define SPMI_REG_FAULT_IES_STATUS       0x0010 /* Fault IES Status */
#define SPMI_REG_FAULT_IES_MASK         0x0014 /* Fault IES Mask */

/* IES Status bitfields */
#define SPMI_IES_CMD_COMPLETE           (1U << 0)
#define SPMI_IES_RSP_AVAILABLE          (1U << 1)
#define SPMI_IES_QUEUE_EMPTY            (1U << 2)
#define SPMI_IES_BUS_COLLISION          (1U << 8)
#define SPMI_IES_CMD_PARITY_ERR         (1U << 9)
#define SPMI_IES_ADDR_PARITY_ERR        (1U << 10)
#define SPMI_IES_DATA_PARITY_ERR        (1U << 11)
#define SPMI_IES_SLAVE_NACK             (1U << 12)
#define SPMI_IES_TIMEOUT                (1U << 13)

/*
 * ============================================================================
 * 5. COMMAND & RESPONSE RING BUFFER DESCRIPTORS (256 Slots, 16 Bytes Each)
 * ============================================================================
 */
#define SPMI_RING_QUEUE_DEPTH           256
#define SPMI_DESCRIPTOR_SIZE            16
#define SPMI_RING_BUFFER_SIZE           (SPMI_RING_QUEUE_DEPTH * SPMI_DESCRIPTOR_SIZE) /* 4096 B */

/* Status return codes */
typedef enum {
    SPMI_STATUS_SUCCESS             = 0x0000,
    SPMI_STATUS_SLAVE_NACK          = 0x0001,
    SPMI_STATUS_PARITY_ERROR        = 0x0002,
    SPMI_STATUS_BUS_COLLISION       = 0x0003,
    SPMI_STATUS_TIMEOUT             = 0x0004,
    SPMI_STATUS_UNRECOGNIZED_CMD    = 0x0005,
    SPMI_STATUS_FIFO_OVERFLOW       = 0x0006
} spmi_status_t;

/* SPMI Command Ring Descriptor (16 bytes packed) */
typedef struct __attribute__((packed)) {
    uint16_t target_address;   /* Word 0 [15:0]: Target Register Address (0x0000..0xFFFF) */
    uint8_t  byte_count_minus1:4; /* Word 0 [19:16]: BC (0=1 byte, 15=16 bytes) */
    uint8_t  priority:2;       /* Word 0 [21:20]: 0=Low, 1=Med, 2=High, 3=Critical */
    uint8_t  reserved0:2;
    uint8_t  opcode:4;         /* Word 0 [27:24]: Command Opcode */
    uint8_t  slave_id:4;       /* Word 0 [31:28]: SPMI Slave ID */

    uint32_t payload_low;      /* Word 1: Data bytes 0..3 (Little Endian) */
    uint32_t payload_high;     /* Word 2: Data bytes 4..7 (Little Endian) */

    uint8_t  flags;            /* Word 3 [7:0]: Bit 0=Valid, Bit 1=IRQ on Complete, Bit 2=RD/WR */
    uint8_t  token;            /* Word 3 [15:8]: Request Sequence Token */
    uint16_t hardware_status;  /* Word 3 [31:16]: Populated by controller on completion */
} spmi_command_descriptor_t;

/* Descriptor flag bits */
#define SPMI_DESC_FLAG_VALID            (1U << 0)
#define SPMI_DESC_FLAG_IRQ_EN           (1U << 1)
#define SPMI_DESC_FLAG_IS_READ          (1U << 2)
#define SPMI_DESC_FLAG_IS_BURST         (1U << 3)

/* SPMI Response Ring Descriptor (16 bytes packed) */
typedef struct __attribute__((packed)) {
    uint16_t target_address;   /* Word 0 [15:0]: Target Register Address */
    uint8_t  byte_count;       /* Word 0 [23:16]: Actual bytes read */
    uint8_t  slave_id;         /* Word 0 [31:24]: Slave ID responding */

    uint32_t data_low;         /* Word 1: Received bytes 0..3 */
    uint32_t data_high;        /* Word 2: Received bytes 4..7 */

    uint8_t  token;            /* Word 3 [7:0]: Matching Request Token */
    uint8_t  reserved;         /* Word 3 [15:8] */
    uint16_t status;           /* Word 3 [31:16]: Execution result code */
} spmi_response_descriptor_t;

#ifdef __cplusplus
}
#endif

#endif /* APPLE_SPMI_H */
