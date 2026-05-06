== The Laser Learning Environment <lle-background>

The Laser Learning Environment (LLE) @LLE is a grid-based cooperative multi-agent benchmark
designed to study coordination-critical tasks. A level consists of a rectangular grid containing
walls, coloured laser sources, agent start positions, and exit tiles. Each agent is assigned a
colour and must reach its designated exit tile.

The central mechanic is the laser beam. Each source emits a directional beam that propagates
cell by cell until it reaches a wall or the grid boundary. An agent whose colour matches the
beam is _immune_ to it: it may occupy a cell the beam traverses without being harmed, but its
physical presence truncates the beam at that cell. Agents of other colours cannot occupy a
cell crossed by an active beam.

This truncation is the source of the cooperative structure studied in this thesis. By occupying
a position along its own beam, an agent shortens the beam and opens cells beyond it for
teammates who are not immune to that colour. Crucially, this action is locally unrewarded: the
helper agent receives no direct benefit from blocking its own beam. The reward is issued only
when all agents simultaneously occupy their exits, which requires the full team to coordinate
successfully.

#figure(
  image("../../../assets/lvl6-annotated.png", width: 70%),
  caption: [
    An annotated LLE level. Coloured agents must reach their matching exit tiles. Laser beams
    block movement for non-immune agents; an immune agent can truncate its own beam by occupying
    a cell along its path, opening a route for a teammate.
  ],
)

A complete description of the benchmark, its difficulty properties, and its relation to existing
MARL methods is given in Chapter 2. The present chapter focuses on the formal model used to
reason about solvability and cooperation within a bounded time horizon.


== Boolean Satisfiability <sat-background>

Boolean Satisfiability (SAT) is the problem of deciding whether a propositional formula has a
satisfying assignment — a mapping from Boolean variables to true or false that makes the formula
evaluate to true. It is the canonical NP-complete decision problem @Cook1971.

In practice, SAT solvers operate on formulas in _Conjunctive Normal Form_ (CNF). A CNF formula
is a conjunction of _clauses_, where each clause is a disjunction of _literals_ and a literal is
either a variable $x$ or its negation $not x$. For example:

$
  (x_1 or not x_2) and (not x_1 or x_3) and (x_2 or x_3)
$

is a CNF formula over three variables. It is satisfied by setting $x_1 = "true"$, $x_2 = "false"$,
$x_3 = "true"$, among other assignments.

Modern SAT solvers based on the DPLL procedure and Conflict-Driven Clause Learning (CDCL) can
handle industrial instances with millions of variables and clauses @Davis1962. Given a CNF
formula, a solver either:

- returns a _satisfying assignment_ that witnesses the formula is satisfiable (SAT), or
- certifies that _no_ satisfying assignment exists (UNSAT).

The UNSAT certificate is as informative as the SAT witness: it proves the non-existence of a
solution. This property is central to the cooperation detection mechanism developed in
@cooperation-detection, where UNSAT under a modified encoding is used to certify that no
solution exists without the cooperative interaction.

In this thesis, propositional variables are introduced to represent agent positions, laser beam
states, and laser activity at each time step. The constraints of the bounded-horizon solvability
problem are then encoded as CNF clauses, and a SAT solver is used as a decision oracle. The
solver used throughout is Minisat22, accessed through the PySAT interface @Ignatiev2018.
