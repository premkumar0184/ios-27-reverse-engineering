# Agent Prompt: Phase 8 - Knowledge Graph Synthesizer & Master Architectural Dossier

## Mission
Execute **Phase 8: Cross-Component Knowledge Graph Synthesis & Master Architectural Dossier**.
Unify all extracted artifacts, findings documents, symbol cross-references, UI event flows, and security trust relationships into a coherent knowledge graph using `/graphify`. Deliver the final master reverse engineering dossier.

## Required Deliverables
1. `graphify-out/graph.json` & `graphify-out/GRAPH_REPORT.md`:
   - Persistent knowledge graph indexing all components, IPC channels, UI controllers, and trust boundaries.
2. `findings/08_SYNTHESIS_AND_GRAPH.md`:
   - Master technical synthesis report synthesizing the complete iOS 27 architecture.
   - Comprehensive Mermaid diagrams showing boot flow, SPTM/TXM execution levels, kernel architecture, coprocessor interactions, and SpringBoard UI event routing.

## Available Tools & Procedures
1. Run `/graphify . --no-viz` (or via Python graphify pipeline) across `findings/`, `artifacts/`, and documentation.
2. Validate graph queries using `graphify query` and `graphify path` to ensure all key architectural relationships are navigable.
3. Verify results with `python3 tools/verify_phase.py phase_08_graphify_synthesis`.
