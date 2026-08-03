# Design

## System

Smart Cricket uses a restrained product UI with a confident sports-tech feel. The interface is built for analysis work: recording, reviewing, reading coaching feedback, and checking shot history.

## Color

Scene phrase: evening practice lane under clean training lights, with measured olive equipment tones and precise red-ball accents.

```css
:root {
  --bg: oklch(1 0 0);
  --surface: oklch(0.975 0.006 110);
  --surface-strong: oklch(0.935 0.012 110);
  --ink: oklch(0.17 0.018 112);
  --muted: oklch(0.43 0.018 112);
  --primary: oklch(0.35 0.075 110);
  --primary-strong: oklch(0.29 0.08 110);
  --accent: oklch(0.55 0.16 28);
  --success: oklch(0.48 0.12 145);
  --warning: oklch(0.68 0.14 72);
  --danger: oklch(0.55 0.18 25);
  --line: oklch(0.88 0.01 110);
}
```

## Typography

Use one product-focused sans stack:

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

Use fixed rem-based sizes for the app shell. Reserve larger headings for the unauthenticated intro area and keep dashboard text compact.

## Components

Primary controls use olive fills with near-white text. Secondary controls use full borders and white or surface backgrounds. Panels use 12px radius or less, restrained borders, and no decorative glass effects.

Camera, auth, analysis, and chart components must include default, hover, focus, disabled, loading, and empty states.

## Layout

The app uses:

- an authenticated top bar
- a main analysis workspace
- a camera/recording area
- a right feedback panel
- a lower history/chart section

Mobile collapses to a single-column workflow: camera, result, feedback, then history.

## Motion

Motion is brief and state-driven: record indicators, loading progress, panel transitions, and chart hover feedback. All motion must be disabled or simplified under `prefers-reduced-motion`.
