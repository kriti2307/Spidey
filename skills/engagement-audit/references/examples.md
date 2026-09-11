# Example findings (illustrative)

These examples show the expected output format, severity calibration, and
the three mandatory elements every finding must include: specific evidence,
mechanism-specific fix steps, and (where applicable) proactive suggestions
even in the absence of a defect. They were produced during development
testing and are included here as format references, not as the basis for
the checks themselves — the checks are derived from the discoverability/
engagement reasoning in the Round 2 appendix and are designed to generalize
to any site, not to reproduce these specific examples.

## Check 1 — Findability from homepage

```json
{
  "id": "F-eng-003",
  "type": "warning",
  "title": "Key offerings not directly represented in top-level navigation",
  "severity": "medium",
  "evidence": "Homepage highlights several specific offerings via homepage links/icons, but none appear as top-level nav items — the top nav only shows a generic parent link. The specific offerings are only visible after clicking into a submenu not shown on the homepage nav itself.",
  "suggested_action": {
    "summary": "Surface the offering categories directly in the nav.",
    "steps": [
      "Expand the generic parent nav item into a dropdown/mega-menu listing each specific offering by name, so a visitor scanning the top nav sees them without clicking in.",
      "Alternatively, add a one-line descriptor under the parent nav label on hover/tap (e.g. 'Offerings: Restaurants, Rooms, Banquets...') so the categories are visible without a full redesign.",
      "Verify the change by re-running Check 1: every homepage-highlighted offering should now have a top-level (not submenu-only) nav path."
    ],
    "priority": "medium"
  }
}
```

## Check 2 — Orientation on deep entry

```json
{
  "id": "F-eng-004",
  "type": "issue",
  "title": "Every menu item links to a single broken placeholder page",
  "severity": "critical",
  "evidence": "All items on a menu page link identically to the same URL, which returns a 404. The per-item 'order' or 'detail' action has never worked, or broke and was never fixed.",
  "suggested_action": {
    "summary": "Remove or fix the shared broken link target.",
    "steps": [
      "If per-item ordering/detail pages are not planned, remove the <a> wrapper from each menu item entirely and keep the item as plain text — a non-clickable item is less damaging than a link that 404s on every attempt.",
      "If per-item pages ARE intended, build real per-item destinations (even a simple templated page per dish) and point each item's link to its own URL instead of a shared placeholder.",
      "Add a redirect or custom 404 page at the very least as an interim fix, so visitors aren't shown a raw server error while the real fix is built.",
      "Re-test by sampling 5+ menu items after the fix and confirming each link target returns 200 and shows relevant content."
    ],
    "priority": "critical"
  }
}
```

## Check 3 — Broken links, dead-end pages & orphan pages

```json
{
  "id": "F-eng-001",
  "type": "issue",
  "title": "Broken internal link on homepage CTA",
  "severity": "critical",
  "evidence": "A homepage icon link and nav item point to an endpoint that returns a client error.",
  "suggested_action": {
    "summary": "Fix or replace the broken booking endpoint.",
    "steps": [
      "Check server logs/config for why the endpoint errors (e.g. misconfigured route, expired third-party integration) and restore it if the underlying booking system still exists.",
      "If the booking system is deprecated, replace the link target with a working alternative (a contact form, a phone number, or a third-party booking widget) rather than leaving the old endpoint live.",
      "Because this link sits on the homepage as a primary CTA, treat this as top priority — it is likely the single highest-traffic broken link on the site."
    ],
    "priority": "critical"
  }
},
{
  "id": "F-eng-002",
  "type": "issue",
  "title": "Dead-end page",
  "severity": "high",
  "evidence": "A page returns 200 OK and displays a heading but contains no unique content beyond the repeated global navigation.",
  "suggested_action": {
    "summary": "Populate the page or remove it from navigation.",
    "steps": [
      "If content for this page exists elsewhere (e.g. images stored but never embedded), add it to the page directly.",
      "If no content is ready yet, remove the nav entry pointing to this page until it has real content, rather than leaving a visible but empty destination.",
      "If the page is meant to be populated soon, add a brief 'coming soon' message with a link back to a relevant populated page, so visitors aren't left with nothing at all."
    ],
    "priority": "high"
  }
}
```

## Check 6 — Basic accessibility (opportunity example, no hard defect)

```json
{
  "id": "F-eng-005",
  "type": "opportunity",
  "title": "Missing alt text on page images",
  "severity": "medium",
  "evidence": "A header image has no alt attribute set. A screen reader user gets no information about this image, and text-extraction-based systems cannot use it as a source of information either.",
  "suggested_action": {
    "summary": "Add descriptive alt text to meaningful images.",
    "steps": [
      "Add an alt attribute describing the image's content and purpose (e.g. alt=\"Restaurant dining menu header\") rather than a generic filename or empty string.",
      "Prioritize images that convey information (menus, product photos) over purely decorative images, which can reasonably keep alt=\"\".",
      "This also benefits AI-assistant discoverability (a related skill's concern): descriptive alt text gives crawlers plain-text signal about image content they would otherwise miss entirely."
    ],
    "priority": "medium"
  }
}
```

## Proactive suggestion with no defect present (Check 3)

This illustrates the "opportunity even when nothing is broken" requirement:
a site with no broken links or dead-ends can still receive a suggestion.

```json
{
  "id": "F-eng-006",
  "type": "opportunity",
  "title": "No related-content linking between reachable pages",
  "severity": "low",
  "evidence": "All crawled pages return 200 and have working internal links (no broken-link or dead-end findings from Check 3), but individual service/product pages do not link to each other — each page only links back to top-level nav.",
  "suggested_action": {
    "summary": "Add related-content links between similar pages.",
    "steps": [
      "On each service/product page, add a small 'You might also be interested in' section linking to 2-3 related offerings.",
      "This reduces reliance on the visitor returning to the homepage to explore further, directly supporting engagement for assistant-referred visitors who land deep in the site.",
      "Low priority since no functional defect exists today — treat as a strengthening improvement, not a fix."
    ],
    "priority": "low"
  }
}
```