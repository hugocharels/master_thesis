// `formalbox` renders a coloured definition / theorem / proposition / constraint card with
// a bold title and a body. To make the box clickably referenceable, the caller appends a
// label after the call (e.g. `#formalbox(...) <thm-5-1>`); cross-references then use the
// `#fref` helper below, which produces a clickable "Theorem 5.1"-style link pointing at
// the labelled formalbox.
//
// The card is rendered with the `thmbox` package (https://typst.app/universe/package/thmbox/):
// a coloured accent bar, a sans-serif title in the accent colour, and a light background
// fill. We call the low-level `thmbox` function directly with `numbering: none` so the
// package's automatic counter is bypassed — the thesis numbers its formal objects by hand
// in the title ("Definition 3.1", "Constraint 4.1", ...) to keep them aligned with the
// chapter numbers. We deliberately do NOT run `thmbox-init()`, because it issues a
// document-wide `set heading(numbering: "1.1")` that would override the custom chapter /
// appendix heading numbering set up in main.typ.
//
// The `kind` keyword selects a palette so each formal-object type renders in a distinct
// colour. Supported kinds: "definition", "constraint", "proposition", "theorem", "lemma",
// "corollary". Any other value falls back to the neutral "default" palette.
#import "@preview/thmbox:0.3.0": thmbox

// thmbox defaults its title font to "New Computer Modern Sans", which is not bundled with
// Typst and triggers an "unknown font family" warning on every box. We pin the box fonts to
// "New Computer Modern" (the thesis body font, always available) so the cards stay typo-
// graphically consistent with the rest of the document and the build is warning-free.
#let _box-font = "New Computer Modern"

#let formalbox(title, body, kind: "default") = {
  // Palette: Okabe & Ito's colourblind-safe qualitative set (Color Universal Design),
  // the de-facto standard for scientific figures — see https://jfly.uni-koeln.de/color/ .
  // The accent (bar + title) is the saturated colour; the background is the same accent
  // lightened to a faint tint, so the fill stays subtle and tonally matched to its title.
  let accents = (
    default: rgb("#555555"),
    definition: rgb("#1F4E79"), // blue
    theorem: rgb("#6A3D9A"), // deep blue
    lemma: rgb("#6A3D9A"), // purple
    corollary: rgb("#0F766E"), // teal
    proposition: rgb("#D4A017"), // gold/yellow
    constraint: rgb("#B45F06"), // orange
  )
  let accent = accents.at(kind, default: accents.default)
  let p = (accent: accent, fill: accent.lighten(88%))
  // `color` drives the accent bar (and is thmbox's default title colour). We keep the bar
  // accent-coloured but force the title itself to black by wrapping it in an explicit
  // `text(fill: black, ...)`, which overrides thmbox's title colour. The fill is the faint
  // accent tint.
  thmbox(
    variant: text(fill: black, title),
    title: none,
    numbering: none,
    color: p.accent,
    fill: p.fill,
    title-fonts: _box-font,
    sans-fonts: _box-font,
    body: body,
  )
}

// Clickable reference helper for formalbox-style elements. Usage:
//   #fref(<thm-5-1>, [Theorem 5.1])
#let fref(lbl, body) = link(lbl, body)

// Proof card. Rendered with the same `thmbox` styling but without a background fill — a
// proof is a passage of reasoning rather than a highlighted statement, so it carries only
// the neutral accent bar to set it apart from the surrounding body text.
#let proofbox(body, breakable: true) = {
  // thmbox wraps every card in a `figure`, and a figure does NOT split across a
  // page boundary by default: an oversized proof is pushed whole onto the next
  // page (leaving a gap) or overflows the page. The show rule below makes the
  // figure's block breakable, so a long proof flows across as many pages as it
  // needs. The title bar is `sticky`, so "Proof." is never orphaned at the foot
  // of a page. Pass `breakable: false` to force a proof to stay on one page.
  show figure.where(kind: "thmbox"): set block(breakable: breakable)
  thmbox(
    variant: text(fill: black)[Proof.],
    title: none,
    numbering: none,
    color: rgb("#555555"), // grey accent bar; title forced black via the wrapped `text`
    fill: none,
    title-fonts: _box-font,
    sans-fonts: _box-font,
    body: body,
  )
}
