This part presents the original technical contribution of the thesis. Chapter 3 established the
formal problem setting: the environment model, the two decision problems, and the semantic objects
needed to state them precisely. Building on that foundation, the following sections introduce the
SAT encoding of those decision problems, the cooperation detector based on a strict counterfactual
semantics, and the family of procedural generators that use the resulting decision procedures as
acceptance oracles.

The logical order is important. The cooperation detector is not an isolated add-on; it depends on
the standard solvability encoding and changes only the beam semantics needed to test whether the
blocking action is genuinely necessary. The generator family then reuses those two decision
procedures to certify the advertised properties of accepted levels.
