# iOS 27 ExclaveOS RE — Phase 1A: Workspace Baseline & BUND Container Dissection

## 1. Executive Summary

This investigation establishes the empirical baseline for reverse engineering **ExclaveOS and the Tightbeam IPC Protocol** in iOS 27.2 (`24B119`) on Apple Silicon A19 Pro (`t8150`). ExclaveOS is Apple's isolated microkernel execution world, running in dedicated SPTM hardware domains outside the monolithic XNU kernel to provide capability-isolated enclaves (conclaves) for ambient sensor processing, biometric validation, and secure trust services.

The primary artifacts reverse engineered in this phase are:
1. **The Decrypted ExclaveOS APFS Root Image**: `artifacts/crypto/141-08904-238_exclaveos.dmg` (602 MiB, APFS volume `RaveB24B119.V57ExclaveOS`).
2. **The ExclaveCore BUND Container**: `iPhone18,3_27.2_24B119_Restore/Firmware/image4/exclavecore_bundle.t8150.RELEASE.im4p` (31,719,658 bytes, `DNUB` magic).
3. **The Four Core Microkernel Mach-Os**: Unpacked in `artifacts/firmware/exclavecore_bundle_unpacked/`.

---

## 2. Apple BUND (DNUB) Container Architecture

The `exclavecore_bundle` payload encapsulates the microkernel, platform runtime, and trust services into a specialized multi-binary archive headed by the `DNUB` (`0x444e5542`, ASCII `BUND` in little-endian) container header:

```
+-----------------------------------------------------------------------------+
|                      APPLE BUND (DNUB) ARCHIVE FORMAT                       |
+-----------------------------------------------------------------------------+
| 0x00000000: IM4P ASN.1 DER Envelope (Tag 0x16: "excl")                     |
| 0x00000023: DNUB Header Magic (0x444e5542)                                 |
|             - Version: 0x00040000 (v4.0 ExclaveCore)                        |
|             - Number of Section Entries: 10 (0x0000000a)                    |
|             - Table of Contents Offset: +636 bytes relative to DNUB         |
+-----------------------------------------------------------------------------+
| +636 Bytes: Table of Contents (10 x 24-byte Descriptors)                    |
|             - 4-Byte Little-Endian FourCC Tag                               |
|             - 8-Byte Offset (uint64_t)                                      |
|             - 8-Byte Section Size (uint64_t)                                |
|             - 4-Byte Flags (uint32_t)                                       |
+-----------------------------------------------------------------------------+
| +0x18000  : Section Payloads (ktxt, rtxt, utxt, kdat, rdat, udat, knlr, tsru)|
+-----------------------------------------------------------------------------+
```

### 2.1 Dissected FourCC Table of Contents

| Entry | Raw Tag | FourCC | Offset | Size (Bytes) | Flags | Functional Role |
|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 0 | `txtk` | `ktxt` | `0x00018000` | 6,897,664 (`0x694000`) | `0x000a` | Microkernel Code (Tightbeam Runtime Text) |
| 1 | `txtr` | `rtxt` | `0x006ac000` | 20,545,536 (`0x1398000`)| `0x000e` | Runtime Platform Code (VASCore Platform Text) |
| 2 | `txtu` | `utxt` | `0x01a44000` | 131,072 (`0x020000`)   | `0x0011` | Userland Conclave Code (Jungle Preload Text) |
| 3 | `tadk` | `kdat` | `0x01a64000` | 294,912 (`0x048000`)   | `0x0011` | Microkernel Static Data (Tightbeam Runtime Data)|
| 4 | `tadr` | `rdat` | `0x01aac000` | 1,654,784 (`0x194000`) | `0x0015` | Runtime Platform Static Data (VASCore Data) |
| 5 | `tadu` | `udat` | `0x01c40000` | 81,920 (`0x014000`)    | `0x0011` | Userland Conclave Static Data (Jungle Data) |
| 6 | `knlr` | `rlnk` | `0x01c54000` | 229,376 (`0x038000`)   | `0x0015` | cL4 Microkernel Core (Bootstrap & Scheduler) |
| 7 | `knlu` | `ulnk` | `0x01c8c000` | 49,152 (`0x00c000`)    | `0x0015` | cL4 Userland / Syscall Unit Interface |
| 8 | `tsru` | `urst` | `0x01c98000` | 1,736,704 (`0x1a8000`) | `0x0015` | Trust Services Runtime Unit (Audio / Sensor HAL)|
| 9 | `ldbu` | `ubdl` | `0x00000000` | 0 (`0x000000`)         | `0x0000` | Bundle Loader Header Descriptor |

Notice the contiguous allocation:
$$	ext{End}(txtk) = 0x18000 + 0x694000 = 0x6ac000 = 	ext{Start}(txtr)$$
$$	ext{End}(txtr) = 0x6ac000 + 0x1398000 = 0x1a44000 = 	ext{Start}(txtu)$$
$$	ext{End}(tsru) = 0x1c98000 + 0x1a8000 = 0x1e40000 = 31,719,424	ext{ bytes}$$

---

## 3. Microkernel Binaries Catalog

The core microkernel binaries unpacked from `exclavecore_bundle` comprise:

1. **`00_tightbeam_runtime.macho`** (7,268,976 bytes):
   - **Language**: Swift 5 + cL4 C Transports.
   - **Sections**: `__DATA.__ENDPOINTS` (`0xc06d7a78`), `__DATA.__DEVICETREE` (`0xc06d84be`), Swift metadata (`__TEXT.__swift5_*`).
   - **Role**: Tightbeam RPC router, message accumulator, endpoint dispatcher, and cL4 register/shared-memory IPC engine.

2. **`01_pmm_server.macho`** (579,904 bytes):
   - **Language**: C / Assembly (cL4 Native Service).
   - **Role**: Physical Memory Manager (PMM). Enforces client memory budgets, allocates page frames, retypes memory pages via Datacubes (`Release Datacube`), and mints cL4 endpoint capabilities (`L4_Cap_Mint_Ep`).

3. **`02_vascore_platform.macho`** (21,880,432 bytes):
   - **Language**: C / Assembly.
   - **Role**: Virtual Address Space (VAS) manager and Exclave Runtime (`xrt`) concurrency manager (`sync_space_init`, `vas_root_cap_copy`, `vas_slot_alloc`).

4. **`03_jg_sharedmem_preload.macho`** (131,072 bytes):
   - **Language**: Swift 5.
   - **Role**: Jungle Shared Memory coordinator (`JgSharedMemoryComponent.ExclavesSegment`, `JgEXSurfaceRootComponent`, `JgXnuProxyComponents`).

5. **`knlr` / `rlnk`** (229,376 bytes):
   - **Role**: Foundational cL4 microkernel scheduler and CPU core bootstrap (`_thread_enter_scheduler_hook`, `_xrt__platform_init_stack`).

6. **`tsru` / `urst`** (1,736,704 bytes):
   - **Role**: Trust Services Runtime Unit hosting sensor isolation HALs (`sharedmem_audio_SoundAnalysisHALEKOutput`).

---

## 4. ExclaveKit dyld Shared Cache Baseline

Inside `141-08904-238_exclaveos.dmg`, ExclaveKit maintains its own dedicated dyld shared cache:
- **Cache Path**: `System/ExclaveKit/System/Library/dyld/dyld_shared_cache_arm64e` (189,710,336 bytes).
- **Symbol Cache**: `System/ExclaveKit/System/Library/dyld/dyld_shared_cache_arm64e.symbols` (56,360,960 bytes).
- **Dynamic Linker**: `System/ExclaveKit/usr/lib/dyld` (906,128 bytes).
- **Core Framework**: `System/ExclaveKit/System/Library/PrivateFrameworks/Tightbeam.framework`.
- **Client Stub**: `System/ExclaveKit/usr/bin/tightbeam_stub` (51,744 bytes).

This confirms that ExclaveOS conclaves run standard ARM64E Mach-O binaries dynamically linked against ExclaveKit's private shared cache, communicating across enclave boundaries exclusively via Tightbeam and cL4 capabilities.
