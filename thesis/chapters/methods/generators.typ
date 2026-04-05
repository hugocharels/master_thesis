== Level Generators <generators>

=== Design Pattern

All generators follow a common architecture built around three principles:

+ *SAT as oracle*: the solver is not post-hoc — it is embedded in the generation loop. A candidate
  level is only accepted if the solver confirms the desired property (solvability, cooperation).
+ *Separation of concerns*: level construction and property verification are decoupled. Generators
  build candidate levels using domain-specific heuristics; the solver decides acceptance.
+ *Extensibility*: every generator extends `BaseGenerator` and is registered via the
  `@register_generator` decorator, making it available to the CLI without modifying core code.

#lorem(3) // TODO: add small code/pseudocode snippet showing the generator loop pattern


=== Random Solvable Generator

The simplest generator. It samples a level uniformly at random (wall placement, laser sources,
agent starts and exits), then queries the SAT solver. If SAT, the level is accepted; otherwise a
new sample is drawn. The process repeats until a solvable level is found or a budget is exhausted.

// Parameters: grid size (H x W), number of agents, wall density, laser count, time horizon T_max
// Strength: simple, unbiased distribution over solvable levels
// Weakness: low acceptance rate for large grids or many agents — most random levels are unsolvable

#lorem(3) // TODO: write full description


=== Constrained Random Solvable Generator

A structured variant that biases generation toward solvable configurations by construction, while
still using the solver to verify. Constraints applied during sampling include:

- Ensuring exits are reachable from starting positions (connectivity check before SAT call).
- Limiting wall density to preserve navigable space.
- Placing laser sources only where beams have non-trivial reach.

This reduces the rejection rate compared to the fully random generator while preserving diversity.

#lorem(3) // TODO: write full description and detail which constraints are applied


=== Random Cooperative Generator

Extends the random solvable generator with a second SAT call (strict solver). A level is accepted
only if it is solvable (standard SAT) and requires cooperation (strict UNSAT). As established in
<cooperation-detection>, this guarantees that every accepted level structurally requires inter-agent
coordination.

// Acceptance condition: standard SAT ∧ strict UNSAT
// Inherits the low acceptance rate issue of the random solvable generator, amplified

#lorem(3) // TODO: write full description


=== Constrained Random Cooperative Generator

Combines the structural biases of the constrained solvable generator with the cooperation
acceptance condition. Additionally applies heuristics that increase the probability of generating
levels with cooperative structure:

- Placing laser sources such that beams cross agent paths.
- Ensuring that at least one agent's exit is behind a laser of a different color.

These heuristics increase the cooperation acceptance rate without sacrificing formal correctness:
the solver remains the final arbiter.

#lorem(3) // TODO: write full description and detail heuristics


=== Summary

#figure(
  // TODO: replace with actual table
  table(
    columns: 3,
    stroke: black,
    inset: 8pt,
    align: horizon,
    table.header([*Generator*], [*Solvable*], [*Cooperative*]),
    [Random Solvable], [✓ (SAT check)], [✗],
    [Constrained Random Solvable], [✓ (SAT check)], [✗],
    [Random Cooperative], [✓ (SAT check)], [✓ (strict UNSAT)],
    [Constrained Random Cooperative], [✓ (SAT check)], [✓ (strict UNSAT)],
  ),
  caption: [Overview of the four generators and their guaranteed properties.],
)
