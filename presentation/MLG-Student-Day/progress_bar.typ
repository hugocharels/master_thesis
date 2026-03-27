#import "@preview/polylux:0.4.0": *

// ─── SETTINGS ─────────────────────────────────────────────────────────────────
#let bar-height      = 1cm
#let img-left-width  = 1cm
#let img-mid-width   = 1cm
#let img-right-width = 1cm
#let bar-margin-x    = -0.5cm
#let bar-margin-y    = -0.5cm

// Max width of the middle section:
// The bar is placed at dx = bar-margin-x (negative = extends left off-page).
// Total bar width from that anchor to right page edge = 100% - bar-margin-x.
// Subtract left cap and right cap to get the middle section's max width.
#let bar-full-width = 100% + (-bar-margin-x) - img-left-width - img-right-width

// ─── IMAGE PATHS ──────────────────────────────────────────────────────────────
#let path-left   = "progress_bar/left.png"
#let path-middle = "progress_bar/mid.png"
#let path-right  = "progress_bar/right.png"

// ─── END PLACEHOLDER — always visible at the far right, underneath the bar ────
#let end-placeholder = rect(
  width: img-right-width,
  height: bar-height,
  fill: luma(220),
  stroke: 0.5pt + black,
)

// Fixed x position of the end placeholder (same anchor as the bar)
#let end-rect-x = bar-margin-x + img-left-width + bar-full-width

// ─── MID TILE as a tiling fill ────────────────────────────────────────────────
#let mid-tiling = tiling(size: (img-mid-width, bar-height))[
  #image(path-middle, width: img-mid-width, height: bar-height, fit: "cover")
]

// ─── PROGRESS BAR ─────────────────────────────────────────────────────────────
#let image-progress-bar = toolbox.progress-ratio(ratio => {
  stack(
    dir: ltr,
    spacing: 0pt,

    // LEFT — static anchor
    box(height: bar-height, image(path-left, height: bar-height)),

    // MIDDLE — rect filled with the tiling; grows with ratio, no tile counting
    rect(
      width: ratio * bar-full-width,
      height: bar-height,
      fill: mid-tiling,
      stroke: none,
    ),

    // RIGHT — glued to the end of the filled section
    box(height: bar-height, image(path-right, height: bar-height)),
  )
})

// ─── SLIDE TEMPLATE ───────────────────────────────────────────────────────────
#let my-slide(body) = slide[

  // END placeholder — fixed position, always visible underneath
  #place(
    bottom + left,
    dx: end-rect-x,
    dy: -bar-margin-y,
    end-placeholder,
  )

  // Growing bar on top (renders above the placeholder in z-order)
  #place(
    bottom + left,
    dx: bar-margin-x,
    dy: -bar-margin-y,
    image-progress-bar,
  )

  #body
]

// ─── PRESENTATION ─────────────────────────────────────────────────────────────
#set page(paper: "presentation-16-9")
#set text(size: 24pt)

#my-slide[= Slide 1 \ Welcome!]
#my-slide[= Slide 2 \ The bar starts growing.]
#my-slide[= Slide 3 \ Halfway there.]
#my-slide[= Slide 4 \ Almost done.]
#my-slide[= Slide 5 \ Last slide — bar is full!]
