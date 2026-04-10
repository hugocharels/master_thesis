== Level Generators <generators>

=== Design Pattern

All generators follow a common architecture built around three principles:

+ *SAT as oracle*: the solver is not post-hoc; it is embedded in the generation loop. A candidate
  level is only accepted if the solver confirms the desired property (solvability, cooperation).
+ *Separation of concerns*: level construction and property verification are decoupled. Generators
  build candidate levels using domain-specific heuristics; the solver decides acceptance.
+ *Extensibility*: every generator extends `BaseGenerator` and is registered via the
  `@register_generator` decorator, making it available to the CLI without modifying core code.

#lorem(2) // TODO: add small code or pseudocode snippet showing the generator loop pattern


=== Generation Targets

Viewed through the solvability and cooperation definitions of <formalization>, the generator family
targets the three level categories shown in Figure @fig-generator-categories. Solvable generators
accept levels in categories (b) and (c), cooperative generators accept only levels in category (c),
and unsolvable levels in category (a) are always rejected.

#figure(
  grid(
    columns: 3,
    gutter: 10pt,
    align: center,
    [*(a)* Unsolvable \ _rejected by all generators_],
    [*(b)* Solvable, no cooperation \ _accepted only by solvable generators_],
    [*(c)* Solvable and cooperative \ _target of cooperative generators_],

    image("../../../assets/unsolvable_map_example.png", width: 100%),
    image("../../../assets/bad_map_example.png", width: 100%),
    image("../../../assets/good_map_example.png", width: 100%),
  ),
  caption: [Target level categories for the generator family.],
) <fig-generator-categories>


=== Random Solvable Generator

The simplest generator. It samples a level uniformly at random (wall placement, laser sources,
agent starts and exits), then queries the SAT solver. If SAT, the level is accepted; otherwise a
new sample is drawn. The process repeats until a solvable level is found or a budget is exhausted.

// Parameters: grid size (H x W), number of agents, wall density, laser count, time horizon T_max
// Strength: simple, unbiased distribution over solvable levels
// Weakness: low acceptance rate for large grids or many agents; most random levels are unsolvable

#lorem(2) // TODO: write full description


=== Constrained Random Solvable Generator

A structured variant that biases generation toward solvable configurations by construction, while
still using the solver to verify. Constraints applied during sampling include:

- Ensuring exits are reachable from starting positions.
- Limiting wall density to preserve navigable space.
- Placing laser sources only where beams have non-trivial reach.

This reduces the rejection rate compared to the fully random generator while preserving diversity.

#lorem(2) // TODO: write full description and detail which constraints are applied


=== Random Cooperative Generator

Extends the random solvable generator with a second SAT call based on the strict semantics. A level
is accepted only if it is solvable under the standard encoding and requires cooperation under the
criterion of <cooperation-detection>. This guarantees that every accepted level structurally
requires inter-agent coordination.

The current implementation augments this binary acceptance rule with a *cooperation profile
analyzer*. The binary detector remains the formal guarantee used throughout the thesis: a level is
cooperative if and only if it is satisfiable under the standard semantics and unsatisfiable under
the strict semantics. The analyzer adds a second layer whose purpose is to distinguish *which kind*
of cooperation the accepted level exhibits.

Given a cooperative level, we first extract a valid joint plan from the standard SAT model. We then
run selective counterfactual checks in which one agent at a time loses the ability to block beams
of its own colour. If the level becomes unsatisfiable under that selective restriction, the agent is
identified as a necessary helper. By combining these counterfactual checks with the helping actions
observed in the extracted plan, we build a directed dependency graph between agents.

This dependency graph is used as a generation target. In the present implementation, the generator
can recognise and filter levels according to the following profile families:

- *independent*: no cooperation is required;
- *asymmetric*: at least one one-way helping relation is present;
- *mutual*: two agents depend on each other;
- *distributed*: one agent depends on multiple distinct helpers;
- *fully coupled*: all agents belong to a single strongly connected dependency component.

The important methodological point is that profile control is layered on top of the existing formal
machinery. The SAT encodings still certify solvability and binary cooperation. The profile analyzer
uses those certified levels as input and acts as a classification and filtering layer for the
generator.


=== Constrained Random Cooperative Generator

Combines the structural biases of the constrained solvable generator with the cooperation
acceptance condition. Additionally applies heuristics that increase the probability of generating
levels with cooperative structure:

- Placing laser sources such that beams cross agent paths.
- Biasing candidate layouts toward configurations where helper positions can affect teammates.

These heuristics increase the cooperation acceptance rate without sacrificing formal correctness:
the solver remains the final arbiter.

#lorem(2) // TODO: write full description and detail heuristics


=== Summary

#figure(
  table(
    columns: 3,
    stroke: black,
    inset: 8pt,
    align: horizon,
    table.header([*Generator*], [*Solvable*], [*Cooperative*]),
    [Random Solvable], [Yes (SAT check)], [No],
    [Constrained Random Solvable], [Yes (SAT check)], [No],
    [Random Cooperative], [Yes (SAT check)], [Yes (strict UNSAT)],
    [Constrained Random Cooperative], [Yes (SAT check)], [Yes (strict UNSAT)],
  ),
  caption: [Overview of the four generators and their guaranteed properties.],
)
