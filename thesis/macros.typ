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
