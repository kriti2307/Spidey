# Example findings (illustrative)

These examples show the expected output format, severity calibration, and
the elements every finding must include: specific evidence,
mechanism-specific fix steps, and (where applicable) proactive suggestions
even in the absence of a defect. They are format references, not the basis
for the checks themselves — the checks are derived from the reasoning in
`references/structured-data-checklist.md` and are designed to generalize to
any site, not to reproduce these specific examples.

## SD001 — No structured data detected

```json
{
  "id": "SD001",
  "type": "issue",
  "title": "No structured data detected",
  "severity": "high",
  "evidence": "No <script type=\"application/ld+json\"> blocks were found anywhere on the page.",
  "suggested_action": {
    "summary": "Add Schema.org/JSON-LD structured data appropriate to the page type.",
    "steps": [
      "Identify the page's primary entity type (e.g. LocalBusiness, Restaurant, Product, Article) based on its actual content.",
      "Add a single JSON-LD block in the <head> or <body> with @context, @type, and the core properties for that type (name, address, telephone for a business; name, image, offers for a product).",
      "Validate the block with a JSON-LD validator before publishing.",
      "Re-run this check to confirm the block is now detected."
    ],
    "priority": "high"
  }
}
```

## SD002 — Invalid JSON-LD

```json
{
  "id": "SD002-invalid-0",
  "type": "issue",
  "title": "Invalid JSON-LD structured data",
  "severity": "high",
  "evidence": "The JSON-LD block in <script> tag #0 could not be parsed as valid JSON (trailing comma after the \"telephone\" property).",
  "suggested_action": {
    "summary": "Fix the malformed JSON-LD syntax.",
    "steps": [
      "Run the block through a JSON validator to locate the exact syntax error.",
      "Correct it (remove trailing commas, close unmatched braces/quotes).",
      "Re-validate with a Schema.org-aware validator, not just a generic JSON linter, to also catch structural issues.",
      "Confirm the fix by re-crawling the page and re-parsing the block."
    ],
    "priority": "high"
  }
}
```

## SD005 — Conflicting structured data across blocks

```json
{
  "id": "SD005-1",
  "type": "issue",
  "title": "Conflicting structured data: name",
  "severity": "high",
  "evidence": "JSON-LD block 0 declares the Event name as 'ACIFFS 2026', while JSON-LD block 1 on the same page declares it as 'ACIFFS 2025'.",
  "suggested_action": {
    "summary": "Reconcile the conflicting values to a single authoritative source.",
    "steps": [
      "Determine which value is current (check the visible page content and any official announcement for the correct year).",
      "Update every JSON-LD block on the page to use that single value — do not leave a stale block from a prior year's template.",
      "If the page is templated/CMS-generated, check whether the two blocks come from different template components (e.g. header schema vs. footer schema) that are updated independently, and fix the underlying template so both pull from one source.",
      "Re-crawl and confirm all blocks now agree."
    ],
    "priority": "high"
  }
}
```

## SD006 — Schema contradicts visible page content

```json
{
  "id": "SD006-0",
  "type": "issue",
  "title": "Structured data value not found in visible content: price",
  "severity": "high",
  "evidence": "The page's visible content displays a price of ₹799, but the JSON-LD Offer.price value is '599'. A system reading only the structured data would report a different price than what a human visitor sees.",
  "suggested_action": {
    "summary": "Sync the structured-data price with the actual current price.",
    "steps": [
      "Identify which value is correct (check the payment/checkout flow, not just the display text, as the source of truth).",
      "Update the JSON-LD Offer.price to match.",
      "If price is pulled from a CMS field, verify the structured-data generation script reads from the same field as the visible price display, rather than a separate/stale field.",
      "Re-check after the fix that both representations agree."
    ],
    "priority": "high"
  }
}
```

## SD007 — Schema type vs. page-content mismatch

```json
{
  "id": "SD007-0",
  "type": "issue",
  "title": "Potentially inappropriate Schema.org type",
  "severity": "medium",
  "evidence": "The page contains strong signals (3 keyword matches: 'restaurant', 'menu', 'reserve a table') of a restaurant page, but the structured data uses type 'Organization'. Heuristic-based — verify manually before treating as confirmed.",
  "suggested_action": {
    "summary": "Use a more specific Schema.org type to expose domain-relevant properties.",
    "steps": [
      "Change @type from 'Organization' to 'Restaurant' (or 'FoodEstablishment' if a more general food-service type fits better).",
      "Add the properties that become available/expected under the more specific type: servesCuisine, priceRange, openingHoursSpecification, menu.",
      "Keep 'Organization'-level properties (name, url, logo) — the more specific type extends rather than replaces them.",
      "Re-run the type-mismatch check to confirm it no longer fires."
    ],
    "priority": "medium"
  }
}
```

## SD008 — Missing important properties

```json
{
  "id": "SD008-0-localbusiness",
  "type": "issue",
  "title": "Important Schema.org properties are missing",
  "severity": "medium",
  "evidence": "Schema type 'LocalBusiness' is missing these important properties: address, telephone. These are exactly the facts a visitor or AI assistant is most likely to look up directly.",
  "suggested_action": {
    "summary": "Add the missing core LocalBusiness properties.",
    "steps": [
      "Add a structured 'address' object (streetAddress, addressLocality, addressRegion, postalCode).",
      "Add a 'telephone' property in a consistent, machine-parseable format (e.g. +91-XXXXXXXXXX).",
      "Cross-check these values against the visible page footer/contact page to ensure they match (avoids also triggering SD006).",
      "Re-run this check to confirm both properties are now present."
    ],
    "priority": "medium"
  }
}
```

## SD009 — Entity ambiguity (no disambiguating identifier)

```json
{
  "id": "SD009-0",
  "type": "issue",
  "title": "Entity has no disambiguating identifier (sameAs/@id)",
  "severity": "medium",
  "evidence": "Entity 'ABC Textiles' (type: Organization) has no 'sameAs' links and no stable '@id'. 'ABC' is a common name pattern; without a disambiguator, an AI assistant citing this entity has no explicit signal separating it from other unrelated organizations also named 'ABC'.",
  "suggested_action": {
    "summary": "Add sameAs links and/or a stable @id to disambiguate this entity.",
    "steps": [
      "Add a 'sameAs' array linking to the business's verified external profiles: Wikidata (if eligible), official social media accounts, Google Business Profile.",
      "Add a stable '@id' URI (e.g. the canonical page URL with a fragment) so the entity has a consistent identifier across pages of the site.",
      "Prioritize this if the business name is generic/common — the more common the name, the higher the mistaken-identity risk.",
      "Re-run this check after adding sameAs/@id to confirm it no longer fires."
    ],
    "priority": "medium"
  }
}
```

## SD010 — Duplicate/conflicting @id

```json
{
  "id": "SD010-2",
  "type": "issue",
  "title": "Duplicate @id used by conflicting entities",
  "severity": "high",
  "evidence": "@id 'https://example.com/#business' is used by both entity 'ACIFFS Restaurant' (block 0) and entity 'ACIFFS Events' (block 2) — these should be distinct entities with distinct @id values.",
  "suggested_action": {
    "summary": "Give each distinct entity its own unique @id.",
    "steps": [
      "Assign a separate, stable @id to each real-world entity (e.g. '#restaurant', '#events-division').",
      "If the two entities are genuinely meant to be the same thing under different names, resolve the name conflict instead (see SD005) rather than keeping a shared @id with mismatched names.",
      "Update any other blocks referencing the old shared @id to point to the correct one.",
      "Re-crawl and confirm no @id is shared across differently-named entities."
    ],
    "priority": "high"
  }
}
```

## Opportunity example — no defect present, proactive suggestion

This illustrates the "opportunity even when nothing is broken" case: a page
with fully valid, consistent structured data can still receive a
suggestion, per the entity-relationship gap identified in research.

```json
{
  "id": "SD011-0",
  "type": "opportunity",
  "title": "Multiple entities on page with no explicit relationship between them",
  "severity": "low",
  "evidence": "The page declares both an Organization entity and a Product entity, both technically valid and internally consistent (no SD001-SD010 findings), but no relational property (e.g. 'brand', 'manufacturer') connects the Product to the Organization.",
  "suggested_action": {
    "summary": "Add a relational property linking the entities explicitly.",
    "steps": [
      "Add a 'brand' or 'manufacturer' property on the Product entity referencing the Organization's @id.",
      "This removes the need for a consuming system to infer the relationship from proximity/context alone.",
      "Low priority — this is a strengthening improvement, not a fix, since no defect exists today."
    ],
    "priority": "low"
  }
}
```