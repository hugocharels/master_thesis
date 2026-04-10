# Cooperation Profiles for Generation

This note extends the current binary notion of cooperation used in the thesis.

The thesis already defines:

- `solvable`: the standard solver is SAT
- `requires cooperation`: the standard solver is SAT and the strict-laser solver is UNSAT

That binary property is useful for correctness, but it is not rich enough to drive a generator
towards different kinds of cooperative structure. For generation, we need a second layer:
*cooperation profiles*.

## Core idea

Instead of describing cooperation by a specific object placement such as "an exit behind a laser",
we describe it by the *dependency structure between agents*.

Define a directed dependency graph:

- `i -> j` means agent `i` must perform at least one helping action for agent `j` to finish.

Then a level can be classified by the shape of this graph.

## Interesting cooperation types

### 1. One-way helper

One agent helps another, but the dependency is not mutual.

- Graph pattern: one directed edge `i -> j`
- Interpretation: asymmetric support
- Usefulness: simplest non-trivial cooperative level

### 2. Mutual pair

Two agents depend on each other.

- Graph pattern: `i -> j` and `j -> i`
- Interpretation: bidirectional cooperation
- Usefulness: stronger than helper levels because there is no pure "support" role

### 3. Dependency chain

Agents help each other in sequence.

- Graph pattern: `i -> j -> k -> ...`
- Interpretation: ordered cooperative progression
- Usefulness: gives a clean curriculum axis through chain length

### 4. Hub-and-spoke

One central agent enables several others.

- Graph pattern: one node with high out-degree
- Interpretation: role asymmetry, coordinator or support agent
- Usefulness: interesting for studying specialised roles

### 5. Distributed support

Multiple agents each contribute part of what is needed for another agent or for the team.

- Graph pattern: several incoming edges toward the same target or subgoal
- Interpretation: no single helper is sufficient
- Usefulness: stronger than simple pairwise help

### 6. Fully coupled cooperation

All agents belong to one strongly connected dependency component.

- Graph pattern: strongly connected graph over all agents
- Interpretation: everyone needs everyone, directly or indirectly
- Usefulness: matches the intuitive notion of "full cooperation"

### 7. Synchronous cooperation

Several agents must help at the same time, not only in sequence.

- Graph pattern: dependency alone is not enough; concurrency is required
- Interpretation: coordination by simultaneity
- Usefulness: captures a different difficulty dimension than sequential dependence

### 8. Temporal baton passing

Agents help in the right order, but not necessarily simultaneously.

- Graph pattern: sequential enablement with ordering constraints
- Interpretation: scheduling-sensitive cooperation
- Usefulness: useful for levels where timing matters more than geometric difficulty

## Recommended first taxonomy for the generator

For a first implementation, the most useful target classes are:

- `asymmetric`: at least one one-way helper relation and no full mutual structure
- `mutual`: at least one bidirectional dependency pair
- `chain(k)`: a dependency chain of length `k`
- `synchronous(k)`: at least `k` agents must coordinate in the same timestep
- `fully_coupled`: all agents are in one strongly connected dependency component

These profiles are expressive enough to be interesting, but still simple enough to analyze and
target during generation.

## How to define "help"

The key point is to define cooperation structurally, not visually.

An agent helps another if removing or forbidding that help destroys the other agent's ability to
finish in any global solution.

This should be tested through *counterfactual solvability*:

- remove agent `i`
- forbid agent `i` from performing helping actions
- delay agent `i`
- forbid simultaneous helper configurations

and observe which agents or full-team solutions become impossible.

## Practical definition of a helping action in LLE

Given the current LLE mechanics used in the thesis, the main cooperative action is:

- an agent stands on a beam of its own colour, thereby making cells traversable for teammates

This is already the basis of the strict-laser cooperation detector. Therefore the first version of
cooperation profiles should build directly on same-colour laser-blocking acts.

## Recommended implementation strategy

## Short answer

Do **not** start by building a new SAT solver for every cooperation type.

Instead:

1. keep the current `WorldSolver` and `CooperationSolver`
2. add a new *analysis layer* on top of them
3. let generators filter candidates using this analyzer

This is the lowest-risk path and fits the current codebase.

## Why an analyzer first

You already have:

- `WorldSolver`: decides solvability and returns a model
- `WorldSolverStrictLaser`: removes same-colour blocking
- `CooperationSolver`: binary cooperation check

That means the hard formal machinery already exists.

What is missing is not another base solver, but a component that says:

- which agent helps whom
- whether the dependency is one-way, mutual, chained, or fully coupled
- whether simultaneity is required

This is best implemented first as a `CooperationProfileAnalyzer`.

## Proposed code structure

Suggested files:

- `src/solver/cooperation_profile_analyzer.py`
- optionally later: `src/solver/cooperation_profile_result.py`

Suggested responsibilities:

- solve the level with the standard solver
- extract one valid joint plan
- identify same-colour laser-blocking events
- run counterfactual checks to infer dependency edges
- classify the resulting dependency graph into a cooperation profile

## Suggested result object

```python
@dataclass
class CooperationProfileResult:
    solvable: bool
    cooperation_required: bool
    helper_events: list[HelperEvent]
    dependency_edges: set[tuple[int, int]]
    profile: str | None
    mutual_pairs: set[tuple[int, int]]
    longest_chain_length: int
    largest_scc_size: int
    synchronous_width: int
```

## First implementation plan

### Step 1. Reuse the existing solvers

- Run `WorldSolver`
- If UNSAT: reject immediately
- Run `CooperationSolver`
- If cooperation is not required: classify as non-cooperative

### Step 2. Extract helper events from one solution

From the satisfying model or extracted plan, detect times where:

- agent `i` occupies a cell crossed by a laser of colour `i`

These are candidate helper actions.

### Step 3. Build dependency edges with counterfactual checks

For each candidate helper event by agent `i`:

- construct a modified world or modified check that forbids this help
- test whether the global solution still exists
- inspect which agents can still finish, or whether only the team solution disappears

The first version can stay conservative:

- if forbidding helper actions of `i` destroys solvability, then `i` is globally necessary
- attribute edges from `i` to agents whose reachable exits become impossible in the induced
  partial analysis

Even a coarse dependency graph is enough to start distinguishing helper, mutual, chain, and
fully-coupled levels.

### Step 4. Classify the graph

Once edges are computed:

- one directed edge only -> `asymmetric`
- any two-cycle -> `mutual`
- longest simple path length `k` -> `chain(k)` candidate
- one SCC containing all agents -> `fully_coupled`

### Step 5. Add generator filters

Extend the cooperative generators with a target profile argument:

```bash
python generate.py random_cooperative --profile mutual
python generate.py random_cooperative --profile fully_coupled
python generate.py random_cooperative --profile chain --chain-length 3
```

The generator still samples candidate worlds, but now accepts only those whose analyzed profile
matches the target.

## What I would *not* do first

I would not immediately:

- create a separate SAT encoding for each profile
- try to directly synthesize exact dependency graphs inside CNF
- optimize generation before the profile analyzer exists

That would make the system much harder to debug.

## Long-term evolution

Once the analyzer works, there are two natural improvements:

### 1. Smarter generation

Use profile-aware construction heuristics instead of pure rejection sampling.

Examples:

- for `mutual`, place two colored bottlenecks that cross-enable each other
- for `chain`, place staged coloured gates in sequence
- for `fully_coupled`, force all agents through interlocking regions

### 2. Stronger formalization

Later, some profile checks could be compiled more directly into SAT or verified with dedicated
constraints. But this should be a second step, after the analyzer-based pipeline is validated.

## Final recommendation

For the current state of the project:

- keep the current solver as the formal correctness engine
- keep the current cooperation solver as the binary gate
- add a `CooperationProfileAnalyzer` as a verification and classification layer
- make generators target a requested cooperation profile by filtering on that analyzer

So the next implementation should be:

- **not** a brand new solver family
- **not** just ad hoc geometric heuristics
- **but** an analyzer-driven generator built on top of the solvers you already trust
