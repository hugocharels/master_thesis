== Evaluation protocol <benchmarking>

The first benchmark implemented in this project isolates the SAT solver rather than the generators.
Its goal is to compare the two movement formulations used in the encoding: the *local* formulation,
which combines neighbourhood-based exclusivity with backward consistency, and the *global*
formulation, which enforces uniqueness by pairwise exclusion over the whole grid.

=== Metrics

For each run, the benchmarking code records:

- the total number of clauses in the generated CNF;
- the clause count contributed by each major constraint family;
- the CNF generation time;
- the SAT solving time;
- the total time obtained by summing generation and solving.

The implementation also stores per-constraint method profiles for the movement constraint, which
allows us to inspect the part of the final CNF generated inside the movement-constraint module.


=== Solver and level sets

All benchmark runs use the same SAT backend as the main solver implementation, namely `Minisat22`,
a descendant of the MiniSat solver of Eén and Sörensson @EenSorensson2003, accessed through the
PySAT interface @Ignatiev2018. The benchmarking script can evaluate the six hand-crafted benchmark
levels distributed with the environment, each paired with a horizon known to be sufficient for
solvability. It can also benchmark custom levels constructed programmatically.

The SAT encoding comparison reported in the following sections uses four representative levels:
three synthetic instances of increasing size and one hand-crafted LLE benchmark level (Level 6).
This combination exposes both scaling
behaviour and the behaviour of the solver on a realistic cooperative puzzle.


=== Protocol

For each level and each movement formulation, the benchmark performs one profiled run to extract the
exact clause counts and the full constraint breakdown. It then repeats the same solver invocation
for 100 runs, reporting the mean and standard deviation of generation and solve time. Each run
starts from a freshly built world in its initial state, so the 100 repetitions are independent and
none is affected by state a previous run may have left in the mutable `lle.World` object.

No timeout or parallel speedup is introduced in this protocol. The measurements should therefore be
read as direct comparisons between the two SAT formulations on the same machine, rather than as
hardware-independent absolute performance claims. The clause counts and timing statistics recorded
here are the basis for the results reported in the following sections.
