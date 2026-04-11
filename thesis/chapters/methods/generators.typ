== Level Generators <generators>

=== Design Pattern

All generators follow a common architecture built around three principles:

+ *SAT as oracle*: the solver is not post-hoc; it is embedded in the generation loop. A candidate
  level is accepted only if the solver confirms the desired property (solvability, cooperation).
+ *Separation of concerns*: level construction and property verification are decoupled. Generators
  build candidate levels using domain-specific heuristics; the solver decides acceptance.
+ *Extensibility*: every generator extends `BaseGenerator` and is registered via the
  `@register_generator` decorator, making it available to the CLI without modifying core code.

In implementation terms, each generator repeatedly performs the following loop: sample or
construct a candidate layout, reject it if it violates generator-specific structural constraints,
build an `lle.World`, and finally run the appropriate SAT-based acceptance test. Solvable
generators stop after the first candidate certified satisfiable within the target horizon, while
cooperative generators add the strict-semantics counterfactual test and, optionally, a
cooperation-profile filter.


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

The random solvable generator is the baseline member of the family. It samples pairwise-distinct
positions for agent starts, exits, walls, and laser sources uniformly over the grid, assigns a
random direction to each source, and submits the resulting world to the solver. A candidate is
accepted only if it is satisfiable within the requested horizon $T_("max")$; when a lower bound
$T_("min")$ is provided, the generator also requires the candidate to be unsatisfiable for
$T_("min") - 1$, thereby selecting levels that fall inside a difficulty window.

This generator is deliberately simple. Its main value is methodological: it gives an unbiased
sampling baseline against which more structured generators can be compared. Its main weakness is
rejection rate. As the grid grows and the number of interacting entities increases, purely random
layouts quickly become dominated by unsolvable or trivial instances.


=== Constrained Random Solvable Generator

A structured variant that biases generation toward solvable configurations before any SAT call is
made. Relative to the random solvable generator, it rejects candidates that are already
geometrically degenerate, for example when a laser points outside the grid immediately, when a
laser would have zero beam length, or when an exit lies on an unavoidable beam segment.

These filters do not themselves prove solvability, but they remove a large class of obviously bad
candidates before invoking the solver. The generator therefore remains sound with respect to the
formal solvability guarantee, while typically spending less time on layouts that fail for purely
local geometric reasons.


=== Random Cooperative Generator

The random cooperative generator extends the random solvable generator with a second SAT test based
on the strict semantics of <cooperation-detection>. A candidate is accepted only if it is
satisfiable under the standard encoding and unsatisfiable under the strict encoding. This guarantees
that every accepted level structurally requires inter-agent coordination.

The current implementation augments this binary guarantee with a *cooperation profile analyzer*.
The binary detector remains the formal guarantee used throughout the thesis: a level is cooperative
if and only if it is satisfiable under the standard semantics and unsatisfiable under the strict
semantics. The analyzer adds a second layer whose purpose is to distinguish *which kind* of
cooperation the accepted level exhibits.

Given a cooperative level, we first extract a valid joint plan from the standard SAT model. We
then run selective counterfactual checks in which one agent at a time loses the ability to block
beams of its own colour. If the level becomes unsatisfiable under that selective restriction, the
agent is identified as a necessary helper. By combining these counterfactual checks with the
helping actions observed in the extracted plan, we build a directed dependency graph between
agents.

This dependency graph is used as a generation target. In the present implementation, the generator
can recognise and filter levels according to the following profile families:

- *cooperative*: binary cooperation is required, regardless of finer structure;
- *asymmetric*: at least one one-way helping relation is present;
- *mutual*: two agents depend on each other;
- *chain*: dependencies form a directed chain without branching;
- *distributed*: one agent depends on multiple distinct helpers;
- *fully coupled*: all agents belong to a single strongly connected dependency component.

The important methodological point is that profile control is layered on top of the existing formal
machinery. The SAT encodings still certify solvability and binary cooperation. The profile analyzer
uses those certified levels as input and acts as a classification and filtering layer for the
generator.


=== Constrained Random Cooperative Generator

The constrained random cooperative generator combines the geometric filters of the constrained
solvable generator with the binary cooperation test and optional profile filter of the random
cooperative generator. In other words, it first avoids immediately degenerate geometries, then
requires the surviving candidates to satisfy the same solver-based cooperation criterion.

This generator therefore targets the same formally certified output class as the random cooperative
generator, but with a sampling distribution biased away from trivial failures. It is useful when
the goal is not only to obtain cooperative levels, but to obtain them with fewer discarded samples.


=== Constructive Solvable Generator

The constructive solvable generator replaces blind sampling with a partial-by-construction layout.
It reserves one disjoint horizontal or vertical lane per agent, places each start at one end of its
lane and the corresponding exit at the other end, and only samples walls and lasers outside the
reserved traversable lanes. Additional lasers are accepted only if their beam segments avoid the
reserved cells. The solver still acts as the final verifier, but the sampling process is strongly
biased toward jointly solvable instances.


=== Constructive Cooperative Generator

The constructive cooperative generator further specialises the constructive idea by planting a
deliberate dependency pattern. One laser is placed so that a helper agent must block a beam of its
own colour before a beneficiary lane becomes traversable. The resulting candidate is then verified
with the standard and strict SAT encodings, and can optionally be filtered by cooperation profile.
This generator is useful when one wants deliberately cooperative instances rather than merely
sampling for cooperation and hoping to find it by rejection.


=== Summary

#figure(
  table(
    columns: 4,
    stroke: black,
    inset: 8pt,
    align: horizon,
    table.header([*Generator*], [*Construction Bias*], [*Solvable*], [*Cooperative*]),
    [Random Solvable], [Uniform random sampling], [Yes (SAT check)], [No],
    [Constrained Random Solvable], [Random + geometric rejection], [Yes (SAT check)], [No],
    [Random Cooperative], [Uniform random sampling], [Yes (SAT check)], [Yes (strict UNSAT)],
    [Constrained Random Cooperative], [Random + geometric rejection], [Yes (SAT check)], [Yes (strict UNSAT)],
    [Constructive Solvable], [Reserved agent lanes], [Yes (SAT check)], [No],
    [Constructive Cooperative], [Reserved lanes + planted dependency], [Yes (SAT check)], [Yes (strict UNSAT)],
  ),
  caption: [Overview of the implemented generators and their guaranteed properties.],
)
