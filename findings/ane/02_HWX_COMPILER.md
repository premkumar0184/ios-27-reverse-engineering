# iOS 27 Apple Neural Engine (ANE) RE — Phase 2: Model Compilation & HWX Container Dissection

## 1. Executive Architecture Summary

In iOS 27.2 on Apple Silicon A19 Pro (`t8150`, generation H18 / Apollo v5), the Apple Neural Engine bypasses all traditional GPU and CPU execution paths by compiling neural network computational graphs into proprietary **`.hwx` ("Hardware Executable")** binary packages. This compilation is performed by **`ANECompiler.framework`** (subcache `.11` at VM `0x1ab96c000`, 33,530,684 bytes), which lowers high-level MIL (`MIL.framework`) and CoreML graph representations through Apple's internal compiler dialect **`MPS-ANEC`** into **`ZinIr`** (the ANE Intermediate Representation).

The resulting `.hwx` bundle contains discrete hardware-mapped sections:
1. **Task Descriptors (`__DATA.__td`)**: Fixed-size 128-byte parameter packets (`ZinAneTd<36>`) driving DMA engines and base address registers (BARs).
2. **Task Stream (`__DATA.__tsk`)**: Microcode execution sequences scheduled on the Apollo v5 microcontroller.
3. **Kernel Weights (`__DATA.__krn`)**: 32-channel aligned quantized parameter tensors (FP16/INT8/UINT8) tailored for 16 KB SRAM hardware memory tiles.
4. **Network Descriptors (`__DATA.__desc`)**: Model procedure DAGs, input/output tensor shapes, and IOSurface memory mapping attributes.

---

## 2. ANECompiler Lowering Pipeline & Pass Architecture

Analysis of compiler source paths in `ANECompiler.framework` reveals an end-to-end 7-stage lowering pipeline:

```
[CoreML / PyTorch / ONNX]
          │
          ▼
   MIL Graph (MIL.framework)
          │
          ▼
  MPS-ANEC Dialect (MLIR Transform Passes)
          │
          ▼
   ZinMirPrepare (Active NE selection, batch & spatial graph splitting, L2 legalization)
          │
          ▼
   ZinMirOpt (Merge deconv/conv, fully-connected fusion, activation folding)
          │
          ▼
   ZinIrSchedule (ZinCpBasedAllocator: Critical Path Allocator & parallel DAG scheduler)
          │
          ▼
   ZinIrRegAlloc (ZinIrLocalRegAlloc: Multi-segment spilling & L2 SRAM footprint planning)
          │
          ▼
   ZinIrCodegen (ZinCodegen_v11 / ZinCodegen_v7: RunTDCodeGen & RunRTCodeGen)
          │
          ▼
   ZinLinker (Assembly into .hwx container: td, tsk, krn, desc, net.plist)
```

### 2.1 ZinMirPrepare: Graph Partitioning & Legalization
- **Spatial Splitting**: Models exceeding the 16 KB tile cache or L2 SRAM footprint are partitioned along the spatial ($H, W$) or channel ($C$) dimensions via `ZinMirSpatialSplitUtils` and `ZinMirBatchOrChannelSplitter`.
- **L2 Legalization**: `ZinMirL2Legalizer` validates that live tensor allocations do not exceed the on-chip SRAM capacity (typically 8 MB to 16 MB shared L2 on t8150).

### 2.2 ZinMirOpt: Operator Fusion
- **Conv + Bias + Activation Fusion**: `ZinNEConvLayer` automatically folds scale, bias addition, and non-linear activation functions (ReLU, GeLU, SiLU/Swish) into the single-cycle output stage of the Processing Element (PE) matrix pipeline.
- **Merge Deconv / Conv**: Transposed convolutions are merged with adjacent operations via `ZinMirOptMergeDeconvConv`.
- **Batch Normalization / LayerNorm**: Folded into matrix multiply weight scaling factors during `ZinMirOptFullyConnectedLayer`.

### 2.3 ZinIrSchedule: Critical Path Allocator
- `ZinCpBasedAllocator` calculates latency cost models across physical ANE clusters (`fANE0`, `fANE1`, `fANE2`) using `ZinMirGraphSplitLatencyCostModel`.
- Assigns Base Address Registers (`bar_id` 0..7) to balance memory bandwidth across DART IOMMU channels.

---

## 3. The `.hwx` Binary Container Specification

A compiled `.hwx` package is organized either as a directory bundle (`model.hwx/`) or as a monolithic Mach-O container. The binary header structure (`anec_header_t`) layout extracted from `ANECompiler` is detailed below:

### 3.1 ANEC Binary Header Layout (128 Bytes)

| Offset | Field Name | Data Type | Size (Bytes) | Description |
|:---|:---|:---|:---:|:---|
| `0x00` | `magic` | `uint32_t` | 4 | Magic signature `0x414e4543` (`"ANEC"`) |
| `0x04` | `hw_version` | `uint32_t` | 4 | Hardware architecture generation (H18 = `36`) |
| `0x08` | `flags` | `uint32_t` | 4 | Compilation mode, QoS flags, caching policy |
| `0x0c` | `num_procedures` | `uint32_t` | 4 | Subgraph procedure count |
| `0x10` | `td_section_offset` | `uint64_t` | 8 | Offset to Task Descriptor section (`__DATA.__td`) |
| `0x18` | `td_section_size` | `uint64_t` | 8 | Byte length of `td` section |
| `0x20` | `tsk_section_offset` | `uint64_t` | 8 | Offset to Task Stream microcode section (`__DATA.__tsk`) |
| `0x28` | `tsk_section_size` | `uint64_t` | 8 | Byte length of `tsk` section |
| `0x30` | `krn_section_offset` | `uint64_t` | 8 | Offset to Kernel Weights section (`__DATA.__krn`) |
| `0x38` | `krn_section_size` | `uint64_t` | 8 | Byte length of `krn` section |
| `0x40` | `desc_section_offset`| `uint64_t` | 8 | Offset to Network Descriptor section (`__DATA.__desc`) |
| `0x48` | `desc_section_size`  | `uint64_t` | 8 | Byte length of `desc` section |
| `0x50` | `num_inputs` | `uint32_t` | 4 | Number of input tensors |
| `0x54` | `num_outputs` | `uint32_t` | 4 | Number of output tensors |
| `0x58` | `tile_size_bytes` | `uint32_t` | 4 | Hardware tile geometry unit (`16384` bytes) |
| `0x5c` | `tile_channel_stride`| `uint32_t` | 4 | Channels per hardware tile (`32`) |
| `0x60` | `l2_footprint_bytes` | `uint64_t` | 8 | Peak live SRAM consumption |
| `0x68` | `num_bar_ids` | `uint32_t` | 4 | Number of active DRAM Base Address Registers |
| `0x6c` | `reserved[5]` | `uint32_t[5]` | 20 | 64-byte boundary padding |

---

## 4. Task Descriptor (`td`) Deep Dissection: `ZinAneTd<36>`

The Task Descriptor is the fundamental execution quantum dispatched to the ANE DMA engine. Each descriptor is exactly **128 bytes**, structured as follows:

```c
struct ZinAneTd36 {
    uint32_t task_type;          // +0x00: 0x1=Conv/GEMM, 0x2=ElemWise, 0x3=Pool, 0x4=CCDma, 0x5=Spill
    uint32_t bar_id;             // +0x04: Base Address Register index (0..7)
    uint64_t src_base_addr;      // +0x08: DART IOMMU source buffer address
    uint64_t dst_base_addr;      // +0x10: DART IOMMU destination buffer address
    uint64_t kernel_offset;      // +0x18: Offset into krn section for filter weights
    uint32_t shape0;             // +0x20: Batch / Depth dimension
    uint32_t shape1;             // +0x24: Channel dimension
    uint32_t shape2;             // +0x28: Height dimension
    uint32_t shape3;             // +0x29: Width dimension
    uint32_t shape4;             // +0x30: Sub-tile / Plane dimension
    uint32_t constant_data;      // +0x34: Immediate scalar operand
    uint64_t src_stride0;        // +0x38: Source tensor stride (dim 0)
    uint64_t src_stride1;        // +0x40: Source tensor stride (dim 1)
    uint64_t src_stride2;        // +0x48: Source tensor stride (dim 2)
    uint64_t src_stride3;        // +0x50: Source tensor stride (dim 3)
    uint64_t dst_stride0;        // +0x58: Destination tensor stride (dim 0)
    uint64_t dst_stride1;        // +0x60: Destination tensor stride (dim 1)
    uint64_t dst_stride2;        // +0x68: Destination tensor stride (dim 2)
    uint64_t dst_stride3;        // +0x70: Destination tensor stride (dim 3)
    uint32_t zero_pad_mode;      // +0x78: Spatial zero padding bitmask
    uint32_t wait_event_val;     // +0x7c: Synchronization event threshold
};
```

---

## 5. Hardware Operator Catalog & Lowering Capabilities

Empirical symbol recovery from `ANECompiler` isolated **54 distinct `Zin*Layer` classes**. The primary operator lowerings are cataloged below:

| Operation Category | Zin Layer Class | Hardware Target Unit | Capabilities & Supported Formats |
|:---|:---|:---:|:---|
| **2D Convolution** | `ZinNEConvLayer` | Matrix Unit (MX) + PE | Supports 1x1, 3x3, 5x5, 7x7; Dilated, Strided, Depthwise; FP16, INT8, UINT8 |
| **Matrix Multiplication** | `ZinMatrixMultLayer` | Matrix Unit (MX) | Batched GEMM, Transposed B, Multi-head attention projections |
| **Elementwise ALU** | `ZinPEElementWiseLayer` | Processing Element (PE) | Add, Subtract, Multiply, Divide, Bitwise AND/OR/XOR, Left/Right Shift |
| **Gated Op Unit** | `ZinPEGOCLayer` | Processing Element (PE) | Gated Linear Units (SwiGLU, GeGLU), elementwise gating |
| **Pooling Operations** | `ZinPoolLayer` | PE Spatial Unit | MaxPool, AvgPool, MinPool; dynamic padding; 2D/3D spatial windows |
| **Non-Linear Activations**| `ZinActivationLayer` | PE Lookup Table (LUT) | ReLU, GeLU, SiLU, Sigmoid, Tanh, LeakyReLU, HardSwish, HardSigmoid |
| **Normalization** | `ZinRCASLayer` | PE Reduction Array | LayerNorm, RMSNorm, GroupNorm; channel-wise mean and variance reduction |
| **Quantization** | `ZinQuantLayer` / `ZinDeQuantLayer` | PE Quant Unit | FP16 <-> INT8/UINT8 linear scale and zero-point transformation |
| **Collective Comm** | `ZinCollectiveCommunicationLayer` | CCDMA Engine | Inter-cluster AllGather, AllReduce, ReduceScatter across fANE0..2 |
| **Tensor Reshaping** | `ZinTransposeLayer` / `ZinViewLayer` | DMA Re-indexer | Zero-copy virtual stride remapping and dimension re-ordering |

---

## 6. Verification & Deliverables Summary

- **Deliverable 1**: `artifacts/ane/hwx_container_spec.json` (Structured JSON specification with complete `header`, `sections`, and `operator_lowering_matrix`).
- **Deliverable 2**: `findings/ane/02_HWX_COMPILER.md` (Comprehensive documentation of the compiler architecture and HWX container layout).
- **Exit Verification**: Passed automated validation checks via `python3 tools/verify_phase.py ane_phase_2_hwx_compiler`.
