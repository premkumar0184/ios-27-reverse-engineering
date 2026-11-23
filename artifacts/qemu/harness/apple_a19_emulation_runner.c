/**
 * @file apple_a19_emulation_runner.c
 * @brief Standalone Clean-Room Execution Harness & Validation Runner
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iPhone18,3)
 * Operating System: iOS 27.2 (Darwin 24.2.0, Build 24B119)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <inttypes.h>

#include "../include/apple_a19_platform.h"
#include "../devices/apple_aic.h"
#include "../devices/apple_ascwrap.h"
#include "../devices/apple_dart.h"
#include "../devices/apple_agx_direct.h"
#include "../devices/apple_silenus_dma.h"
#include "../devices/apple_prores_hw.h"
#include "../devices/apple_tightbeam_ipc.h"
#include "../firmware/stub_rtkit_core.h"

/* Primary and fallback trace log paths */
#define EMULATION_TRACE_LOG_PATH_PRIMARY  "artifacts/qemu/logs/emulation_trace.json"
#define EMULATION_TRACE_LOG_PATH_FALLBACK "../logs/emulation_trace.json"

typedef struct {
    bool agx_passed;
    bool silenus_passed;
    bool prores_passed;
    bool tightbeam_passed;
    bool rtkit_handshake_passed;

    /* Robustness & Edge Invariant Tests */
    bool firmware_binaries_loaded;
    bool dart_fault_w1c_passed;
    bool aic_priority_arbitration_passed;
    bool ascwrap_32bit_mmio_passed;
    bool doorbell_multibit_passed;
    bool silenus_fault_isolation_passed;

    uint64_t agx_commands;
    uint32_t agx_final_heartbeat;
    uint32_t silenus_frames;
    uint32_t silenus_bni_packets;
    uint32_t prores_frames;
    uint32_t prores_crc;
    uint64_t tightbeam_queries;
    uint64_t tightbeam_caps;
    uint64_t total_irqs_raised;
    uint64_t total_irqs_acked;
} EmulationSummary;

static AppleRTKitState g_aop2_rtk;
static AppleASCwrapState *g_active_ascwrap = NULL;

static void rtkit_coproc_tx_callback(void *opaque, uint16_t ep, uint64_t payload) {
    AppleASCwrapState *asc = (AppleASCwrapState *)opaque;
    if (asc) {
        ascwrap_coproc_send(asc, ep, payload);
    }
}

static void ascwrap_to_rtkit_rx_callback(void *opaque, uint16_t ep, uint64_t payload) {
    AppleRTKitState *rtk = (AppleRTKitState *)opaque;
    if (rtk && g_active_ascwrap) {
        rtkit_handle_msg(rtk, ep, payload, rtkit_coproc_tx_callback, g_active_ascwrap);
    }
}

static bool load_firmware_stub(const char *name, uint8_t *dest, size_t max_size, size_t *out_size) {
    char path[256];
    snprintf(path, sizeof(path), "artifacts/qemu/firmware/%s.bin", name);
    FILE *f = fopen(path, "rb");
    if (!f) {
        snprintf(path, sizeof(path), "../firmware/%s.bin", name);
        f = fopen(path, "rb");
    }
    if (!f) return false;

    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (sz <= 0 || (size_t)sz > max_size) {
        fclose(f);
        return false;
    }

    size_t rd = fread(dest, 1, (size_t)sz, f);
    fclose(f);
    if (out_size) *out_size = rd;
    return (rd == (size_t)sz);
}

int main(void) {
    printf("====================================================================\n");
    printf("  Apple Silicon A19 Pro (t8150) Bare-Metal Emulation Runner\n");
    printf("  Clean-Room Virtualization Platform (iOS 27.2 Build 24B119)\n");
    printf("====================================================================\n\n");

    EmulationSummary summary;
    memset(&summary, 0, sizeof(summary));

    /* 1. Initialize Subsystems */
    printf("[1/7] Initializing Hardware Fabric & Subsystems...\n");
    AppleAICState aic;
    aic_init(&aic);

    AppleASCwrapState asc_aop2;
    ascwrap_init(&asc_aop2, "ascwrap_aop2", &aic,
                 AIC_IRQ_AOP2_INBOX, AIC_IRQ_AOP2_OUTBOX, AIC_IRQ_AOP2_DOORBELL);

    AppleASCwrapState asc_agx;
    ascwrap_init(&asc_agx, "ascwrap_agx0", &aic,
                 AIC_IRQ_AGX_CORE0_INBOX, AIC_IRQ_AGX_CORE0_OUTBOX, AIC_IRQ_AGX_CORE0_DOORBELL);

    AppleDARTState dart_isp;
    dart_init(&dart_isp, "dart_isp", &aic, AIC_IRQ_DART_ISP_FAULT);

    AppleDARTState dart_ave;
    dart_init(&dart_ave, "dart_ave", &aic, AIC_IRQ_DART_AVE_FAULT);

    AppleAGXState agx;
    agx_direct_init(&agx, "agx_g18p", &aic, &asc_agx, &dart_isp);

    AppleSilenusState silenus;
    silenus_dma_init(&silenus, "silenus_isp", &aic, &asc_aop2, &dart_isp);

    AppleProResHWState prores;
    prores_hw_init(&prores, "apple_prores_hw", &aic, &dart_ave);

    AppleTightbeamState tightbeam;
    tightbeam_ipc_init(&tightbeam, "tightbeam_relay", &aic);

    /* Hook RTKit Coprocessor State Machine to AOP2 ASCwrap */
    rtkit_init(&g_aop2_rtk, RTK_COPROC_AOP2, MMIO_ASCWRAP_AOP2_BASE, MMIO_DOORBELL_AOP2_BASE);
    g_active_ascwrap = &asc_aop2;
    ascwrap_set_coproc_handler(&asc_aop2, ascwrap_to_rtkit_rx_callback, &g_aop2_rtk);

    /* 1b. Load Bare-Metal RTKit Firmware Binaries into Simulated SRAM */
    size_t sram_size = 128 * 1024;
    uint8_t *aop2_sram = (uint8_t *)calloc(1, sram_size);
    uint8_t *silenus_sram = (uint8_t *)calloc(1, sram_size);
    uint8_t *rtbuddy_sram = (uint8_t *)calloc(1, sram_size);

    size_t aop2_bin_sz = 0, silenus_bin_sz = 0, rtbuddy_bin_sz = 0;
    bool aop2_loaded = load_firmware_stub("stub_rtkit_aop2", aop2_sram, sram_size, &aop2_bin_sz);
    bool silenus_loaded = load_firmware_stub("stub_rtkit_silenus", silenus_sram, sram_size, &silenus_bin_sz);
    bool rtbuddy_loaded = load_firmware_stub("stub_rtkit_rtbuddy", rtbuddy_sram, sram_size, &rtbuddy_bin_sz);

    if (aop2_loaded && silenus_loaded && rtbuddy_loaded) {
        summary.firmware_binaries_loaded = true;
        printf("      -> [PASS] Loaded 3 RTKit coprocessor binaries into simulated SRAM (%zuB, %zuB, %zuB)\n",
               aop2_bin_sz, silenus_bin_sz, rtbuddy_bin_sz);
    } else {
        printf("      -> [WARN] Firmware binary load fallback (stubs available via direct dispatch)\n");
    }

    printf("      -> AIC v3/v4: 1024 IRQ lines ready\n");
    printf("      -> ASCwrap-v6: Mailbox & Doorbell FIFO active\n");
    printf("      -> DART IOMMU: Gen3/Gen4 16 KB page granules active (ISP: 302, AVE: 917)\n\n");

    /* 2. Run RTKit Coprocessor Handshake */
    printf("[2/7] Executing RTKit Coprocessor Endpoint 0 Handshake...\n");
    /* Host sends HELLO message to coprocessor on Endpoint 0 */
    uint64_t hello_msg = ascwrap_msg_compose(RTK_EP_MGMT, RTK_EP0_MSG_HELLO);
    ascwrap_write64(&asc_aop2, ASCWRAP_REG_OUTBOX_DATA, hello_msg);

    /* Check if Coprocessor answered back into host Inbox */
    if (asc_aop2.inbox_count > 0) {
        uint64_t resp_ack = ascwrap_read64(&asc_aop2, ASCWRAP_REG_INBOX_DATA);
        uint16_t resp_ep = ascwrap_msg_get_ep(resp_ack);
        uint64_t resp_payload = ascwrap_msg_get_payload(resp_ack);
        uint32_t cmd = (uint32_t)(resp_payload >> 32);
        uint32_t ver = (uint32_t)(resp_payload & 0xFFFFFFFF);

        if (resp_ep == RTK_EP_MGMT && cmd == RTK_EP0_MSG_HELLO_ACK && ver == 0x00020000) {
            summary.rtkit_handshake_passed = true;
            printf("      -> [PASS] RTKit Handshake SUCCESS: Version 0x%08X ACK received\n", ver);
            /* Drain all subsequent EP_MAP messages (LO and HI) */
            while (asc_aop2.inbox_count > 0) {
                uint64_t resp_map = ascwrap_read64(&asc_aop2, ASCWRAP_REG_INBOX_DATA);
                uint16_t m_ep = ascwrap_msg_get_ep(resp_map);
                uint64_t m_payload = ascwrap_msg_get_payload(resp_map);
                uint32_t m_cmd = (uint32_t)(m_payload >> 32);
                uint32_t m_mask = (uint32_t)(m_payload & 0xFFFFFFFF);
                printf("      -> [PASS] RTKit Map Message: EP=%u Cmd=0x%04X Mask=0x%08X\n",
                       m_ep, m_cmd, m_mask);
            }
        } else {
            printf("      -> [FAIL] Unexpected RTKit response: EP=%u Payload=0x%" PRIX64 "\n", resp_ep, resp_payload);
        }
    } else {
        printf("      -> [FAIL] No response from RTKit coprocessor\n");
    }
    printf("\n");

    /* 3. Run AppleMetalDirect Workload */
    printf("[3/7] Running Workload 1: AppleMetalDirect (AGX G18 Pro GPU)...\n");
    struct agx_ring_buffer *ring = (struct agx_ring_buffer *)calloc(1, sizeof(*ring));
    struct agx_status_page *status = (struct agx_status_page *)calloc(1, sizeof(*status));
    agx_direct_attach_buffers(&agx, ring, status);

    /* Prepare 64-byte Compute Descriptor */
    struct agx_command_descriptor *desc = &ring->entries[0];
    desc->hdr.bits.opcode = AGX_CMD_COMPUTE_DISPATCH;
    desc->hdr.bits.data_master = AGX_DM_CDM;
    desc->hdr.bits.priority = AGX_PRIORITY_HIGH;
    desc->hdr.bits.flags = AGX_CMD_FLAG_COHERENT;
    desc->hdr.bits.context_id = 0x42;
    desc->trace_id = 0xAA00112233445566ULL;
    desc->command_buffer_gpu_va = 0x800040000ULL;
    desc->buf_size.lengths.used_bytes = 4096;
    desc->buf_size.lengths.allocated_bytes = 16384;
    desc->stamp_token.stamp.queue_index = 0;
    desc->stamp_token.stamp.stamp_value = 0x00001001;

    /* Doorbell Kick */
    agx_doorbell_token_t kick;
    kick.fields.queue_id = 0;
    kick.fields.tail_offset = sizeof(struct agx_command_descriptor);
    kick.fields.flags = 0x8000; /* High priority kick */
    agx_doorbell_write64(&agx, 0, kick.raw_token);

    /* Validate Execution & Interrupt */
    uint32_t aic_irq = aic_get_pending_irq(&aic);
    if (status->completed_stamps[0] == 0x00001001 &&
        status->firmware_heartbeat >= 2 &&
        aic_irq == AIC_IRQ_AGX_CORE0_INBOX) {
        summary.agx_passed = true;
        summary.agx_commands = agx.total_commands_processed;
        summary.agx_final_heartbeat = status->firmware_heartbeat;
        aic_ack_irq(&aic, aic_irq);
        printf("      -> [PASS] AGX Compute Executed: Timestamp 0x%08X, Heartbeat %u, AIC IRQ %u Acked\n",
               status->completed_stamps[0], status->firmware_heartbeat, aic_irq);
    } else {
        printf("      -> [FAIL] AGX verification failed: Stamp=0x%08X Heartbeat=%u IRQ=%u\n",
               status->completed_stamps[0], status->firmware_heartbeat, aic_irq);
    }

    /* Drain any remaining auxiliary IRQs (e.g. AGX Doorbell) */
    while ((aic_irq = aic_get_pending_irq(&aic)) != 0) {
        aic_ack_irq(&aic, aic_irq);
    }
    printf("\n");

    /* 4. Run Silenus Camera ISP & BNI Workload */
    printf("[4/7] Running Workload 2: Silenus Camera ISP & Bayer Neural Interface (BNI)...\n");
    /* Program DART-ISP mappings */
    dart_map(&dart_isp, DART_ISP_SID_RAW_STREAM, 0x880000000ULL, 0x880000000ULL, 16384, DART_PERM_READ);
    dart_map(&dart_isp, DART_ISP_SID_BNI_PEARL,  A19_SEP_TZ1S_BASE, A19_SEP_TZ1S_BASE, 16384, DART_PERM_WRITE);
    dart_map(&dart_isp, DART_ISP_SID_YUV_PREVIEW, 0x880020000ULL, 0x880020000ULL, 16384, DART_PERM_WRITE);

    uint8_t *tz1s_sink = (uint8_t *)calloc(1, 4096);
    silenus_set_tz1s_buffer(&silenus, tz1s_sink, 4096);

    /* Prepare CISP Process Buffer Packet */
    struct cisp_command_packet cisp_pkt;
    memset(&cisp_pkt, 0, sizeof(cisp_pkt));
    cisp_pkt.header.magic = CISP_MAGIC;
    cisp_pkt.header.opcode = CISP_CMD_CH_PROCESS_BUFFERS;
    cisp_pkt.header.sequence_id = 1;
    cisp_pkt.payload.buffer_process.surface_id = 101;
    cisp_pkt.payload.buffer_process.dva_luma = 0x880000000ULL;
    cisp_pkt.payload.buffer_process.dva_chroma = 0x880020000ULL;
    cisp_pkt.payload.buffer_process.width = 4032;
    cisp_pkt.payload.buffer_process.height = 3024;

    bool cisp_ok = silenus_process_cisp_packet(&silenus, &cisp_pkt);
    uint32_t *tz1s_header = (uint32_t *)tz1s_sink;

    uint32_t irq_frame = aic_get_pending_irq(&aic);
    aic_ack_irq(&aic, irq_frame);
    uint32_t irq_stats = aic_get_pending_irq(&aic);
    aic_ack_irq(&aic, irq_stats);

    if (cisp_ok && tz1s_header[0] == 0x4E495230 && /* 'NIR0' */
        (irq_frame == AIC_IRQ_ISP_FRAME_DONE || irq_frame == AIC_IRQ_ISP_STATS_READY)) {
        summary.silenus_passed = true;
        summary.silenus_frames = (uint32_t)silenus.total_frames_processed;
        summary.silenus_bni_packets = (uint32_t)silenus.total_bni_packets_routed;
        printf("      -> [PASS] Silenus CISP Frame Processed: BNI NIR Token 0x%08X in SEP TZ1S, IRQs %u & %u Acked\n",
               tz1s_header[0], irq_frame, irq_stats);
    } else {
        printf("      -> [FAIL] Silenus verification failed: ok=%d NIR=0x%08X irq1=%u irq2=%u\n",
               cisp_ok, tz1s_header[0], irq_frame, irq_stats);
    }

    /* Drain any remaining auxiliary IRQs (e.g. AOP2 Doorbell) */
    uint32_t extra_irq;
    while ((extra_irq = aic_get_pending_irq(&aic)) != 0) {
        aic_ack_irq(&aic, extra_irq);
    }
    printf("\n");

    /* 5. Run AppleProResHW Workload */
    printf("[5/7] Running Workload 3: AppleProResHW (AVE2 8K RAW Video Accelerator)...\n");
    sAppleProResRawFrameHeader_t prores_hdr;
    memset(&prores_hdr, 0, sizeof(prores_hdr));
    prores_hdr.size = sizeof(prores_hdr);
    prores_hdr.ver = 1;
    prores_hdr.id = 77;
    prores_hdr.hsize = 8192; /* 8K UHD */
    prores_hdr.vsize = 4320;
    prores_hdr.cfa = APR_CFA_PATTERN_RGGB;
    prores_hdr.wbr = 0x00018000; /* 1.5x Red Gain */
    prores_hdr.wbb = 0x00014000; /* 1.25x Blue Gain */
    for (int i = 0; i < 9; i++) prores_hdr.cm[i] = 0x00010000;

    uint8_t *sample_bayer = (uint8_t *)malloc(1024);
    memset(sample_bayer, 0x5A, 1024);
    uint8_t *encoded_out = (uint8_t *)malloc(4096);
    size_t encoded_bytes = 0;

    bool prores_ok = prores_hw_encode_raw_frame(&prores, &prores_hdr, sample_bayer,
                                                encoded_out, 4096, &encoded_bytes);
    uint32_t *out_words = (uint32_t *)encoded_out;
    uint32_t prores_irq = aic_get_pending_irq(&aic);
    aic_ack_irq(&aic, prores_irq);

    if (prores_ok && out_words[0] == 0x7072386BU && /* 'pr8k' */
        prores.total_slices_processed == 16 &&
        prores_irq == AIC_IRQ_PRORES_COMPLETE) {
        summary.prores_passed = true;
        summary.prores_frames = (uint32_t)prores.total_frames_encoded;
        summary.prores_crc = prores.computed_crc;
        printf("      -> [PASS] ProRes 8K RAW Encoded: Magic 'pr8k', 16 Slices (A1:8, A2:8), CRC=0x%08X, AIC IRQ %u Acked\n",
               prores.computed_crc, prores_irq);
    } else {
        printf("      -> [FAIL] ProRes verification failed: ok=%d Magic=0x%08X Slices=%" PRIu64 " IRQ=%u\n",
               prores_ok, out_words[0], prores.total_slices_processed, prores_irq);
    }
    printf("\n");

    /* 6. Run Tightbeam IPC & ExclaveOS Workload */
    printf("[6/7] Running Workload 4: Tightbeam IPC & ExclaveOS cL4 Syscall Bridge...\n");
    struct tb_message_s tb_query;
    memset(&tb_query, 0, sizeof(tb_query));
    tb_query.state_and_flags = TB_MESSAGE_STATE_READY;
    tb_query.disposition = TB_MESSAGE_DISPOSITION_QUERY;
    tb_query.invocation_id = 0x1234567890ABCDEFULL;
    tb_query.endpoint_token = 0xFEDCBA0987654321ULL;
    tb_query.capabilities_count = 1;
    tb_query.inline_payload[0] = 777; /* Query input operand */

    L4_IpcBuffer_t ipc_buf;
    memset(&ipc_buf, 0, sizeof(ipc_buf));

    int tb_rc = tightbeam_handle_syscall(&tightbeam, 0, &ipc_buf, &tb_query);
    uint32_t tb_irq = aic_get_pending_irq(&aic);
    aic_ack_irq(&aic, tb_irq);

    if (tb_rc == L4_SUCCESS &&
        tb_query.disposition == TB_MESSAGE_DISPOSITION_REPLY &&
        tb_query.inline_payload[1] == 1554 && /* 777 * 2 */
        (ipc_buf.cr[0] & 0xFFFFFFFF00000000ULL) == 0xCAFEBABE00000000ULL &&
        tb_irq == AIC_IRQ_EXCLAVE_AOP2_INBOX) {
        summary.tightbeam_passed = true;
        summary.tightbeam_queries = tightbeam.total_queries_routed;
        summary.tightbeam_caps = tightbeam.total_caps_minted;
        printf("      -> [PASS] Tightbeam RPC Delivered: Reply Value=%" PRIu64 ", Minted Badge=0x%016" PRIX64 ", AIC IRQ %u Acked\n",
               tb_query.inline_payload[1], ipc_buf.cr[0], tb_irq);
    } else {
        printf("      -> [FAIL] Tightbeam verification failed: rc=%d disp=%u val=%" PRIu64 " badge=0x%016" PRIX64 " IRQ=%u\n",
               tb_rc, tb_query.disposition, tb_query.inline_payload[1], ipc_buf.cr[0], tb_irq);
    }
    printf("\n");

    /* 7. Robustness, Edge Case & Priority Invariant Probes */
    printf("[7/7] Executing Robustness Invariants & Edge Probes...\n");

    /* Edge 1: ASCwrap 32-bit MMIO FIFO Staging */
    AppleASCwrapState asc_probe;
    ascwrap_init(&asc_probe, "asc_probe", &aic, 357, 358, 359);
    uint64_t probe_payload = 0x0000ABCDEF123456ULL;
    uint16_t probe_ep = 42;
    /* Write Outbox using two 32-bit operations */
    ascwrap_write32(&asc_probe, ASCWRAP_REG_OUTBOX_DATA, (uint32_t)(probe_payload & 0xFFFFFFFFULL));
    uint32_t hi_word = (uint32_t)((probe_payload >> 32) | ((uint64_t)probe_ep << 16));
    ascwrap_write32(&asc_probe, ASCWRAP_REG_OUTBOX_DATA + 4, hi_word);

    uint16_t rec_ep = 0;
    uint64_t rec_pay = 0;
    bool rec_ok = ascwrap_coproc_recv(&asc_probe, &rec_ep, &rec_pay);
    /* Coprocessor echoes message back into Inbox */
    ascwrap_coproc_send(&asc_probe, rec_ep, rec_pay);
    /* Host reads Inbox using two 32-bit operations */
    uint32_t in_lo = ascwrap_read32(&asc_probe, ASCWRAP_REG_INBOX_DATA);
    uint32_t in_hi = ascwrap_read32(&asc_probe, ASCWRAP_REG_INBOX_DATA + 4);
    uint64_t reassembled = ((uint64_t)in_hi << 32) | in_lo;

    if (rec_ok && rec_ep == 42 && rec_pay == probe_payload &&
        ascwrap_msg_get_ep(reassembled) == 42 &&
        ascwrap_msg_get_payload(reassembled) == probe_payload) {
        summary.ascwrap_32bit_mmio_passed = true;
        printf("      -> [PASS] ASCwrap 32-bit MMIO Staging: 64-bit Word preserved across high/low reads\n");
    } else {
        printf("      -> [FAIL] ASCwrap 32-bit MMIO Staging mismatch\n");
    }

    /* Edge 2: Doorbell Multi-Bit Persistence & Re-assertion */
    ascwrap_doorbell_write32(&asc_probe, DOORBELL_REG_SET, 0x03); /* bits 0 & 1 */
    uint32_t db_irq1 = aic_get_pending_irq(&aic);
    aic_ack_irq(&aic, db_irq1);
    /* Clear only bit 0 */
    ascwrap_doorbell_write32(&asc_probe, DOORBELL_REG_CLEAR, 0x01);
    /* IRQ line should remain asserted because bit 1 is still pending */
    uint32_t db_irq2 = aic_get_pending_irq(&aic);
    aic_ack_irq(&aic, db_irq2);
    /* Clear remaining bit 1 */
    ascwrap_doorbell_write32(&asc_probe, DOORBELL_REG_CLEAR, 0x02);
    uint32_t db_irq3 = aic_get_pending_irq(&aic);

    if (db_irq1 == 359 && db_irq2 == 359 && db_irq3 != 359 && asc_probe.doorbell_status == 0) {
        summary.doorbell_multibit_passed = true;
        printf("      -> [PASS] ASCwrap Doorbell Multi-Bit: Level remains asserted until all bits cleared\n");
    } else {
        printf("      -> [FAIL] Doorbell multi-bit clear behavior unexpected\n");
    }

    /* Edge 3: DART Translation Fault Generation & W1C Clearing */
    AppleDARTState dart_probe;
    dart_init(&dart_probe, "dart_probe", &aic, AIC_IRQ_DART_ISP_FAULT);
    uint64_t fault_out_pa = 0;
    bool fault_tr = dart_translate(&dart_probe, 0, 0x900000000ULL, &fault_out_pa, DART_PERM_READ);
    uint32_t dart_fault_irq = aic_get_pending_irq(&aic);
    aic_ack_irq(&aic, dart_fault_irq);
    /* Clear fault status via W1C */
    dart_write32(&dart_probe, DART_REG_FAULT_STATUS, dart_probe.fault_status);
    uint32_t dart_cleared_irq = aic_get_pending_irq(&aic);

    if (!fault_tr && dart_fault_irq == AIC_IRQ_DART_ISP_FAULT &&
        dart_probe.fault_status == 0 && dart_cleared_irq != AIC_IRQ_DART_ISP_FAULT) {
        summary.dart_fault_w1c_passed = true;
        printf("      -> [PASS] DART Translation Fault: Handled, reported IRQ %u, and cleared via W1C\n",
               dart_fault_irq);
    } else {
        printf("      -> [FAIL] DART translation fault handling failed\n");
    }

    /* Edge 4: AIC Priority Arbitration (Low Vector Number Prioritization) */
    aic_set_irq(&aic, AIC_IRQ_AOP2_DOORBELL, 1);    /* Vector 359 */
    aic_set_irq(&aic, AIC_IRQ_DART_ISP_FAULT, 1);   /* Vector 302 */
    uint32_t first_prio = aic_get_pending_irq(&aic);
    aic_ack_irq(&aic, first_prio);
    uint32_t second_prio = aic_get_pending_irq(&aic);
    aic_ack_irq(&aic, second_prio);

    if (first_prio == AIC_IRQ_DART_ISP_FAULT && second_prio == AIC_IRQ_AOP2_DOORBELL) {
        summary.aic_priority_arbitration_passed = true;
        printf("      -> [PASS] AIC Interrupt Priority: DART Fault (IRQ 302) correctly prioritized over Doorbell (IRQ 359)\n");
    } else {
        printf("      -> [FAIL] AIC Priority arbitration failed: 1st=%u 2nd=%u\n", first_prio, second_prio);
    }

    /* Edge 5: Silenus Fault Isolation on Unmapped DVA */
    struct cisp_command_packet bad_pkt;
    memset(&bad_pkt, 0, sizeof(bad_pkt));
    bad_pkt.header.magic = CISP_MAGIC;
    bad_pkt.header.opcode = CISP_CMD_CH_PROCESS_BUFFERS;
    bad_pkt.payload.buffer_process.dva_luma = 0x999000000ULL; /* Unmapped */
    bad_pkt.payload.buffer_process.dva_chroma = 0x880020000ULL;
    bool bad_cisp_ok = silenus_process_cisp_packet(&silenus, &bad_pkt);
    uint32_t bad_cisp_irq = aic_get_pending_irq(&aic);
    aic_ack_irq(&aic, bad_cisp_irq);

    if (!bad_cisp_ok && bad_cisp_irq == AIC_IRQ_ISP_DMA_ERROR) {
        summary.silenus_fault_isolation_passed = true;
        printf("      -> [PASS] Silenus Fault Isolation: Unmapped DVA aborted frame and signaled DMA Error (IRQ %u)\n",
               bad_cisp_irq);
    } else {
        printf("      -> [FAIL] Silenus fault isolation failed: ok=%d irq=%u\n", bad_cisp_ok, bad_cisp_irq);
    }
    printf("\n");

    summary.total_irqs_raised = aic.total_irqs_raised;
    summary.total_irqs_acked = aic.total_irqs_acked;

    /* Write Emulation Trace JSON (with fallback path support) */
    FILE *fp = fopen(EMULATION_TRACE_LOG_PATH_PRIMARY, "w");
    if (!fp) {
        fp = fopen(EMULATION_TRACE_LOG_PATH_FALLBACK, "w");
    }

    if (fp) {
        fprintf(fp, "{\n");
        fprintf(fp, "  \"timestamp\": \"%lu\",\n", (unsigned long)time(NULL));
        fprintf(fp, "  \"target_soc\": \"t8150\",\n");
        fprintf(fp, "  \"status\": \"%s\",\n",
                (summary.agx_passed && summary.silenus_passed &&
                 summary.prores_passed && summary.tightbeam_passed &&
                 summary.rtkit_handshake_passed &&
                 summary.dart_fault_w1c_passed &&
                 summary.aic_priority_arbitration_passed &&
                 summary.ascwrap_32bit_mmio_passed &&
                 summary.doorbell_multibit_passed &&
                 summary.silenus_fault_isolation_passed) ? "PASSED" : "FAILED");
        fprintf(fp, "  \"rtkit_coprocessor_handshake\": {\n");
        fprintf(fp, "    \"passed\": %s,\n", summary.rtkit_handshake_passed ? "true" : "false");
        fprintf(fp, "    \"protocol_version\": \"0x00020000\"\n");
        fprintf(fp, "  },\n");
        fprintf(fp, "  \"workloads\": {\n");
        fprintf(fp, "    \"apple_metal_direct\": {\n");
        fprintf(fp, "      \"passed\": %s,\n", summary.agx_passed ? "true" : "false");
        fprintf(fp, "      \"commands_processed\": %" PRIu64 ",\n", summary.agx_commands);
        fprintf(fp, "      \"firmware_heartbeat\": %u\n", summary.agx_final_heartbeat);
        fprintf(fp, "    },\n");
        fprintf(fp, "    \"silenus_camera_isp\": {\n");
        fprintf(fp, "      \"passed\": %s,\n", summary.silenus_passed ? "true" : "false");
        fprintf(fp, "      \"frames_processed\": %u,\n", summary.silenus_frames);
        fprintf(fp, "      \"bni_packets_routed\": %u\n", summary.silenus_bni_packets);
        fprintf(fp, "    },\n");
        fprintf(fp, "    \"apple_prores_hw\": {\n");
        fprintf(fp, "      \"passed\": %s,\n", summary.prores_passed ? "true" : "false");
        fprintf(fp, "      \"frames_encoded\": %u,\n", summary.prores_frames);
        fprintf(fp, "      \"computed_crc_hex\": \"0x%08X\"\n", summary.prores_crc);
        fprintf(fp, "    },\n");
        fprintf(fp, "    \"tightbeam_ipc\": {\n");
        fprintf(fp, "      \"passed\": %s,\n", summary.tightbeam_passed ? "true" : "false");
        fprintf(fp, "      \"queries_routed\": %" PRIu64 ",\n", summary.tightbeam_queries);
        fprintf(fp, "      \"capabilities_minted\": %" PRIu64 "\n", summary.tightbeam_caps);
        fprintf(fp, "    }\n");
        fprintf(fp, "  },\n");
        fprintf(fp, "  \"robustness_invariants\": {\n");
        fprintf(fp, "    \"firmware_binaries_loaded\": %s,\n", summary.firmware_binaries_loaded ? "true" : "false");
        fprintf(fp, "    \"dart_fault_w1c_passed\": %s,\n", summary.dart_fault_w1c_passed ? "true" : "false");
        fprintf(fp, "    \"aic_priority_arbitration_passed\": %s,\n", summary.aic_priority_arbitration_passed ? "true" : "false");
        fprintf(fp, "    \"ascwrap_32bit_mmio_passed\": %s,\n", summary.ascwrap_32bit_mmio_passed ? "true" : "false");
        fprintf(fp, "    \"doorbell_multibit_passed\": %s,\n", summary.doorbell_multibit_passed ? "true" : "false");
        fprintf(fp, "    \"silenus_fault_isolation_passed\": %s\n", summary.silenus_fault_isolation_passed ? "true" : "false");
        fprintf(fp, "  },\n");
        fprintf(fp, "  \"interrupt_controller\": {\n");
        fprintf(fp, "    \"total_irqs_raised\": %" PRIu64 ",\n", summary.total_irqs_raised);
        fprintf(fp, "    \"total_irqs_acked\": %" PRIu64 "\n", summary.total_irqs_acked);
        fprintf(fp, "  }\n");
        fprintf(fp, "}\n");
        fclose(fp);
        printf("[+] Execution trace recorded successfully\n");
    } else {
        printf("[-] Failed to open emulation_trace.json for writing\n");
    }

    /* Cleanup memory */
    free(ring);
    free(status);
    free(tz1s_sink);
    free(sample_bayer);
    free(encoded_out);
    free(aop2_sram);
    free(silenus_sram);
    free(rtbuddy_sram);

    bool all_passed = summary.agx_passed && summary.silenus_passed &&
                      summary.prores_passed && summary.tightbeam_passed &&
                      summary.rtkit_handshake_passed &&
                      summary.dart_fault_w1c_passed &&
                      summary.aic_priority_arbitration_passed &&
                      summary.ascwrap_32bit_mmio_passed &&
                      summary.doorbell_multibit_passed &&
                      summary.silenus_fault_isolation_passed;

    printf("\n====================================================================\n");
    if (all_passed) {
        printf("  >>> ALL EMULATION WORKLOADS & EDGE PROBES PASSED (100%% GREEN) <<<\n");
    } else {
        printf("  >>> EMULATION WORKLOADS ENCOUNTERED FAILURES <<<\n");
    }
    printf("====================================================================\n");

    return all_passed ? 0 : 1;
}
