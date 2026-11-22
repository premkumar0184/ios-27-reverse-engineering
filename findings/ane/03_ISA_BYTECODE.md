# iOS 27 Apple Neural Engine (ANE) RE — Phase 3: Hardware ISA, Opcode Decoding & Tile Scheduling

## 1. Hardware ISA Overview

The Apple Neural Engine on Apple Silicon A19 Pro (`t8150`, generation H18 / Apollo v5) is controlled by a dedicated 64-bit coprocessor microcontroller executing the Apollo v5 real-time firmware (`h18_ane_fw_apollo_v5x.raw`). The hardware command interface relies on the **CSNE (Coprocessor Silicon Neural Engine) Command Architecture**, dispatched via dedicated DMA command channels and FIFO ring buffers.

The coprocessor orchestrates four primary execution engines:
1. **Matrix Multiplier Array (MX)**: 32-channel wide systolic multiply-accumulate array optimized for dense convolutions and matrix projections.
2. **Processing Element Array (PE)**: Vector arithmetic-logic units (ALUs), programmable lookup tables (LUTs), and neighborhood spatial pooling engines.
3. **Tile DMA Engine (DMA)**: Hardware memory transformation engine parsing 16 KB tensor tiles through Apple's DART IOMMU.
4. **Cross-Cluster DMA Interconnect (CCDMA)**: High-speed ring connecting the three physical ANE clusters (`fANE0`, `fANE1`, `fANE2`) for parallel tensor reductions.

---

## 2. Hardware Command Opcode Set (`CSNE_CMD_*`)

Static extraction from the Apollo v5 firmware binary identified the core hardware command set:

| Opcode | Mnemonic | Hardware Unit | Description | Operands |
|:---:|:---|:---:|:---|:---|
| `0x0001` | `CSNE_CMD_RESET` | Power / Core | Hardware coprocessor and engine reset | `reset_mask`, `timeout_us` |
| `0x0002` | `CSNE_CMD_LOAD_PROGRAM` | DMA / Scheduler | Load program, bind `.hwx` task descriptors, allocate L2 SRAM | `prog_id`, `td_base`, `td_count`, `l2_footprint` |
| `0x0003` | `CSNE_CMD_UNLOAD_PROGRAM` | DMA / Scheduler | Unload program context and release L2 SRAM footprint | `prog_id` |
| `0x0004` | `CSNE_CMD_CREATE_PROCESS` | MMU / DART | Allocate process execution arena and register DART IOMMU root | `proc_id`, `dart_root_paddr`, `qos` |
| `0x0005` | `CSNE_CMD_TERMINATE_PROCESS` | MMU / DART | Terminate process arena and flush DART mappings | `proc_id` |
| `0x0006` | `CSNE_CMD_PROCEDURE_CALL` | MX / PE Array | Execute procedure inference on pre-mapped input/output IOSurfaces | `prog_id`, `proc_id`, `proc_idx`, `qos`, `flags` |
| `0x0007` | `CSNE_CMD_PROCEDURE_CALL_WITH_CUSTOM_BARS` | MX / PE Array | Execute procedure with custom Base Address Register (BAR) remap table | `prog_id`, `proc_id`, `proc_idx`, `bar_mask`, `bar_table` |
| `0x0008` | `CSNE_CMD_PROCEDURE_CALL_WITH_SIGNAL_EVENTS` | Sequencer / Barrier | Execute procedure with hardware IOSurfaceSharedEvent barrier | `prog_id`, `proc_idx`, `event_id`, `signal_val`, `wait_val` |
| `0x0009` | `CSNE_CMD_LOAD_AFPP` | Fast Path Engine | Load ANE Fast Path Pipeline descriptor into register queue | `afpp_id`, `hwq_id`, `desc_addr` |
| `0x000A` | `CSNE_CMD_UNLOAD_AFPP` | Fast Path Engine | Release Fast Path Pipeline context | `afpp_id`, `hwq_id` |
| `0x000B` | `CSNE_CMD_PREMAP_BUFFER` | DART IOMMU | Asynchronously pre-register IOSurface into DART page tables | `iosurface_id`, `dart_vaddr`, `size`, `prot` |
| `0x000C` | `CSNE_CMD_DATA_CHAINING_EVENT` | Sequencer | Link procedure output to next procedure input in L2 SRAM | `src_proc`, `dst_proc`, `symbol_idx` |
| `0x000D` | `CSNE_CMD_PREFETCH_DSID_EVENT` | DMA Prefetch | Trigger asynchronous DMA tile prefetch into L2 cache | `dsid`, `tile_addr`, `tile_count` |
| `0x000E` | `CSNE_CMD_SECURE_MODE_EVENT` | Security Engine | Engage SPTM isolation barrier for protected biometric models | `domain`, `token` |

---

## 3. Mathematical 16 KB Tile Geometry & Spatial Layout

The Apple Neural Engine does not address memory linearly. All tensor transfers are organized in strict **16 KB memory tiles** (`0x4000` bytes, `TILE_SHIFT = 14`), natively operating on **32-channel aligned raster formats**.

### 3.1 Dimensions & Strides

A 4-dimensional tensor $[N, C, H, W]$ in data type size $B = 	ext{sizeof(dtype)}$ is scheduled using six spatial coordinates:
- $N$: Batch size.
- $C$: Total channel depth.
- $H$: Tensor spatial height.
- $W$: Tensor spatial width.
- $R$: Row stride in bytes (aligned to 64 bytes):
  $$R = \left\lceil rac{W 	imes B}{64} ightceil 	imes 64$$
- $P$: Channel plane pitch in bytes (aligned to 16,384 bytes):
  $$	ext{PlaneSize} = H 	imes R$$
  $$P = \left\lceil rac{	ext{PlaneSize}}{16384} ightceil 	imes 16384$$

### 3.2 Tile Coordinate Transformations

Channels are chunked into 32-channel slices:
$$	ext{ChannelGroups} = \left\lceil rac{C}{32} ightceil$$

The hardware tile geometry parameters programmed into `ZinAneTd` are:
$$	ext{TileHeight} = rac{P}{R}$$
$$	ext{TileWidth} = rac{R}{B}$$
$$	ext{TotalMemoryTiles} = rac{N 	imes 	ext{ChannelGroups} 	imes P}{16384}$$

### 3.3 Precision Encodings Supported on H18 / Apollo v5

1. **FP16 (2 Bytes)**: IEEE 754 half-precision float ($1$ sign, $5$ exponent, $10$ mantissa). Primary precision for CoreML inference.
2. **BF16 (2 Bytes)**: Brain floating point ($1$ sign, $8$ exponent, $7$ mantissa). Preserves dynamic range for modern transformer models.
3. **INT8 (1 Byte)**: Signed 8-bit quantized integer with per-channel scaling factor. Used for 4x memory bandwidth compression.
4. **UINT8 (1 Byte)**: Unsigned 8-bit quantized integer with asymmetric zero-point offset.
5. **INT4 (0.5 Bytes)**: Sub-byte 4-bit packed integer weights, enabling direct on-chip storage for large generative language models.

---

## 4. Verification & Validation Summary

- **Deliverable 1**: `artifacts/ane/ane_isa_opcode_table.json` (Complete structured schema with 14 hardware opcodes and tile geometry formulas).
- **Deliverable 2**: `findings/ane/03_ISA_BYTECODE.md` (Detailed mathematical specification and instruction encodings).
- **Exit Verification**: Passed automated validation checks via `python3 tools/verify_phase.py ane_phase_3_isa_bytecode`.
