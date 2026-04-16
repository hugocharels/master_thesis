This chapter presents the original technical contribution of the thesis. Chapter 3 established the
formal problem setting and the SAT machinery needed to decide bounded-horizon solvability. Building
on that foundation, the present chapter introduces the additional constructions that are specific to
this thesis: a cooperation detector based on a strict counterfactual semantics, and a family of
procedural generators that use the resulting decision procedures as acceptance oracles.

The logical order is important. The cooperation detector is not an isolated add-on; it depends on
the standard solvability encoding and changes only the beam semantics needed to test whether the
blocking action is genuinely necessary. The generator family then reuses those two decision
procedures to certify the advertised properties of accepted levels.
