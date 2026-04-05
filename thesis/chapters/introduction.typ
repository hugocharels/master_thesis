== Context

#lorem(10) // TODO: write context — MARL as a field, cooperative agents, why environment design matters for learning quality

// Key points to cover:
// - RL → MARL, what changes with multiple agents
// - Cooperative MARL: agents share a goal, must coordinate
// - Training quality depends heavily on the environment: too easy = no learning, unsolvable = no learning
// - Procedural generation as a way to supply diverse, controlled environments


== Motivation

#lorem(10) // TODO: write motivation

// Key points to cover:
// - Manual level design is expensive, limited in diversity
// - Solvability in multi-agent settings is non-trivial: not just "is there a path" but "is there a joint action sequence"
// - Cooperation must be structurally enforced: a level that can be solved by one agent alone teaches nothing about coordination
// - SAT as a tool: encode solvability as a formal property, verify it exactly, build generators on top


== Problem Statement

// Three properties we target:
// 1. Solvability — the level admits at least one valid joint action sequence
// 2. Cooperation requirement — solving the level requires inter-agent coordination (cannot be solved independently)
// 3. Learnability — the solution is discoverable by MARL algorithms (open problem, not fully addressed here)

#lorem(10) // TODO: write problem statement


== Contributions

// What this thesis delivers:
// - A SAT-based solver that decides solvability of LLE levels
// - A cooperation detector based on a strict laser variant
// - A family of procedural generators: random solvable, constrained solvable, random cooperative, constrained cooperative
// - Benchmarks evaluating solver performance and generator quality
//
// Generalizability: the approach — reduce solvability/cooperation to a formal property, verify it exactly,
// build generators around the verifier — is applicable to other MARL environments. However, the SAT encoding
// is specific to LLE (laser mechanics, color matching, etc.) and would need to be redesigned for a different
// environment. The method is a blueprint, not a plug-and-play tool.

#lorem(10) // TODO: write contributions


== Thesis Structure

// One paragraph per chapter:
// Chapter 2 — Background: MARL, LLE, PCG, SAT
// Chapter 3 — Related Work: PCG for games, solvability-aware generation, PCG for MARL
// Chapter 4 — Methods: formalization, SAT encoding, cooperation detection, generators, benchmarking setup
// Chapter 5 — Experiments: results
// Chapter 6 — Conclusion: summary, limitations, future work

#lorem(10) // TODO: write structure overview
