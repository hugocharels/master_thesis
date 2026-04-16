== Modeled Subset of the Laser Learning Environment

This thesis does not reason about the full Laser Learning Environment (LLE) implementation. Instead,
it studies the smallest subset of mechanics needed to state and certify the target properties of
solvability and cooperation.

An instance is modeled as a rectangular grid containing wall tiles, agent start positions, exit
tiles, and coloured laser sources. Each source emits a beam in a fixed cardinal direction. Beams
are blocked by walls and, under the standard semantics, by an agent of the matching colour. Agents
of other colours may not occupy cells traversed by an active beam. The level is solved when all
exit tiles are occupied simultaneously.

This restricted model is deliberate. The aim of the thesis is not to reproduce the whole benchmark
engine, but to isolate the part of the dynamics that creates the blocking-based inter-agent
dependencies highlighted in the LLE paper @LLE. In particular, the solver developed here focuses on
whether a joint trajectory exists and whether that trajectory must rely on same-colour
beam-truncation.

The full LLE environment contains additional mechanics, notably gems and void tiles. They are not
included in the present formal model because they are not needed to decide the bounded-horizon
properties studied in this thesis. When constructing levels for the current solver, void tiles can
be conservatively treated as walls, while gem collection is omitted entirely. These omissions narrow
the scope of the formal claims and should therefore be read as modeling assumptions, not as claims
about the full benchmark.
