# Structured Data Audit — Detailed Checklist

This file contains the exhaustive detection logic behind each check in
`SKILL.md`. Use this when a judgment call needs more detail than the
high-level procedure provides. `SKILL.md` stays lean; this file holds the
depth.

Background: JSON-LD is the *format* structured data is written in;
Schema.org is the *vocabulary* (types like `Restaurant`, properties like
`telephone`) it uses. A page can be technically valid JSON-LD while still
being semantically wrong (wrong type) or untrustworthy (contradicts itself
or the visible page). These checks are grouped to reflect that: a page can
pass the technical group and still fail semantic or consistency checks.

---

## TECHNICAL — does it parse and follow the spec

### SD001 — No structured data detected
- [ ] Search the page for `<script type="application/ld+json">` blocks.
- [ ] If none exist, flag. Templated/no-code-built sites frequently skip
      structured data entirely — this is common, not rare.
- **Severity: High.** Every other check in this skill depends on
      structured data existing; its total absence means the machine has no
      explicit, structured representation of the page at all — it must
      infer everything from unstructured text, which is strictly less
      reliable.

### SD002 — Invalid / malformed / empty / unexpected JSON-LD
- [ ] For each JSON-LD block, attempt to parse as JSON.
- [ ] Flag parse failures as **invalid JSON-LD** (high — a broken block is
      as good as absent, but worse, since it signals neglect).
- [ ] Flag blocks with no content as **empty JSON-LD block** (medium).
- [ ] Flag valid JSON that isn't an object, array of objects, or an
      `@graph` wrapper (e.g. a bare string/number) as **unexpected
      structure** (medium).
- Use distinct IDs per sub-case (`SD002-invalid-`, `SD002-empty-`,
  `SD002-unexpected-`) so findings are traceable to the specific defect.

### SD003 — Missing `@context`
- [ ] For each parsed JSON-LD entity, check for an `@context` key.
- [ ] Flag if absent. Without it, the vocabulary the `@type`/properties are
      drawn from is ambiguous to a strict parser.
- **Severity: Medium** — most consumers assume `schema.org` by convention
  even without an explicit context, so this degrades rather than blocks.

### SD004 — Missing `@type`
- [ ] For each parsed JSON-LD entity, check for an `@type` key.
- [ ] Flag if absent — without it, nothing else in the entity can be
      semantically interpreted (a "name" and "address" mean nothing
      without knowing what kind of thing they belong to).
- **Severity: Medium.**

---

## SEMANTIC — is it the *right* structured data

### SD007 — Schema type vs. page-content mismatch
- [ ] Build a lowercase visible-text representation of the page (script/
      style/comment-stripped).
- [ ] Check for keyword signals of common page types (restaurant, hotel,
      event, product — see table below). Require **2+ distinct signal
      matches** before concluding a page type — single-keyword matches are
      too noisy (e.g. "menu" alone could mean a nav menu, not a food menu).
- [ ] If a page type is confidently detected, check whether the declared
      `@type` is compatible with it (e.g. `Restaurant`/`FoodEstablishment`/
      `LocalBusiness` are all compatible with a detected restaurant page;
      a bare `Organization` or `WebPage` is not).
- [ ] Flag mismatches. State explicitly in evidence that this is
      **heuristic-based** — a human should verify before treating it as
      confirmed, since page content can legitimately span multiple types
      (e.g. a hotel with an on-site restaurant).
- **Severity: Medium.** Generic types (e.g. `Organization` used for a page
  that is clearly a restaurant) don't break parsing, but they suppress
  domain-specific properties (cuisine, price range, opening hours) that a
  more specific type would expose — the site becomes technically compliant
  but semantically thin.

| Detected page type | Signals (2+ required) | Compatible `@type`s |
|---|---|---|
| Restaurant | restaurant, menu, book a table, reserve a table, cuisine | Restaurant, FoodEstablishment, LocalBusiness |
| Hotel | hotel, check-in, check-out, rooms, hotel booking | Hotel, LodgingBusiness, LocalBusiness |
| Event | event, conference, register, venue, date and time | Event |
| Product | add to cart, buy now, product, price, in stock | Product |

### SD008 — Missing important properties for declared type
- [ ] For each entity's `@type`, look up the recommended properties for
      that type (see table below).
- [ ] Flag any missing or empty recommended property.
- **Severity: Medium.** A `LocalBusiness`/`Restaurant`/`Hotel` missing
  `address` or `telephone` is a common, high-impact gap: these are exactly
  the facts an AI assistant is most likely to be asked for directly
  ("what's their number", "where are they").

| `@type` | Recommended properties |
|---|---|
| Restaurant / LocalBusiness / Hotel / LodgingBusiness / FoodEstablishment | name, address, telephone |
| Product | name, image, offers |
| Event | name, startDate, location |
| Organization | name, url |

### SD009 — Entity ambiguity (missing disambiguating identifier)
- [ ] For entities of a disambiguation-prone type (Organization, Person,
      LocalBusiness, Brand, Restaurant, Hotel, etc.) that have a `name`,
      check for a `sameAs` array (links to Wikidata, Wikipedia, official
      social profiles) or a stable `@id`.
- [ ] Flag if neither is present.
- **Severity: Medium.** Per the mistaken-identity problem: many businesses
  and people share names with unrelated entities. Without `sameAs`/`@id`,
  a system has no explicit signal to tell this entity apart from a
  same-named one elsewhere — it must guess from context, which fails
  silently more often than it fails loudly.
- Note: this check flags the *absence* of a disambiguator, not the quality
  of the disambiguator. Don't try to verify the `sameAs` links actually
  resolve to the correct entity — that's a corroboration-style check
  better suited to freshness-corroboration if pursued further.

### SD010 — Duplicate/conflicting `@id`
- [ ] Across all entities found on the page, collect any `@id` values.
- [ ] If two entities share an `@id` but have different `name` values,
      flag — this is a broken identity graph, not a legitimate reuse
      (legitimate reuse is the same entity referenced twice with the same
      name, which is not a problem).
- **Severity: High.** `@id` is supposed to be a stable identifier for a
  single entity; two different things claiming the same identity is a
  structural error a consuming system can't safely resolve on its own.

### (Related, not yet a standalone check) Unclear entity relationships
When a page declares multiple distinct entities (e.g. an `Organization`
and a `Product` it sells, or an `Article` and its `author`) without a
relational property connecting them (`brand`, `manufacturer`, `author`,
`publisher`, `worksFor`, etc.), a consuming system has to *infer* the
relationship rather than read it explicitly. This is a real gap identified
in research but is lower-confidence to detect generically (relational
properties vary a lot by type pairing) — treat as a **low-severity,
opportunity-type** suggestion when multiple standalone entities co-occur
with no relational property between them, rather than a hard "issue".

---

## CONSISTENCY / TRUST — does it agree with itself and with the page

### SD006 — Schema value contradicts visible page content
- [ ] For key fields (currently: `name`; extendable to `price`, event
      dates, etc.), check whether the structured-data value appears
      anywhere in the page's genuinely visible text.
- [ ] Only check values of meaningful length (≥4 chars) to avoid noise.
- [ ] Flag if the structured value is not found in visible text at all.
- **Severity: Medium**, escalate to **High** if the mismatched field is a
  fact a visitor would directly rely on (price, date, name of the specific
  thing being described) rather than a peripheral field.
- **Why this matters (core research finding):** different AI systems/agent
  pipelines may consume different *representations* of the same page — raw
  HTML, rendered DOM, visible text, or just the JSON-LD. If those
  representations disagree (e.g. visible page says "ACIFFS 2026" but
  JSON-LD says "ACIFFS 2025"; visible price is ₹799 but structured data
  says ₹599), different pipelines asked about the same page can produce
  contradictory answers — and once a source is caught being internally
  inconsistent, systems that do corroboration are more likely to distrust
  or stop citing it altogether.

### SD005 — Conflicting structured data across blocks
- [ ] Across all JSON-LD blocks/entities on the page, track values for
      `name`, `url`, `datePublished`, `dateModified`.
- [ ] If the same key appears with different values in different blocks,
      flag — cite both conflicting values and where each was found.
- **Severity: High.** This is the same underlying trust problem as SD006
  (the page disagrees with itself), except entirely within the structured
  data layer — arguably a stronger signal of neglect since there's no
  excuse of "visible text vs. hidden markup drift," it's markup
  contradicting markup.

---

## General cross-check rules (apply across all checks)

- Report each underlying defect once. If a value conflict is caught by
  both SD005 (block vs. block) and SD006 (block vs. visible text) for the
  same field, report both — they're genuinely different problems (internal
  markup consistency vs. markup-to-page consistency) — but don't fire the
  same check twice for the same value pair.
- When a check depends on a judgment call (schema-type mismatch, content
  mismatch), lean toward a lower severity and say so explicitly in
  evidence, rather than asserting it as a confirmed defect. False
  positives here cost more credibility than a missed finding.
- Always record the specific block index / entity / field the evidence
  came from — "structured data seems off" is not acceptable evidence; it
  must be traceable to a specific value.
- Out of scope for this skill (handled elsewhere in the marketplace):
  cross-web NAP consistency, fact freshness/staleness, FAQPage/author
  credibility markup (lower-confidence signals, not core), JS-injected
  JSON-LD that never reaches raw HTML (crawl-render-audit's concern).