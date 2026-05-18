#import "../../macros.typ": fref

== Design Pattern

All generators follow a common architecture built around three principles:

+ *SAT as oracle*: the solver is not post-hoc; it is embedded in the generation loop. A candidate
  level is accepted only if the solver confirms the desired property (solvability, cooperation,
  or a specific cooperation profile).
+ *Separation of concerns*: level construction and property verification are decoupled.
  Generators build candidate levels using domain-specific heuristics; the solver decides
  acceptance.
+ *Extensibility*: every generator shares a common base class and registers itself in a
  name-keyed registry, so a new generator can be added without modifying core code.

Each generator repeatedly performs the same loop: sample or construct a candidate layout,
reject it if it violates generator-specific structural constraints, build the corresponding LLE
world instance, and run the appropriate SAT-based acceptance test. A single standard SAT call
certifies solvability. When the user additionally requires cooperation, the generator also runs
the strict-beam counterfactual test from @cooperation-detection; when a specific cooperation
profile is requested, the profile analyzer of @cooperation-profiles acts as a soft filter on
top. The cooperation requirement and the profile filter are parameters rather than separate
generator classes — *what* the generator constructs and *which extra properties* are checked
are independent axes.


== Generation Targets

Viewed through the solvability and cooperation definitions of @formalization, the generator
family targets the three level categories shown in @fig-generator-categories. Every accepted
level is solvable — categories (b) or (c); unsolvable levels in category (a) are always
rejected. When the user additionally requires cooperation, levels in (b) are rejected as well,
so only category (c) survives.

#figure(
  grid(
    columns: 3,
    gutter: 10pt,
    align: center,
    [*(a)* Unsolvable],
    [*(b)* Solvable, no cooperation],
    [*(c)* Solvable and cooperative],

    image("../../../assets/unsolvable_map_example.png", width: 100%),
    image("../../../assets/bad_map_example.png", width: 100%),
    image("../../../assets/good_map_example.png", width: 100%),
  ),
  caption: [Target level categories for the generator family.],
) <fig-generator-categories>


== Cooperation Profile Targeting <profile-targeting>

Every generator in this chapter certifies *solvability* for every accepted level — that is
the role of the SAT oracle and it is always on. On top of that always-on guarantee, the user
can stack two additional acceptance requirements drawn from @cooperation-profiles:

- *Cooperation* (optional). The candidate must additionally satisfy the strict-UNSAT
  counterfactual of #fref(<thm-5-1>, [Theorem 5.1]), so every accepted level provably requires
  the same-colour beam-truncation mechanism. Without this flag the cooperation profile is not
  inspected.
- *Profile filter* (optional, requires cooperation). The candidate must additionally match
  one of the requested cooperation-profile labels (e.g. `mutual`, `chain`, `distributed`).
  The accepted set is the corresponding sub-class of category (c) above.

Solvability is therefore the floor; cooperation and profile filtering are layered on top. All
other generator parameters — grid size, number of agents $n_a$, number of lasers $n_l$, wall
budget, horizon $T_("max")$ — are independent knobs and can be combined freely with any
choice on the cooperation axis.


== Random Generator

The random generator samples every layout component uniformly: agent start positions, exits,
wall positions, and laser source positions are drawn pairwise-distinct from the grid, and each
laser source is given a random direction. The resulting candidate is submitted to the SAT
oracle under whichever acceptance setting (solvability only, plus cooperation, or plus
cooperation with profile filter) was requested. When a lower bound $T_("min")$ is provided, the generator also requires the
candidate to be unsatisfiable for $T_("min") - 1$, selecting levels that fall inside a
difficulty window.

This generator is deliberately simple. Its main value is methodological: it gives an unbiased
sampling baseline against which more structured generators can be compared. Its main weakness
is rejection rate. As the grid grows and the number of interacting entities increases, purely
random layouts quickly become dominated by unsolvable or trivial instances.


== Constrained Random Generator

A structured variant that biases generation toward solvable configurations before any SAT
call is made. Relative to the random generator, it rejects candidates that are already
geometrically degenerate — for example a laser that points immediately outside the grid, a
laser with zero beam length, a laser on the bottom edge oriented downward, or an exit lying
on an unavoidable beam segment.

These filters do not themselves prove solvability or cooperation, but they remove a large
class of obviously bad candidates before invoking the solver. The generator therefore offers
the same formal guarantees as the random generator (solvable, optionally cooperative with
profile filter) at a typically much lower rejection rate. The constrained random variant is
the default we use when the experiments call for "random sampling" of solvable or cooperative
levels.


== Constructive Generator

The constructive generator replaces blind sampling with a partial-by-construction layout. On
a grid of $H$ rows and $W$ columns with $n_a$ agents, it picks a random orientation, samples
a set of $n_a$ distinct *lane indices* without replacement on the orientation axis (rows for
the horizontal orientation, columns for the vertical one), places one agent start at one end
of each lane and the corresponding exit at the other end, and reserves every cell of every
lane as non-buildable. Lane indices are sampled *without* a contiguity constraint, so the
lane band can be split anywhere on the orientation axis — this is the main source of
within-pool diversity.

When the generator is run in cooperative mode, the laser-placement step plants a deliberate
cooperation dependency for every requested laser, rather than relying on the solver to
*discover* one after the fact. For each of the $n_l$ lasers, the generator picks

- a *perpendicular column* (or row, in the vertical orientation) from a pool of distinct
  values in the interior of the perpendicular axis;
- an axis position strictly before or after the lane band, so the beam crosses the lane
  geometry;
- a direction perpendicular to the lane axis, pointing toward the lane band.

Each laser is given a *distinct colour* in ${0, ..., n_l - 1}$. We require $n_l <= n_a$ so
that each laser colour corresponds to a unique agent of that colour, in line with the
at-most-one-source-per-colour assumption of #fref(<def-3-1>, [Definition 3.1]). Distinctness
of the perpendicular columns guarantees that the resulting beams are parallel straight lines
on disjoint columns, so no two laser sources or beam segments coincide.

The full unblocked beam segment of every laser, from source to grid edge, is added to the
reserved cell set before walls are placed; without this step a wall could land between two
non-adjacent lanes and silently break the cooperation requirement. The remaining free cells
are then shuffled uniformly and the first $n_w$ of them are placed as walls, where $n_w$ is
the requested wall budget — shuffling rather than taking a row-major prefix is what gives
within-pool wall-mask diversity. The
finished candidate is verified by the SAT oracle exactly as in the random and constrained
random generators.

The distinct-colour multi-laser construction is the key qualitative change relative to a
single-structural-laser template. With $n_l = 1$ the geometry yields a single
helper-beneficiary pair and the cooperation profile is *asymmetric* by construction. With
$n_l = 2$ the two lasers cross each other's lanes and the profile is *mutual* — every helper
is also a beneficiary. With $n_l >= 3$ on grids large enough to accommodate the construction
the profile mix shifts toward *distributed* as one agent benefits from multiple distinct
helpers.


== Level-6-Style Generator

The level-6-style generator is a specialised constructive variant targeting the layout shape
of LLE Level 6 (see @lle-background): clustered agent starts and clustered exits placed on
opposing sides of the grid, with a corridor of lasers between them. Agents are placed in a
small rectangular cluster (a $2 times 2$ block for four agents) in one third of the grid;
exits are placed in a matching cluster in the opposite third. The orientation (vertical with
start above exit, or horizontal with start left of exit) is chosen at random per call, and
the perpendicular position of each cluster is also randomised. Lasers are then placed inside
the corridor between the clusters, oriented perpendicular to the cluster axis so that each
beam crosses the corridor; remaining free cells receive walls up to the requested wall budget.

This geometry consistently produces *mutual* cooperation profiles that mirror the structure
of Level 6, and it is the generator we recommend for producing training instances intended
to transfer to Level 6 (see the curriculum-transfer experiment in @experiments). The profile
filter from @profile-targeting still applies — the default target is `mutual`, but other
profile labels can be requested when the parameter combination supports them.


== Summary

#figure(
  table(
    columns: 2,
    stroke: black,
    inset: 8pt,
    align: horizon,
    table.header([*Generator*], [*Construction Bias*]),
    [Random], [Uniform random sampling],
    [Constrained Random], [Random + geometric rejection],
    [Constructive], [Reserved agent lanes + planted dependency],
    [Level-6-Style], [Clustered starts/exits + corridor lasers],
  ),
  caption: [Generator families and their construction bias before the SAT oracle is consulted.],
)
