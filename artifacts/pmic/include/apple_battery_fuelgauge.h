/*
 * apple_battery_fuelgauge.h - Clean-Room Fuel Gauge, 4-RC Model & Telemetry
 * Apple Silicon A19 Pro (t8150 / Apple H18) - AppleSmartBatteryManagerEmbedded
 *
 * Grounded in DeviceTree: /device-tree/arm-io/nub-spmi0/btm, /arm-io/pmgr/ppm
 * Kernelcache: com.apple.driver.AppleSmartBatteryManagerEmbedded, AppleBTM
 * Operating System: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 */

#ifndef APPLE_BATTERY_FUELGAUGE_H
#define APPLE_BATTERY_FUELGAUGE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * ============================================================================
 * 1. BATTERY & THERMAL MONITOR (BTM) PROTOCOL OPCODES
 * ============================================================================
 */
#define APPLE_BTM_OPCODE_PTD_READ_MULT  0x524D7470 /* 'RMtp': Multi-Word Telemetry Read */
#define APPLE_BTM_OPCODE_START          0x54534D42 /* 'TSMB': Start Periodic Telemetry */
#define APPLE_BTM_OPCODE_STOP           0x50534D42 /* 'PSMB': Stop Periodic Telemetry */
#define APPLE_BTM_OPCODE_CONFIG         0x4F434D42 /* 'OCMB': Configure Sampling Rates */
#define APPLE_BTM_OPCODE_VTHR           0x54564D42 /* 'TVMB': Set Voltage Droop Trigger */

#define APPLE_BTM_SPMI_SLAVE_ID         0x0E
#define APPLE_BTM_PMU_TYPE_PHONE        15

/*
 * ============================================================================
 * 2. 4-RC EQUIVALENT CIRCUIT BATTERY MODEL (ApplePPMBatteryModel4RC)
 * ============================================================================
 */
#define APPLE_4RC_BRANCH_COUNT          4

typedef struct {
    float r0_mohm;                     /* Ohmic internal resistance (electrolyte/contacts) */
    float r_branch_mohm[APPLE_4RC_BRANCH_COUNT]; /* Branch resistances R1..R4 (mOhm) */
    float c_branch_farads[APPLE_4RC_BRANCH_COUNT]; /* Branch capacitances C1..C4 (Farads) */
    float tau_seconds[APPLE_4RC_BRANCH_COUNT];   /* Branch time constants tau = R * C (seconds) */
    float temp_arrhenius_activation_ev;/* Arrhenius activation energy for temperature scaling */
    float reference_temp_kelvin;       /* Calibration reference temperature (298.15 K) */
} apple_4rc_battery_model_t;

/*
 * ============================================================================
 * 3. CHEMICAL RESISTANCE TABLE (Ra Table: 15 Grid Points)
 * ============================================================================
 */
#define APPLE_RA_GRID_POINTS            15

typedef struct {
    float dod_percent;                 /* Depth of Discharge (0.0% to 100.0%) */
    uint16_t ra_mohm;                  /* Measured cell resistance in milli-Ohms */
} apple_ra_point_t;

typedef struct {
    apple_ra_point_t grid[APPLE_RA_GRID_POINTS];
    uint16_t res_scale;                /* Global resistance scaling multiplier */
    uint16_t chem_id;                  /* Electrochemical chemistry identifier */
    uint32_t qmax_mah;                 /* Maximum chemical cell capacity */
    uint16_t cycle_count;              /* Completed charge/discharge cycles */
    uint8_t  ra_update_disqualified;   /* Non-zero if last update was disqualified */
    uint8_t  qmax_update_disqualified; /* Non-zero if Qmax update was disqualified */
} apple_battery_impedance_profile_t;

/*
 * ============================================================================
 * 4. BATTERY SHUTDOWN HISTORY TELEMETRY REGISTERS
 * ============================================================================
 */
typedef struct __attribute__((packed)) {
    uint32_t timestamp_epoch;          /* Timestamp when shutdown was committed */
    uint16_t shutdown_voltage_mv;      /* Battery terminal voltage at shutdown */
    uint16_t prev_voltage_mv;          /* Battery terminal voltage 100ms prior */
    int16_t  average_current_ma;       /* Rolling average discharge current */
    int16_t  filtered_current_ma;      /* Filtered instantaneous current */
    int16_t  max_discharge_current_ma; /* Maximum observed discharge pulse */
    uint16_t nominal_charge_capacity_mah; /* Capacity remaining in cell */
    uint16_t prev_nominal_capacity_mah;
    uint16_t remaining_capacity_mah;   /* UI capacity remaining */
    uint16_t full_charge_capacity_mah; /* Learned full capacity */
    uint32_t passed_charge_coulombs;   /* Cumulative Coulombs discharged */
    uint8_t  dod0_percent;             /* Initial Depth of Discharge */
    uint8_t  present_dod_percent;      /* Instantaneous Depth of Discharge */
    int16_t  temperature_deci_celsius; /* Battery temperature at shutdown */
    uint8_t  ui_soc_percent;           /* Displayed State of Charge */
    uint8_t  upo_reboot_flag;          /* Triggered by Under-Power-Out (UPO) */
    uint8_t  dyn_sd_soc;               /* Dynamic shutdown SoC threshold */
    uint16_t dyn_sd_voltage_mv;        /* Dynamic cutoff voltage threshold */
    uint16_t dynamic_soc_vcut_mv;      /* IR-compensated cutoff voltage */
    uint16_t raw_ra_table[APPLE_RA_GRID_POINTS]; /* Snapshot of Ra table */
    uint16_t res_scale;                /* Resistance scale factor */
    uint8_t  lpem_mode;                /* Low Power Efficiency Mode status */
    uint8_t  pad;
} apple_battery_shutdown_history_t;

/*
 * ============================================================================
 * 5. CRYPTOGRAPHIC BATTERY AUTHENTICATION (Beads)
 * ============================================================================
 */
#define BEADS_NONCE_SIZE_BYTES          32
#define BEADS_SIGNATURE_SIZE_BYTES      64
#define BEADS_CERT_CHAIN_MAX_BYTES      512

typedef enum {
    BEADS_STATE_IDLE                = 0,
    BEADS_STATE_CHALLENGE_ISSUED    = 1,
    BEADS_STATE_RESPONSE_RECEIVED   = 2,
    BEADS_STATE_CERT_VALIDATED      = 3,
    BEADS_STATE_AUTHENTICATED       = 4,
    BEADS_STATE_AUTH_FAILED         = 5
} beads_auth_state_t;

/* Beads Authentication Challenge Packet */
typedef struct __attribute__((packed)) {
    uint8_t  command_id;               /* 0x01 = AUTH_CHALLENGE */
    uint8_t  nonce[BEADS_NONCE_SIZE_BYTES]; /* 32-byte cryptographically secure random nonce */
    uint32_t timestamp;
} beads_auth_challenge_t;

/* Beads Authentication Response Packet */
typedef struct __attribute__((packed)) {
    uint8_t  status_code;              /* 0x00 = SUCCESS */
    uint8_t  signature_r[32];          /* ECDSA P-256 Signature R component */
    uint8_t  signature_s[32];          /* ECDSA P-256 Signature S component */
    uint16_t cert_len;
    uint8_t  cert_data[BEADS_CERT_CHAIN_MAX_BYTES]; /* Device certificate chain */
} beads_auth_response_t;

/*
 * ============================================================================
 * 6. TELEMETRY CLIENT API PROTOTYPES
 * ============================================================================
 */

/* Compute predictive Vdroop across battery load step */
float apple_battery_compute_vdroop(const apple_4rc_battery_model_t *model,
                                   float load_current_step_a,
                                   float delta_time_seconds);

/* Read raw BTM hardware frame */
int apple_btm_read_telemetry_frame(uint8_t *frame_buffer, size_t buffer_len);

#ifdef __cplusplus
}
#endif

#endif /* APPLE_BATTERY_FUELGAUGE_H */
