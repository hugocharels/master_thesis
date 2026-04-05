== Multi-Agent Reinforcement Learning

#lorem(10) // TODO: write MARL background

// Key points:
// - Single-agent RL recap: MDP, policy, reward, value function
// - Extension to MARL: multiple agents, joint action space, partial observability
// - Cooperative MARL: shared reward, agents must coordinate to maximize it
// - Challenges: non-stationarity, credit assignment, sparse rewards, exploration
// - Why sparse rewards are especially hard: agents must discover long cooperative sequences
//   with no intermediate feedback (connect to LLE's zero-incentive bottlenecks)


== The Laser Learning Environment

// Full description of LLE:
// - 2D grid: H x W, positions (x,y)
// - Agents: 1–4, each has a color, starts at a designated cell, must reach a colored exit
// - Walls: block movement and laser beams
// - Lasers: each laser source has a color and direction, beam propagates until blocked
// - Color-matching mechanic: an agent can only block a laser of its own color
//   (agents of other colors are killed by it)
// - Exit condition: ALL agents must reach their exits simultaneously
// - Zero-incentive bottlenecks: no reward for blocking a laser for a teammate
// - Why it's hard: perfect coordination required, no local reward signal to guide agents
// - Mention it is one instance of a broader class of grid-based cooperative MARL environments

#lorem(10) // TODO: write LLE section — include a figure

// Figure: annotated LLE level showing agents, lasers, exits, walls


== Procedural Content Generation

// Brief overview — enough to situate the SAT-based approach:
// - PCG: algorithmic creation of game content (levels, maps, textures)
// - Main paradigms:
//   * Constructive methods (grammars, noise, cellular automata): fast, no guarantee
//   * Search-based methods (evolutionary, MCTS): flexible, expensive
//   * Constraint-based methods (CSP, SAT): formal guarantees, potentially slower
// - For this thesis: constraint-based (SAT). Other paradigms mentioned for context only.
// - Note: noise-based and CA methods explored in preparatory work but not used here

#lorem(10) // TODO: write PCG overview


== Boolean Satisfiability

// SAT basics:
// - Boolean formula in CNF: conjunction of clauses, each clause a disjunction of literals
// - SAT problem: does there exist an assignment of variables satisfying all clauses?
// - DPLL algorithm: backtracking search with unit propagation
// - CDCL: modern extension — clause learning, non-chronological backtracking
// - Modern solvers (MiniSat, etc.) handle millions of variables in practice

// Complexity:
// - SAT is NP-complete (Cook-Levin theorem, 1971)
// - Despite worst-case exponential, CDCL solvers are highly effective in practice

// Connection to LLE:
// - LLE solvability is in NP: given a joint action sequence, verifying it is correct
//   takes polynomial time (simulate the execution, check all agents reach exits)
// - Our reduction is polynomial-time: LLE ≤_p SAT
//   → LLE solvability is at most as hard as SAT
// - Whether LLE is NP-hard (i.e., NP-complete) is an open question:
//   it would require a polynomial reduction from an NP-hard problem to LLE
// - Practical implication: even if LLE is NP-hard, modern CDCL solvers handle
//   these instances well — justifying the SAT-based approach

#lorem(10) // TODO: write SAT section
