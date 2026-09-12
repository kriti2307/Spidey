# Example findings (illustrative)

These examples show the expected output format, severity/confidence
calibration, and the elements every finding must include: specific
evidence, a mechanism-sound fix, and confidence-scaling where a check is
inherently uncertain from static HTML alone. They are format references,
not the basis for the checks themselves — the checks are derived from the
reasoning in `references/non-text-checklist.md` and are designed to
generalize to any site.

## NT001 — Image with no alt text (informative case)

```json
{
  "id": "NT001-4",
  "type": "issue",
  "title": "Image may contain information that is not available as text",
  "severity": "medium",
  "confidence": "medium",
  "evidence": "Image #5 (a product photo in the main content area) has no alt text. If it conveys meaningful information, that information may not be available as text.",
  "suggested_action": {
    "summary": "Provide a meaningful text alternative when the image conveys important information.",
    "priority": "medium"
  }
}
```

## NT002 — Generic / filename-style alt text

```json
{
  "id": "NT002-7",
  "type": "warning",
  "title": "Image has a generic or filename-style text alternative",
  "severity": "low",
  "confidence": "high",
  "evidence": "Image #8 uses alt text 'IMG_2041.jpg', which does not communicate its actual information.",
  "suggested_action": {
    "summary": "Replace with a meaningful description when the image is informative.",
    "priority": "low"
  }
}
```

## NT009 — Text embedded inside an image (OCR)

```json
{
  "id": "NT009-2",
  "type": "warning",
  "title": "Image contains embedded text with no clear text equivalent",
  "severity": "medium",
  "confidence": "medium",
  "evidence": "OCR detected text inside image #3 that does not appear elsewhere on the page: 'Open Mon-Sat, 11am-10pm. Sunday closed.'",
  "suggested_action": {
    "summary": "Provide this information as normal webpage text, or add a meaningful alt/long-description if it's purely visual.",
    "priority": "medium"
  }
}
```

## NT010 — Functional image with no accessible name

```json
{
  "id": "NT010-1",
  "type": "issue",
  "title": "Functional image has no accessible name",
  "severity": "high",
  "confidence": "high",
  "evidence": "Image #2 is the only content of a link (href points to /booking) and has no alt text, aria-label, or visible text -- its function is not conveyed as text.",
  "suggested_action": {
    "summary": "Add descriptive alt text or aria-label describing what the control does.",
    "priority": "high"
  }
}
```

## NT005 — Fully image-based PDF

```json
{
  "id": "NT005-0",
  "type": "issue",
  "title": "PDF appears to be fully image-based / no extractable text",
  "severity": "high",
  "confidence": "high",
  "evidence": "'/downloads/menu.pdf' has no extractable text across 3 page(s). Content likely exists only as scanned images.",
  "suggested_action": {
    "summary": "Provide a text-based version or an HTML/text equivalent of the document.",
    "priority": "high"
  }
}
```

## NT005b — Partially image-based PDF

```json
{
  "id": "NT005b-1",
  "type": "warning",
  "title": "PDF is partially image-based",
  "severity": "medium",
  "confidence": "medium",
  "evidence": "'/downloads/annual-report.pdf': 4 of 12 pages have little to no extractable text. Some content may be inaccessible to text-based readers even though the document as a whole is not fully scanned.",
  "suggested_action": {
    "summary": "Check the flagged pages -- provide text equivalents for any scanned pages.",
    "priority": "medium"
  }
}
```

## NT007 — Native audio with no transcript signal

```json
{
  "id": "NT007-0",
  "type": "warning",
  "title": "Audio may not have a text equivalent",
  "severity": "medium",
  "confidence": "medium",
  "evidence": "Audio element #1 has no <track> element, and no nearby text suggests a transcript exists.",
  "suggested_action": {
    "summary": "Provide a transcript when the audio conveys important information.",
    "priority": "medium"
  }
}
```

## NT014 — Embedded video (iframe) with no transcript signal

```json
{
  "id": "NT014-0",
  "type": "warning",
  "title": "Embedded video (iframe) may not have a text equivalent",
  "severity": "medium",
  "confidence": "low",
  "evidence": "Iframe #1 embeds video from an external provider (https://www.youtube.com/embed/...). Embedded players are opaque to this audit -- caption/transcript availability inside the player itself cannot be checked from the host page. No nearby text suggests a transcript exists. Iframe has no descriptive title attribute.",
  "suggested_action": {
    "summary": "If this embed conveys important information, provide a transcript/summary as page text near the embed, and add a descriptive iframe title attribute.",
    "priority": "medium"
  }
}
```

## NT011 — Inline SVG with no accessible text

```json
{
  "id": "NT011-0",
  "type": "warning",
  "title": "Inline SVG graphic has no accessible text equivalent",
  "severity": "medium",
  "confidence": "low",
  "evidence": "Inline <svg> #1 has 14 shape elements (may be an icon, chart, or diagram) but no <title> or aria-label.",
  "suggested_action": {
    "summary": "Add a <title> or aria-label describing the SVG's content.",
    "priority": "low"
  }
}
```

## NT012 — CSS background-image (manual review only)

```json
{
  "id": "NT012-0",
  "type": "info",
  "title": "CSS background-image detected with no adjacent text",
  "severity": "low",
  "confidence": "low",
  "evidence": "Element uses a CSS background-image ('hero-banner.jpg') and has no text content. This cannot be reliably classified as decorative vs. informative from static HTML alone -- flagged for manual review.",
  "suggested_action": {
    "summary": "Manually verify: if this image conveys information, provide a text equivalent nearby.",
    "priority": "low"
  }
}
```

## NT013 — Skipped due to robots.txt

```json
{
  "id": "NT013-2",
  "type": "info",
  "title": "PDF not analyzed -- disallowed by robots.txt",
  "severity": "low",
  "confidence": "high",
  "evidence": "Disallowed by robots.txt: https://example.com/private/internal-report.pdf",
  "suggested_action": {
    "summary": "No action -- this file was skipped to respect robots.txt.",
    "priority": "low"
  }
}
```

## Correctly-handled edge case (no finding fired) — for reference, not a finding

Illustrates why NT010 must check the priority chain before flagging, per
research on the image-as-link-accessible-name case:

```html
<a href="brochure.pdf">
  <img src="download-icon.png" alt="Download conference brochure">
</a>
```

No finding is generated here. The `<a>` has no visible text and no
`aria-label`, but the child image's `alt="Download conference brochure"`
resolves as the link's accessible name — this correctly does NOT match the
NT010 "functional image, no accessible name" pattern, and does NOT trigger
NT004 ("non-descriptive PDF link text") either, since the resolved
description is meaningful.