== Benchmarking Setup <benchmarking>

// TODO: define once metrics are decided
// Tentative metrics to evaluate:
// - Solver performance: solve time vs. grid size, number of agents, T_max
// - Generator acceptance rate: fraction of candidates accepted per generator type
// - Cooperation rate: fraction of solvable levels that require cooperation (random baseline)
// - Level diversity: structural diversity of accepted levels (wall layout, laser placement)
// - Scalability: how solver time scales with level size

// Experimental protocol:
// - Fix grid sizes (e.g., 5x5, 6x6, 8x8), number of agents (2, 3, 4)
// - Run each generator N times, record acceptance rate, solve time, cooperation rate
// - Compare constrained vs. unconstrained generators on acceptance rate
// - Profile solver: measure CNF size (variables, clauses) vs. level parameters

#lorem(3) // TODO: fill in once metrics and protocol are finalized
