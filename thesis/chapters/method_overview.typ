== Overview <method-overview>

This chapter develops the formal foundation of the thesis. The goal is to move from the informal
description of a multi-agent puzzle environment to a pair of decidable decision problems, and then
to show that both problems admit polynomial-time reductions to Boolean Satisfiability.

The method is presented in four stages. The present section fixes the environment model and states
the properties to be certified. The following section (@formalization) defines the semantic objects
— positions, trajectories, beam dynamics, and the two decision problems — with full mathematical
precision. The SAT reduction (@sat-reduction) then encodes those semantic objects as propositional
variables and derives the CNF formula whose satisfiability is equivalent to level solvability. The
evaluation protocol (@benchmarking) closes the chapter by describing the experimental protocol used
to compare two alternative movement encodings.


=== Environment Model

We study a restricted class of grid-based cooperative environments. An instance consists of a
rectangular grid of cells, a finite set of agents, a finite set of coloured laser sources, and a
set of exit tiles. Each agent is assigned a starting cell, a designated exit cell, and a colour
that determines which lasers it is immune to.

Laser sources emit directional beams. Each beam propagates cell by cell from its source in a fixed
cardinal direction until it reaches a wall or the grid boundary. An agent whose colour matches a
beam's colour is _immune_ to that beam and may occupy a cell it traverses. Agents of other colours
may not occupy a cell while an active beam of a different colour crosses it.

The key interaction that motivates the thesis is _same-colour blocking_: because an immune agent
physically occupies a cell along its own beam's path, the beam is truncated at that cell under the
standard semantics, leaving the cells beyond it free. This creates an indirect benefit for
teammates: an agent can "block" its own beam to open a path for another agent who is not immune to
that colour. The thesis formalises this mechanism and uses it as the definition of cooperation.

The environment subset modeled here excludes gem tiles and void tiles, which appear in the
benchmark implementation but are not needed to define the two decision problems. Void tiles can be
treated conservatively as walls; gem collection is omitted. These omissions narrow the formal
scope and should be read as modeling assumptions rather than claims about the full benchmark.


=== Two Certified Properties

This thesis certifies two properties for every generated level.

*Solvability.* A level is _solvable_ with horizon $T_"max"$ if there exists a valid joint
trajectory of at most $T_"max"$ steps such that all agents simultaneously occupy their exit tiles
at the final step. Solvability is a correctness requirement: an unsolvable level provides no valid
training signal.

*Cooperation requirement.* A level _requires cooperation_ with horizon $T_"max"$ if it is solvable
under the standard beam semantics and _not_ solvable under the strict beam semantics, in which
same-colour blocking is disabled. A level that satisfies both conditions structurally forces agents
to rely on the blocking interaction. Cooperation is not a stylistic choice about level layout; it
is a formally decidable property that separates levels where agents must coordinate from levels
where they can succeed independently.

Both properties are stated relative to a fixed finite horizon. This is not a limitation but a
modeling choice: the SAT encoding operates over a bounded time window, and the formal claims are
horizon-relative by construction.


=== Reduction to SAT

Both decision problems are encoded as conjunctive normal form (CNF) formulas over propositional
variables indexed by agent, position, and timestep. Satisfiability of the formula is equivalent to
existence of a valid trajectory; unsatisfiability certifies absence of any such trajectory within
the horizon.

The reduction for solvability is described in @sat-reduction. The reduction for cooperation
requirement reuses the same formula with one change: the beam-propagation clauses are replaced by
strict variants that remove the blocking interaction. Running two SAT calls on the same level —
one with the standard formula and one with the strict formula — therefore decides both properties
in a single generation pass.

This coupling of two SAT calls is the core of the cooperation detector described later in
@cooperation-detection. From an engineering perspective, both calls share the same clause-building
infrastructure and differ only in a small family of laser propagation clauses.


=== Generator Architecture

Generators use the decision procedures as _acceptance oracles_. The generation loop repeatedly
samples or constructs a candidate level layout, then submits it to the solver. A candidate is
accepted only if the solver certifies the desired property (solvability, cooperation, or a specific
cooperation profile). Rejected candidates are discarded.

This architecture separates two concerns. _Level construction_ is handled by domain-specific
heuristics: uniform random sampling, geometric rejection filters, or lane-reservation patterns that
bias sampling toward solvable or cooperative layouts. _Property verification_ is handled
exclusively by the SAT solver. The solver is not approximate and does not rely on heuristic
estimates; it returns a formal certificate for every accepted level.

The generator family and the cooperation profile layer built on top of this architecture are
described in @generators. The present chapter focuses on the solver side: the formal model, the
reduction, and the empirical comparison of two alternative movement encodings.


=== Modeled Subset of the Laser Learning Environment

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
dependencies highlighted in the LLE paper @LLE. More specifically, the solver developed here asks
whether a valid joint trajectory exists within a bounded horizon and whether that trajectory must
rely on same-colour beam-truncation.

The full LLE environment contains additional mechanics, notably gems and void tiles. They are not
included in the present formal model because they are not needed to decide the bounded-horizon
properties studied in this thesis. When constructing levels for the current solver, void tiles can
be conservatively treated as walls, while gem collection is omitted entirely. These omissions narrow
the scope of the formal claims and should therefore be read as modeling assumptions, not as claims
about the full benchmark dynamics.
