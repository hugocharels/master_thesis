// `formalbox` renders a coloured definition / theorem / proposition card with a
// bold title and a body. To make the box clickably referenceable, the caller
// appends a label after the call (e.g. `#formalbox(...) <thm-5-1>`); cross-
// references then use the `#fref` helper below, which produces a clickable
// "Theorem 5.1"-style link pointing at the labelled formalbox.
#let formalbox(title, body) = block(
  width: 100%,
  fill: rgb("#f7f9fc"),
  stroke: rgb("#cbd5e1"),
  radius: 6pt,
  inset: 12pt,
)[
  *#title*
  #v(6pt)
  #body
]

// Clickable reference helper for formalbox-style elements. Usage:
//   #fref(<thm-5-1>, [Theorem 5.1])
#let fref(lbl, body) = link(lbl, body)

#let proofbox(body) = block(
  width: 100%,
  fill: rgb("#fbfcfe"),
  stroke: rgb("#d7dee8"),
  radius: 6pt,
  inset: 12pt,
)[
  *Proof.*
  #v(6pt)
  #body
]
