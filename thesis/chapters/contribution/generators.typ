#import "../../macros.typ": fref

== Design Pattern

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
cooperative generators add the strict-beam counterfactual test and, optionally, a
cooperation-profile filter.


== Generation Targets

Viewed through the solvability and cooperation definitions of @formalization, the generator family
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


== Random Solvable Generator

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


== Constrained Random Solvable Generator

A structured variant that biases generation toward solvable configurations before any SAT call is
made. Relative to the random solvable generator, it rejects candidates that are already
geometrically degenerate, for example when a laser points outside the grid immediately, when a
laser would have zero beam length, or when an exit lies on an unavoidable beam segment.

These filters do not themselves prove solvability, but they remove a large class of obviously bad
candidates before invoking the solver. The generator therefore remains sound with respect to the
formal solvability guarantee, while typically spending less time on layouts that fail for purely
local geometric reasons.


== Random Cooperative Generator

The random cooperative generator extends the random solvable generator with a second SAT test based
on the strict semantics of @cooperation-detection. A candidate is accepted only if it is
satisfiable under the standard encoding and unsatisfiable under the strict encoding. This guarantees
that every accepted level structurally requires the beam-truncation mechanism identified as
cooperation in #fref(<def-3-7>, [Definition 3.7]).

The current implementation augments this binary guarantee with a *cooperation profile analyzer*.
The binary detector remains the formal guarantee used throughout the thesis: a level is cooperative
if and only if it is satisfiable under the standard semantics and unsatisfiable under the strict
semantics. The analyzer adds a second layer whose purpose is to distinguish *which kind* of
cooperation the accepted level exhibits.

Given a cooperative level, we first extract a valid joint plan from the standard SAT model. We
then run selective counterfactual checks in which one agent at a time loses the same-colour laser
interaction used for helping behaviour. If the level becomes unsatisfiable under that selective
restriction, the agent is identified as a necessary helper. By combining these counterfactual
checks with the helping actions observed in the extracted plan, we build a directed dependency
graph between agents.

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


== Constrained Random Cooperative Generator

The constrained random cooperative generator combines the geometric filters of the constrained
solvable generator with the binary cooperation test and optional profile filter of the random
cooperative generator. In other words, it first avoids immediately degenerate geometries, then
requires the surviving candidates to satisfy the same solver-based cooperation criterion.

This generator therefore targets the same formally certified output class as the random cooperative
generator, but with a sampling distribution biased away from trivial failures. It is useful when
the goal is not only to obtain cooperative levels, but to obtain them with fewer discarded samples.


== Constructive Solvable Generator

The constructive solvable generator replaces blind sampling with a partial-by-construction layout.
On a grid of $H$ rows and $W$ columns with $n_a$ agents, it picks a random orientation, samples
a set of $n_a$ distinct *lane indices* without replacement on the orientation axis (rows for the
horizontal orientation, columns for the vertical one), places one agent start at one end of each
lane and the corresponding exit at the other end, and reserves every cell of every lane as
non-buildable. Walls and lasers are sampled only from the remaining cells, with walls drawn from
a uniformly shuffled list of free cells and truncated to the requested wall budget. Additional
lasers are accepted only if their full beam segment avoids every reserved cell. The solver acts
as the final verifier, but the sampling process is strongly biased toward jointly solvable
instances. Lanes are sampled *without* the contiguity constraint used in earlier prototypes, so
the lane band can be split anywhere on the orientation axis, which is the main source of
within-pool diversity.


== Constructive Cooperative Generator

The constructive cooperative generator inherits the lane machinery of the constructive solvable
generator and replaces its laser-placement step with one that plants a deliberate cooperation
dependency for every laser, not just one. The geometry is built in the following sequence.

+ *Orientation.* One of the two orientations (horizontal lanes / vertical lanes) is chosen
  uniformly at random per call, subject to feasibility constraints on the grid dimensions.

+ *Lane sample.* A set $L subset.eq {0, ..., D - 1}$ of $|L| = n_a$ lane indices is sampled
  without replacement on the orientation axis ($D = H$ or $D = W$). The lanes are *not* required
  to be contiguous; any subset of size $n_a$ is admissible.

+ *Rotation flip.* Independently of the orientation, a fair coin chooses whether the agent
  starts sit on the first or the last index of the perpendicular axis (and the exits sit on the
  opposite edge). Combined with the two orientations this gives all four rotations
  (agents on left, right, top, or bottom) with equal probability.

+ *Structural laser placement.* For each of the $n_l$ requested lasers, the generator picks
  - a *perpendicular column* (or row, in the vertical orientation) from a pool of distinct
    values in the interior of the perpendicular axis: ${1, ..., D_("perp") - 2}$;
  - an axis position $a in.not L$ strictly before the lane band ($a < min(L)$) or strictly
    after it ($a > max(L)$);
  - a direction perpendicular to the lane axis, pointing toward the lane band.
  These choices are independent across the $n_l$ lasers. Distinctness of the perpendicular
  columns guarantees that the resulting beams are parallel straight lines on disjoint columns,
  so no two laser sources or beam segments coincide. Each laser is given a *distinct colour* in
  ${0, ..., n_l - 1}$.

+ *Beam-path reservation.* The full unblocked beam segment of every laser, from source to grid
  edge, is added to the reserved cell set. Without this step, walls placed in the next step
  could land on a beam cell strictly between two non-adjacent lanes and clip the beam before it
  reaches the far lane, which would silently break the cooperation requirement.

+ *Walls.* The remaining free cells are shuffled uniformly and the first `num_walls` of them
  are placed as walls. Shuffling — rather than taking the row-major prefix — is what gives
  within-pool wall-mask diversity.

+ *SAT verification and profile filter.* The candidate is built into an `lle.World`, the
  standard and strict SAT encodings of @cooperation-detection are run, and the cooperation
  profile analyzer is applied. The candidate is accepted only if it is satisfiable under the
  standard semantics and unsatisfiable under the strict one — the binary cooperation criterion
  of #fref(<thm-5-1>, [Theorem 5.1]) — and if the profile analyzer's classification matches the requested family
  (default: `cooperative`, which accepts any same-colour beam-truncation requirement).

The distinct-colour multi-laser construction is the key qualitative change relative to a
single-structural-laser template: with $n_l >= 2$ each laser's beam can only be safely
truncated by the unique agent of its colour, so cooperation involves $n_l$ helpers acting on
their own beams in turn, rather than a single helper acting on one beam. On the parameter
configurations of the experiments in @experiments this consistently produces *mutual* profiles
(every helper is also a beneficiary) for $n_l = 2$ and a mix of *mutual* and *distributed*
profiles for $n_l >= 3$ when the grid is large enough.


== Constructive Level-6-Style Generator

The constructive level-6-style generator targets the specific layout shape of LLE Level 6: clustered
agent starts and clustered exits placed on opposing sides of the grid, with a corridor of lasers
between them. Agents are placed in a small rectangular cluster (a $2 times 2$ block for four agents)
in one third of the grid; exits are placed in a matching cluster in the opposite third. The
orientation (vertical with start above exit, or horizontal with start left of exit) is chosen at
random per call, and the perpendicular position of each cluster is also randomised, so that the two
clusters are always forced to span at least a third of the grid in their main axis. Lasers are then
placed inside the corridor between the clusters, oriented perpendicular to the cluster axis so that
each beam crosses the corridor; remaining free cells receive walls up to the requested wall budget.
This geometry consistently produces *mutual* cooperation profiles that mirror the structure of
Level 6, and it is the generator we recommend for producing training instances intended to transfer
to Level 6.


== Summary

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
    [Constructive Level-6-Style], [Clustered starts/exits + corridor lasers], [Yes (SAT check)], [Yes (strict UNSAT)],
  ),
  caption: [Overview of the implemented generators and their guaranteed properties.],
)
