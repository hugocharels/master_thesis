// `formalbox` renders a coloured definition / theorem / proposition / constraint card with
// a bold title and a body. To make the box clickably referenceable, the caller appends a
// label after the call (e.g. `#formalbox(...) <thm-5-1>`); cross-references then use the
// `#fref` helper below, which produces a clickable "Theorem 5.1"-style link pointing at
// the labelled formalbox.
//
// The `kind` keyword selects a palette so each formal-object type renders in a distinct
// colour. Supported kinds: "definition", "constraint", "proposition", "theorem", "lemma",
// "corollary". Any other value falls back to the neutral "default" palette.
#let formalbox(title, body, kind: "default") = {
  // Palette: Tailwind CSS — fill = *-50, stroke = *-200 (or *-300 where the chroma
  // is too pale to be visible, e.g. grey/gray).
  let palette = (
    default:     (fill: rgb("#f9fafb"), stroke: rgb("#6b7280")),  // gray-50 fill (very light) / gray-500 stroke (clearly visible) — light fill, defined border
    definition:  (fill: rgb("#eff6ff"), stroke: rgb("#bfdbfe")),  // blue-50 / blue-200
    constraint:  (fill: rgb("#fef2f2"), stroke: rgb("#fecaca")),  // red-50 / red-200
    proposition: (fill: rgb("#fefce8"), stroke: rgb("#fde68a")),  // yellow-50 / yellow-200
    theorem:     (fill: rgb("#fefce8"), stroke: rgb("#fde68a")),  // yellow-50 / yellow-200
    lemma:       (fill: rgb("#faf5ff"), stroke: rgb("#e9d5ff")),  // purple-50 / purple-200
    corollary:   (fill: rgb("#faf5ff"), stroke: rgb("#e9d5ff")),  // purple-50 / purple-200
  )
  let p = palette.at(kind, default: palette.default)
  block(
    width: 100%,
    fill: p.fill,
    stroke: p.stroke,
    radius: 6pt,
    inset: 12pt,
    breakable: false,
  )[
    *#title*
    #v(6pt)
    #body
  ]
}

// Clickable reference helper for formalbox-style elements. Usage:
//   #fref(<thm-5-1>, [Theorem 5.1])
#let fref(lbl, body) = link(lbl, body)

#let proofbox(body) = block(
  width: 100%,
  fill: rgb("#e5e7eb"),  // Tailwind gray-200
  stroke: rgb("#9ca3af"),  // Tailwind gray-400
  radius: 6pt,
  inset: 12pt,
  breakable: false,
)[
  *Proof.*
  #v(6pt)
  #body
]
