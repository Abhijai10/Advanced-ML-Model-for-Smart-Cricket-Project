# Smart Cricket Frontend Product Design

## Current Frontend Scope

The frontend now presents Smart Cricket as a complete product surface rather than a single prototype screen. The public information architecture is:

- `/` public landing page
- `/auth` sign-in, sign-up, and demo entry
- `/app` practice overview
- `/app/analyze` camera/upload analysis workspace
- `/app/history` trusted history and trends
- `/app/history/:id` analysis detail route
- `/app/settings` account, privacy, capabilities, and model-improvement state

Routing uses React Router. Demo mode remains local to the browser session, and authenticated mode continues to use Supabase where configured.

## Design Direction

Smart Cricket should feel like premium athletic intelligence: focused, precise, and practice-ready. The visual foundation is near-black with pitch-green depth, lime action color, restrained blue and clay accents, crisp borders, and dense but readable product surfaces.

The UI should avoid generic AI landing-page patterns, student dashboard styling, neon gamer treatment, and decorative cricket clichés. Motion is intentionally light and should support attention, not distract from analysis.

## React Bits-Style Component Inventory

The implementation uses local TypeScript/CSS components inspired by the free React Bits component patterns. They are kept local to avoid adding heavy visual dependencies or Tailwind conversion work.

- `SoftAurora`: subtle landing background atmosphere
- `BlurText`: one-time landing headline reveal
- `AnimatedContent`: landing and result panel entrance polish
- `SpotlightCard`: primary card/panel treatment
- `PillNav`: app navigation
- `Stepper`: analysis workflow state
- `CountUp`: metric and result values
- `MagicBento`: feature and score grouping
- `AnimatedList`: recent analysis rows
- `BorderGlow`: active camera/analyzing frame
- `ShinyText`: landing product label

## Preserved Behaviors

The redesign preserves existing product behavior:

- Supabase auth session detection and sign-out
- Demo mode entry when auth is unavailable
- Camera lifecycle and stream cleanup
- MediaRecorder MIME fallback
- Upload preview before submission
- Retention consent gating
- Analysis API submission
- Result persistence state
- TTS/audio fallback
- Feedback submission and model-improvement consent rules
- History trust filtering
- Responsive and accessibility smoke coverage

## Verification

Frontend verification should include:

- `npm run lint`
- `npm run build`
- `npm run test`
- `npm run test:e2e`
- `npm audit --audit-level=high`
- Visual screenshots for landing, auth, overview, analysis result, and history at desktop and mobile widths

Final visual artifacts from this pass were captured at:

- `/private/tmp/smart-cricket-visual/landing-desktop.png`
- `/private/tmp/smart-cricket-visual/auth-desktop.png`
- `/private/tmp/smart-cricket-visual/overview-desktop.png`
- `/private/tmp/smart-cricket-visual/result-desktop.png`
- `/private/tmp/smart-cricket-visual/history-desktop.png`
- `/private/tmp/smart-cricket-visual/landing-mobile.png`
- `/private/tmp/smart-cricket-visual/auth-mobile.png`
- `/private/tmp/smart-cricket-visual/overview-mobile.png`
- `/private/tmp/smart-cricket-visual/result-mobile.png`
- `/private/tmp/smart-cricket-visual/history-mobile.png`
