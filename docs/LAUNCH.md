# Launch Checklist

## Positioning

**One-liner:** "The desktop app that turns an idea into a deployed app — specs, code,
tests, deploy — running entirely on your machine."

**Differentiators to lead with:**
1. Local-first (keys + code never leave the laptop) — the sharpest angle vs. cloud AI builders.
2. Watchable pipeline — the live timeline demo *is* the marketing asset.
3. Bring-your-own-model — works with self-hosted gateways, not locked to one vendor.

**Honesty rule:** don't claim end-to-end autonomy until ROADMAP 🔴 items ship.
Position v0.1 as "public beta of the pipeline runner."

## Pre-launch (engineering)

- [ ] ROADMAP items 🔴1, 🔴2 fixed (pipeline honest end-to-end)
- [ ] Signed + notarized dmg (🔴3)
- [ ] Fresh-machine install test (new macOS user account: dmg → first run → demo mode)
- [ ] Version bump + CHANGELOG.md
- [ ] GitHub repo public: README, LICENSE, docs/, issue templates, CI green badge

## Assets

- [ ] 60–90s demo video (script in TUTORIAL.md "Recording a demo video")
- [ ] 3 screenshots: Forge mid-run, Artifacts (PRD open), Services page
- [ ] Landing page deployed (`website/index.html` — works on GitHub Pages as-is)
- [ ] Social card image (1200×630)

## Channels (in order of expected ROI)

1. **Hacker News — Show HN.** Title: "Show HN: DevFoundry – a local-first desktop app
   that runs an AI software factory". Post the demo video + repo. Answer every comment
   for the first 4 hours.
2. **r/LocalLLaMA.** Emphasize BYO-model + self-hosted gateway support; this crowd
   cares about exactly that. Include the demo-mode one-liner so they can try without keys.
3. **X/Twitter thread.** 6–8 tweets: hook (video), the 5-stage pipeline, local-first
   argument, demo-mode GIF, repo link.
4. **YouTube.** 5-minute "idea to deployed app" walkthrough; the timeline UI makes
   compelling B-roll.
5. **Product Hunt** after the HN/Reddit feedback round settles (ship the fixes first).

## Launch-day ops

- [ ] Pin a "Known issues / roadmap" issue linking docs/ROADMAP.md
- [ ] Enable GitHub Discussions for support
- [ ] Watch: install failures (Gatekeeper), Docker startup flow, first-run confusion
- [ ] Tag `v0.1.0` release with the dmg attached

## Success metrics (first 2 weeks)

- 500 unique repo visitors / 100 stars
- 50 dmg downloads, ≥10 completed real pipeline runs (ask in Discussions)
- 3 actionable pieces of feedback that reorder the roadmap
