== Benchmarking Setup <benchmarking>

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
allows us to inspect how much of the final CNF is attributable specifically to the local or global
uniqueness mechanism.


=== Solver and Level Sets

All benchmark runs use the same SAT backend as the main solver implementation, namely `Minisat22`
through the PySAT interface. By default, the benchmarking script can evaluate the six hand-crafted
LLE levels listed in `levels.py`, each paired with a horizon known to be sufficient for solvability.
It can also benchmark custom levels constructed programmatically with `WorldBuilder`.

The experiment reported in Chapter 5 uses four representative levels: three synthetic instances of
increasing size and one original LLE level. This combination exposes both scaling behaviour and the
behaviour of the solver on a realistic cooperative puzzle.


=== Protocol

For each level and each movement formulation, the benchmark performs one profiled run to extract the
exact clause counts and the full constraint breakdown. It then repeats the same solver invocation
for 100 runs, each time on a fresh copy of the world, and reports the mean and standard deviation
of generation time and solve time. Using fresh world copies avoids benchmark contamination by
mutable environment state.

No timeout or parallel speedup is introduced in this protocol. The measurements should therefore be
read as direct comparisons between the two SAT formulations on the same machine, rather than as
hardware-independent absolute performance claims.


=== Outputs

The benchmarking pipeline produces a console summary table, a JSON file containing the raw
measurements, and a set of plots for clause counts, per-constraint clause breakdowns, and timing
statistics. Chapter 5 draws on these outputs to interpret the trade-off between the two movement
formulations.
