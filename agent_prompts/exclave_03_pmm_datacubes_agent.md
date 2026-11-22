# Agent Prompt: ExclaveOS RE Phase 3 — Memory Subsystem, Datacubes & Shared Memory Architecture

## Objective
Reverse engineer the memory management architecture of ExclaveOS, focusing on the **Datacube** retyping protocol between XNU and ExclaveOS, PMM (Physical Memory Manager) allocation bitmaps, MTE (Memory Tagging Extension) frames, and Jungle (`jg_sharedmem`) shared memory segments.

## Target Binaries
- `artifacts/firmware/exclavecore_bundle_unpacked/01_pmm_server.macho`
- `artifacts/firmware/exclavecore_bundle_unpacked/03_jg_sharedmem_preload.macho`
- `kernelcache.release.raw` (PMM driver bridges)

## Target Deliverables
1. `artifacts/exclave/datacube_memory_spec.json`:
   - Datacube abstraction: Structure, state transitions, page donation, and retyping protocol (`Release Datacube` / `Releasing Datacube`).
   - PMM allocator: Bitmap indexing, bundle metadata, early sync allocation (`xrt__sync_pmm_early_alloc`).
   - MTE frame management: `__PMM_EXTRA_FRAMES`, `__PMM_EXTRA_MTE_FRAMES`.
2. `artifacts/exclave/jg_sharedmem_spec.json`:
   - Jungle shared memory layout: `JgSharedMemoryComponent.ExclavesSegment` attributes (nPages, shmemGroup, backingModel, shmemID).
   - `JgEXSurfaceRootComponent` and hardware acceleration bridges (e.g. ANE ExclaveKit clients).
   - XnuSharedSegment permissions and sync primitives.
3. `findings/exclave/03_DATACUBES_AND_MEMORY.md`:
   - Deep structural report on Datacube memory retyping, PMM physical allocation, and Jungle shared memory.

## Verification Gate
```bash
python3 tools/verify_phase.py exclave_phase_3_pmm_datacubes
```
