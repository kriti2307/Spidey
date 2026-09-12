---
name: non-text-audit
description: >
  Audits a website for information that exists only in non-text form —
  images, PDFs, audio/video (native and embedded), inline SVG, and CSS
  background-images — and would therefore be invisible or degraded for
  text-based AI agents and crawlers. Explicitly avoids "existence =
  problem" rules: a PDF, an image, or a background-image is only flagged
  when it plausibly carries information with no text equivalent, and
  confidence is downgraded whenever a false positive is plausible. Use
  when diagnosing why an AI assistant might be missing facts that are
  visually present on the page but never available as text.
license: MIT
allowed-tools: ["web_fetch", "http_get"]
---

# Non-Text Content Audit

## When to use

Use this skill once a target page's HTML is available (ideally post-render,
so client-side-injected images/embeds aren't missed). This skill evaluates
whether meaningful information on the page is locked inside a non-text
medium, and if so, how confidently.

Do not use this skill to evaluate structured data (structured-data-audit),
crawlability/JS-rendering (crawl-render-audit), or fact freshness/cross-web
corroboration (freshness-corroboration). This skill only asks: *is
information here represented as machine-readable text, and if not, is
there an adequate text equivalent nearby?*

## Inputs

- `html` (required): the page's HTML, ideally post-render.
- `url` (required): the page URL, used to resolve relative image/PDF links
  and for evidence traceability.

## Procedure

Checks fall into two groups:

**Detection** (is information locked in a non-text form)
1. Image with no alt text and no accessible-name fallback — NT001 / NT010
2. Image with generic/filename-style alt text — NT002
3. Text embedded inside an image, not duplicated as page text (OCR) — NT009
4. PDF likely fully or partially image-based (no extractable text) — NT005 / NT005b
5. Audio/video (native `<audio>`/`<video>`) with no caption/transcript signal — NT007 / NT008
6. Embedded video/audio via iframe (YouTube, Vimeo, SoundCloud, etc.) with
   no nearby transcript signal — NT014
7. Inline SVG graphic with no `<title>`/`aria-label` — NT011
8. CSS background-image with no adjacent text (low-confidence, flagged for
   manual review only) — NT012

**Access hygiene** (can the important content even be reached/checked)
9. PDF linked with non-descriptive link text — NT004
10. PDF/image skipped because disallowed by robots.txt — NT013
11. PDF unreachable/unparseable — NT006
12. OCR unavailable in this environment — NT015

See `references/non-text-checklist.md` for full detection logic, thresholds,
and false-positive guardrails behind each check.

## Design principle

Existence of a PDF, image, or background-image is never itself a finding.
Every check asks: does this plausibly carry information, and is that
information available as text somewhere the visitor/agent can reach? Findings
are confidence-scaled (`high`/`medium`/`low`) rather than binary, since many
of these checks (background-images, SVG complexity, OCR relevance) can't be
resolved with certainty from static HTML alone.

## Severity guide

- **High** — functional image (the only content of a link/button) with no
  accessible name at all; PDF with zero extractable text.
- **Medium** — informative image missing alt text; partially image-based
  PDF; audio/video with no caption/transcript signal and no context hint;
  OCR-detected image text not duplicated elsewhere.
- **Low** — generic/filename alt text; non-descriptive PDF link text;
  background-image / inline-SVG findings (inherently low-confidence from
  static HTML); any finding where nearby context (caption, keyword hint)
  makes a false positive plausible.

## Output

Emit findings matching the shared marketplace schema: `id`, `title`,
`severity`, `evidence`, `suggested_action` (`summary`, `priority`). This
skill's findings also carry `type` (`issue`/`warning`/`info`) and
`confidence` (`high`/`medium`/`low`) — include these as extra fields, they
are additive to the required schema, not a replacement for it. Read-only —
this skill never edits the site or downloads beyond the configured size cap.
See `references/example-findings.md` for format/severity calibration
examples.