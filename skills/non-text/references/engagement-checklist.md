# Non-Text Content Audit — Detailed Checklist

This file contains the exhaustive detection logic behind each check in
`SKILL.md`. Use this when a judgment call needs more detail than the
high-level procedure provides. `SKILL.md` stays lean; this file holds the
depth.

Core framing (from research): the question is not "does every image have
alt text" — it's "is important information represented in a form an AI
agent can actually access as text, and if not, is there an adequate
equivalent?" Existence of a PDF/image/background-image is never itself a
problem; every check below tries to reflect that and downgrades confidence
when a false positive is plausible.

---

## IMAGES

### NT001 — Image has no alt text (informative case)
- [ ] For every `<img>` without an `alt` attribute, and not otherwise
      marked decorative (see below), flag.
- [ ] Check for nearby context that reduces (but does not eliminate) real-
      world severity: a `<figcaption>` inside a parent `<figure>`, or an
      `aria-describedby` reference. If present, downgrade to low severity/
      confidence rather than dropping the finding — nearby context can be
      partial, not a substitute for a real alt.
- [ ] **Do not flag** images where `alt=""` (explicit empty alt) or
      `role="presentation"`/`role="none"` is set — both are standard,
      intentional ways to mark an image as decorative. This is a deliberate
      design choice, not an oversight: `alt="" ≠ missing alt`.
- **Severity: Medium** (or **Low** if caption context present).

### NT002 — Generic or filename-style alt text
- [ ] Normalize the alt text (lowercase, collapsed whitespace).
- [ ] Flag if it matches a generic-word list (`image`, `photo`, `icon`,
      `logo`, etc.), a filename-style pattern (`img_1234.jpg`,
      `screenshot42`), or is ≤2 characters.
- [ ] Reasoning: alt text like "image" or "IMG_4821.jpg" technically
      satisfies "has an alt attribute" while communicating nothing — a
      pure format-compliance check would miss this entirely.
- **Severity: Low** — the image isn't inaccessible, just poorly described.

### NT009 — Text embedded inside an image (OCR)
- [ ] Skip images below a minimum pixel dimension (icons/spacers/social
      buttons aren't worth OCR-ing).
- [ ] Skip images that already have alt text ≥10 characters (already has a
      meaningful text equivalent — don't second-guess it).
- [ ] Run OCR; skip if detected text is under a minimum length (avoids
      flagging OCR noise from decorative textures/logos).
- [ ] **Suppress the finding if the OCR'd text already appears elsewhere on
      the page's visible text** — this is the key false-positive guard: an
      image duplicating a heading that's also rendered as real HTML text is
      not a problem, even though it "contains text."
- [ ] Runtime budget: cap the number of images OCR'd per page (this is the
      slowest check in the skill) — beyond the cap, skip rather than risk
      exceeding the marketplace's runtime limit.
- [ ] If OCR tooling (tesseract binary) isn't available in the running
      environment, skip this check entirely and emit a single info-level
      "OCR unavailable" finding rather than crashing or silently doing
      nothing.
- **Severity: Medium**, confidence medium — OCR proves text exists in the
  image, not that the text is important; a human should still judge
  relevance from the excerpt shown in evidence.

### NT010 — Functional image (link/button) with no accessible name
- [ ] For an `<img>` inside an `<a>`/`<button>` with no `alt`, check whether
      the parent link/button has *any* accessible name via: `aria-label`,
      visible text, any child image's alt, or `title` — in that priority
      order (matches how assistive tech resolves it).
- [ ] Flag only if none of those are present.
- [ ] **Key edge case handled:** `<a href="brochure.pdf"><img alt="Download
      conference brochure"></a>` — the image's alt IS the link's accessible
      name here. This must not be flagged as a broken/empty link, even
      though the `<a>` itself has no visible text.
- **Severity: High.** Unlike a decorative or informative image, a
  functional image with zero accessible name means the *action itself* —
  what clicking this does — is unrecoverable as text. That's a stronger
  failure than a missing description of a picture.

---

## PDFs

### NT005 / NT005b — Image-based PDF (fully / partially)
- [ ] Download the PDF (respecting robots.txt and a size cap — see access
      hygiene section).
- [ ] Extract text per page.
- [ ] If total extracted text across all pages is empty → **fully
      image-based**, high severity. The document is a scanned image
      wearing a PDF extension; no text-based system can read any of it.
- [ ] If ≥30% of pages individually have near-zero extractable text (but
      the document as a whole isn't empty) → **partially image-based**,
      medium severity. This catches the common case of a mostly-text report
      with a few scanned signature/chart pages mixed in — a whole-document
      check alone would miss this.
- **Why this matters:** per research, PDFs are not inherently a problem —
  the failure mode is specifically when real content becomes scanned-image-
  only, since that's invisible to any text extractor, not just accessibility
  tools.

### NT003 — PDF content may lack a webpage text equivalent
- [ ] For every PDF link (excluding ones already flagged fully image-based
      by NT005, to avoid redundant findings on the same document), flag
      that important information may live only inside the PDF.
- **Severity: Medium.** Even a well-formed, text-extractable PDF is still a
  secondary hop a crawler/agent may not take — the ideal is that important
  facts are *also* present as normal webpage text, not just PDF-locked.

### NT004 — Non-descriptive PDF link text
- [ ] Resolve the link's accessible name using the same priority order as
      NT010 (aria-label > visible text > image alt > title).
- [ ] Flag if that resolved description matches a generic-phrase list
      ("click here", "download", "view pdf", etc.) or is ≤2 characters.
- **Severity: Low.**

---

## AUDIO / VIDEO

### NT007 / NT008 — Native `<audio>`/`<video>` with no caption/transcript
- [ ] Check for a `<track kind="captions"|"subtitles"|"descriptions">`
      child — if present, pass immediately (strong, explicit signal).
- [ ] If absent, check the element's parent text for loose keyword hints
      ("transcript", "captions", "subtitles", "text version").
- [ ] Flag regardless, but **downgrade severity/confidence to low** when a
      keyword hint is present — a keyword match is not proof a transcript
      actually exists or is linked correctly, just a reason to be less
      confident this is a real gap.
- **Severity: Medium** (no hint) / **Low** (hint present).
- **Open research area (per notes):** whether/how different AI systems
  directly consume audio/video content itself (vs. relying on a text
  equivalent) was deliberately not pursued further — this check assumes
  a text equivalent is the safe target regardless of that open question.

### NT014 — Embedded video/audio via iframe
- [ ] Native `<video>`/`<audio>` tags are the minority case in real sites —
      most embeds are YouTube/Vimeo/Wistia/Loom/SoundCloud/Spotify iframes.
      Check iframe `src` domains against a known-provider list.
- [ ] Apply the same keyword-hint logic as NT007/NT008 to the iframe's
      surrounding text.
- [ ] Note explicitly in evidence that the embedded player's *own* caption
      support cannot be checked from the host page — this check can only
      assess whether the host page provides a text equivalent nearby, not
      whether the platform itself has captions on.
- **Severity: Medium** (no hint) / **Low** (hint present). **Confidence:
  always low** — more uncertainty here than the native-tag case, since we
  can't inspect the embedded player at all.

---

## OTHER NON-TEXT FORMS

### NT011 — Inline SVG with no accessible text
- [ ] Only consider SVGs with more than one shape child element (`path`,
      `circle`, `rect`, `polygon`, `line`) — single-shape SVGs are almost
      always trivial icons, not real graphics/charts/diagrams.
- [ ] Skip if `aria-hidden="true"` — an explicit signal the author intended
      it to be ignored by assistive tech/text extraction, same logic as
      `alt=""` on images.
- [ ] Flag if no `<title>` and no `aria-label`.
- **Severity: Medium**, confidence **low** — the "is this a real graphic"
  heuristic (shape count) is crude by nature.

### NT012 — CSS background-image with no adjacent text
- [ ] Find elements with an inline `style` containing `background-image:
      url(...)`.
- [ ] Only flag if the element also has zero text content (a background-
      image behind actual text isn't the same failure mode).
- [ ] Explicitly framed as **info-level, low-confidence, manual-review-only**
      — static HTML alone cannot distinguish a purely decorative background
      texture from one carrying real information (e.g. an infographic set
      as a background-image). This is a known, accepted limit, not a gap to
      "solve" with more heuristics.

---

## ACCESS HYGIENE

### NT013 — Skipped due to robots.txt
- [ ] Before fetching any PDF or image, check the origin's `robots.txt`.
- [ ] If disallowed, do not fetch; emit an info-level finding noting the
      skip rather than silently omitting it or treating it as a defect —
      the marketplace's scope rules require respecting robots.txt, and this
      makes that compliance visible rather than invisible.
- [ ] If robots.txt itself is unreachable, fail open (treat as allowed) —
      an unreachable robots.txt is not evidence that fetching is
      disallowed.

### NT006 — PDF unreachable/unparseable
- [ ] Any PDF that fails to download or fails to parse as a PDF at all
      (distinct from NT005's "parses fine but has no text").
- **Severity: Low**, confidence low — this is as much a possible transient/
  network issue as it is a site defect; don't over-assert it.

### NT015 — OCR unavailable
- [ ] If the OCR dependency (tesseract binary) isn't present in the running
      environment, emit exactly one info-level finding for the whole audit
      run, rather than one per skipped image.
- Purpose: makes a real coverage gap visible to whoever reads the report,
  instead of the audit silently under-reporting NT009 findings with no
  explanation.

---

## General cross-check rules

- Findings carry both `severity` (required by the shared schema) and two
  additive fields, `type` (`issue`/`warning`/`info`) and `confidence`
  (`high`/`medium`/`low`) — these aren't a replacement for severity, they
  let the entrypoint/report reader distinguish "confirmed defect" from
  "flagged for manual review" at a glance.
- Never treat existence alone (of a PDF, image, background-image, or
  embed) as a finding. Every check requires a specific reason to believe
  information is present and inaccessible as text.
- When a check's confidence is inherently limited by static HTML (SVG
  complexity heuristic, background-image decorative-vs-informative,
  embedded-player caption support), say so explicitly in the evidence text
  rather than asserting it as a confirmed defect.
- Resolve all relative `src`/`href` values against the page URL before
  fetching — a large share of real content uses relative paths, and
  silently skipping them under-reports genuine findings.
- Out of scope for this skill (handled elsewhere in the marketplace):
  structured data (structured-data-audit), crawlability/JS-rendering gaps
  that hide these elements entirely before this skill even sees them
  (crawl-render-audit), fact freshness/cross-web corroboration
  (freshness-corroboration).