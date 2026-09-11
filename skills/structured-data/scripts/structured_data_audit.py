import json
from bs4 import BeautifulSoup, Comment


def _get_visible_text(html: str) -> str:
    """Build visible-text (lowercased) with script/style/comments stripped.

    Built from a separate soup instance so the caller's soup (used to find
    the JSON-LD blocks themselves) isn't mutated.

    NOTE (coordination w/ crawl-render-audit skill): this only sees the raw
    HTML as fetched. If structured data or key facts are injected client-side
    via JS, that gap is the crawl-render-audit skill's responsibility to
    flag (SSR vs post-render diff) — not duplicated here.
    """
    text_soup = BeautifulSoup(html, "html.parser")

    for tag in text_soup(["script", "style", "noscript"]):
        tag.decompose()

    for comment in text_soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    return text_soup.get_text(" ", strip=True).lower()


def _normalize_types(schema_type) -> list:
    """Return @type as a lowercase list, regardless of whether the source
    value was a single string or a list of strings."""
    if not schema_type:
        return []
    if isinstance(schema_type, list):
        return [str(t).lower() for t in schema_type if t]
    return [str(schema_type).lower()]


def _iter_entities(data):
    """Flatten a parsed JSON-LD payload into a list of dict entities.

    Handles three shapes:
      - a single object:                  {"@type": "Restaurant", ...}
      - a top-level array of objects:      [{...}, {...}]
      - an @graph wrapper object:          {"@context": ..., "@graph": [...]}
    Non-dict/non-list payloads (or malformed items inside a list/@graph)
    are skipped.
    """
    entities = []

    def add(item):
        if isinstance(item, dict):
            entities.append(item)

    if isinstance(data, list):
        for item in data:
            add(item)
    elif isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            for item in data["@graph"]:
                add(item)
            # Some publishers also put @type directly on the wrapper
            # alongside @graph (e.g. a WebPage wrapping a @graph of
            # entities) — keep it too so it still gets checked.
            if "@type" in data:
                add(data)
        else:
            add(data)

    return entities


def check_schema_type(visible_text, data, index):
    """Flag structured data whose @type looks mismatched against strong,
    repeated page-content signals (e.g. a page that clearly reads as a
    restaurant page but is marked up as something unrelated).

    Heuristic-based: keyword signals on visible text. Requires >=2 distinct
    signal matches before flagging anything, to keep false positives low.
    Evidence text says so explicitly, so a human reviewer knows to sanity
    check before acting.
    """
    findings = []

    if not isinstance(data, dict):
        return findings

    schema_types = _normalize_types(data.get("@type"))
    if not schema_types:
        return findings

    # Strong page-type signals. Heuristic only: a page can legitimately
    # trip signals for more than one type (e.g. a hotel restaurant), in
    # which case only the first type matched (dict order) is evaluated.
    page_type_signals = {
        "restaurant": [
            "restaurant",
            "menu",
            "book a table",
            "reserve a table",
            "cuisine",
        ],
        "hotel": [
            "hotel",
            "check-in",
            "check-out",
            "rooms",
            "hotel booking",
        ],
        "event": [
            "event",
            "conference",
            "register",
            "venue",
            "date and time",
        ],
        "product": [
            "add to cart",
            "buy now",
            "product",
            "price",
            "in stock",
        ],
    }

    detected_type = None
    for page_type, signals in page_type_signals.items():
        matches = sum(signal in visible_text for signal in signals)
        # Require multiple signals so we don't flag based on one word.
        if matches >= 2:
            detected_type = page_type
            break

    if not detected_type:
        return findings

    compatible_types = {
        "restaurant": {"restaurant", "foodestablishment", "localbusiness"},
        "hotel": {"hotel", "lodgingbusiness", "localbusiness"},
        "event": {"event"},
        "product": {"product"},
    }

    if not any(
        expected_type in schema_types
        for expected_type in compatible_types[detected_type]
    ):
        findings.append({
            "id": f"SD007-{index}",
            "title": "Potentially inappropriate Schema.org type",
            "severity": "medium",
            "evidence": (
                f"The page contains strong signals (2+ keyword matches) of a "
                f"{detected_type} page, but the structured data uses "
                f"type(s): {', '.join(schema_types)}. Heuristic-based — "
                f"verify manually before treating as confirmed."
            ),
            "suggested_action": {
                "summary": (
                    f"Review whether a more specific Schema.org type such as "
                    f"{detected_type.title()} better represents this page."
                ),
                "priority": "medium",
            },
        })

    return findings


def check_required_properties(data, index):
    """Flag missing recommended properties for common Schema.org types.

    Handles list-valued @type by checking each type present against the
    recommended-properties table (rather than stringifying the whole list,
    which would never match).
    """
    findings = []

    if not isinstance(data, dict):
        return findings

    schema_types = _normalize_types(data.get("@type"))
    if not schema_types:
        return findings

    recommended_properties = {
        "restaurant": ["name", "address", "telephone"],
        "localbusiness": ["name", "address", "telephone"],
        "hotel": ["name", "address", "telephone"],
        "lodgingbusiness": ["name", "address", "telephone"],
        "foodestablishment": ["name", "address", "telephone"],
        "product": ["name", "image", "offers"],
        "event": ["name", "startDate", "location"],
        "organization": ["name", "url"],
    }

    checked_types = set()
    for schema_type in schema_types:
        required = recommended_properties.get(schema_type)
        if not required or schema_type in checked_types:
            continue
        checked_types.add(schema_type)

        missing = [prop for prop in required if prop not in data or not data[prop]]

        if missing:
            findings.append({
                "id": f"SD008-{index}-{schema_type}",
                "title": "Important Schema.org properties are missing",
                "severity": "medium",
                "evidence": (
                    f"Schema type '{schema_type}' is missing "
                    f"these important properties: {', '.join(missing)}."
                ),
                "suggested_action": {
                    "summary": (
                        "Add relevant properties that accurately describe "
                        "the entity represented by the page."
                    ),
                    "priority": "medium",
                },
            })

    return findings


def check_visible_content_conflicts(visible_text, data, index):
    """Flag structured-data values (currently: name) that don't appear
    anywhere in the page's genuinely visible text."""
    findings = []

    if not isinstance(data, dict):
        return findings

    fields_to_check = ["name"]

    for field in fields_to_check:
        if field not in data:
            continue

        value = str(data[field]).strip()
        if not value:
            continue

        if len(value) >= 4 and value.lower() not in visible_text:
            findings.append({
                "id": f"SD006-{index}",
                "title": f"Structured data value not found in visible content: {field}",
                "severity": "medium",
                "evidence": (
                    f"Structured data contains {field}='{value}', "
                    "but that value was not found in the page's visible text."
                ),
                "suggested_action": {
                    "summary": (
                        f"Verify that the structured-data '{field}' value "
                        "matches the visible page content."
                    ),
                    "priority": "medium",
                },
            })

    return findings


def check_entity_ambiguity(data, index):
    """Flag Organization/Person/LocalBusiness/Brand entities with a name
    but no disambiguating identifier (sameAs to Wikipedia/Wikidata/social
    profiles, or an @id URI).

    Maps to Round-2 appendix D: "mistaken identity when several things
    share a name" — without a disambiguator, an AI assistant citing this
    entity has no way to tell it apart from unrelated namesakes.
    """
    findings = []

    if not isinstance(data, dict):
        return findings

    schema_types = _normalize_types(data.get("@type"))
    disambiguation_prone_types = {
        "organization", "person", "localbusiness", "brand",
        "restaurant", "hotel", "lodgingbusiness", "foodestablishment",
    }

    if not any(t in disambiguation_prone_types for t in schema_types):
        return findings

    name = data.get("name")
    if not name or not str(name).strip():
        return findings

    same_as = data.get("sameAs")
    has_same_as = bool(same_as) and (
        (isinstance(same_as, str) and same_as.strip())
        or (isinstance(same_as, list) and any(str(s).strip() for s in same_as))
    )

    has_id = bool(str(data.get("@id", "")).strip())

    if not has_same_as and not has_id:
        findings.append({
            "id": f"SD009-{index}",
            "title": "Entity has no disambiguating identifier (sameAs/@id)",
            "severity": "medium",
            "evidence": (
                f"Entity '{name}' (type: {', '.join(schema_types)}) has no "
                f"'sameAs' links (e.g. Wikidata, Wikipedia, official social "
                f"profiles) and no stable '@id'. If the name is shared by "
                f"other entities, AI assistants and search engines have no "
                f"reliable way to disambiguate this brand/person from "
                f"unrelated namesakes."
            ),
            "suggested_action": {
                "summary": (
                    "Add a 'sameAs' array linking to authoritative external "
                    "profiles (Wikidata, Wikipedia, LinkedIn, official social "
                    "accounts) and/or a stable '@id' URI to disambiguate this "
                    "entity from others sharing the same name."
                ),
                "priority": "medium",
            },
        })

    return findings


def check_duplicate_ids(entities):
    """Flag distinct entities that reuse the same @id, and entities that
    share a name but declare conflicting @id values (both are signals of
    inconsistent/broken entity identity across the page)."""
    findings = []

    seen_ids = {}
    for i, entity in enumerate(entities):
        entity_id = str(entity.get("@id", "")).strip()
        if not entity_id:
            continue

        if entity_id in seen_ids:
            prev_index, prev_entity = seen_ids[entity_id]
            prev_name = prev_entity.get("name")
            this_name = entity.get("name")
            if prev_name and this_name and str(prev_name) != str(this_name):
                findings.append({
                    "id": f"SD010-{i}",
                    "title": "Duplicate @id used by conflicting entities",
                    "severity": "high",
                    "evidence": (
                        f"@id '{entity_id}' is used by both entity "
                        f"'{prev_name}' (block {prev_index}) and "
                        f"'{this_name}' (block {i}) — these should be "
                        f"distinct entities with distinct @id values."
                    ),
                    "suggested_action": {
                        "summary": (
                            "Give each distinct entity its own unique @id."
                        ),
                        "priority": "high",
                    },
                })
        else:
            seen_ids[entity_id] = (i, entity)

    return findings


def audit_structured_data(html: str, url: str) -> list:
    """Run all structured-data checks against a page and return a list of
    findings dicts."""
    soup = BeautifulSoup(html, "html.parser")
    visible_text = _get_visible_text(html)
    findings = []

    json_ld_blocks = soup.find_all("script", attrs={"type": "application/ld+json"})

    if not json_ld_blocks:
        findings.append({
            "id": "SD001",
            "title": "No structured data detected",
            "severity": "high",
            "evidence": "No JSON-LD structured data was found on the page.",
            "suggested_action": {
                "summary": "Add relevant Schema.org structured data.",
                "priority": "high",
            },
        })
        return findings

    # value -> (value, block_index) so conflict findings can name where the
    # first occurrence came from.
    structured_values = {}
    all_entities = []

    for index, block in enumerate(json_ld_blocks):
        raw = block.string
        if not raw or not raw.strip():
            # Fall back for content wrapped in comments / split across
            # multiple text nodes, where .string returns None.
            raw = block.get_text()

        if not raw or not raw.strip():
            findings.append({
                "id": f"SD002-empty-{index}",
                "title": "Empty JSON-LD block",
                "severity": "medium",
                "evidence": "A JSON-LD <script> tag was found with no content.",
                "suggested_action": {
                    "summary": "Remove the empty block or populate it with valid JSON-LD.",
                    "priority": "medium",
                },
            })
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            findings.append({
                "id": f"SD002-invalid-{index}",
                "title": "Invalid JSON-LD structured data",
                "severity": "high",
                "evidence": "A JSON-LD block could not be parsed as valid JSON.",
                "suggested_action": {
                    "summary": "Fix the malformed JSON-LD.",
                    "priority": "high",
                },
            })
            continue

        # Flatten @graph wrappers / top-level arrays into individual
        # entities so every entity actually gets checked, not just the
        # outer wrapper object.
        entities = _iter_entities(data)

        if not entities:
            # Valid JSON, but not a dict/list/@graph we can meaningfully
            # check (e.g. a bare string or number).
            findings.append({
                "id": f"SD002-unexpected-{index}",
                "title": "Unexpected JSON-LD structure",
                "severity": "medium",
                "evidence": (
                    "A JSON-LD block parsed successfully but did not contain "
                    "an object, an array of objects, or an @graph list."
                ),
                "suggested_action": {
                    "summary": "Verify the JSON-LD follows standard Schema.org structure.",
                    "priority": "medium",
                },
            })
            continue

        for entity in entities:
            all_entities.append(entity)

            # Cross-block conflict detection.
            for key in ["name", "url", "datePublished", "dateModified"]:
                if key in entity:
                    value = str(entity[key]).strip()

                    if key in structured_values:
                        previous_value, previous_index = structured_values[key]
                        if previous_value != value:
                            findings.append({
                                "id": f"SD005-{index}",
                                "title": f"Conflicting structured data: {key}",
                                "severity": "high",
                                "evidence": (
                                    f"Block {index} contains '{key}'='{value}', "
                                    f"which conflicts with '{previous_value}' "
                                    f"found earlier in block {previous_index}."
                                ),
                                "suggested_action": {
                                    "summary": (
                                        f"Ensure all structured-data blocks use "
                                        f"the same authoritative '{key}' value."
                                    ),
                                    "priority": "high",
                                },
                            })
                    else:
                        structured_values[key] = (value, index)

            findings.extend(check_visible_content_conflicts(visible_text, entity, index))
            findings.extend(check_schema_type(visible_text, entity, index))
            findings.extend(check_required_properties(entity, index))
            findings.extend(check_entity_ambiguity(entity, index))

            if "@context" not in entity:
                findings.append({
                    "id": f"SD003-{index}",
                    "title": "Structured data missing @context",
                    "severity": "medium",
                    "evidence": "A JSON-LD object was found without an @context property.",
                    "suggested_action": {
                        "summary": "Add the appropriate Schema.org @context.",
                        "priority": "medium",
                    },
                })

            if "@type" not in entity:
                findings.append({
                    "id": f"SD004-{index}",
                    "title": "Structured data missing @type",
                    "severity": "medium",
                    "evidence": "A JSON-LD object was found without an @type property.",
                    "suggested_action": {
                        "summary": "Specify the appropriate Schema.org type.",
                        "priority": "medium",
                    },
                })

    findings.extend(check_duplicate_ids(all_entities))

    return findings


if __name__ == "__main__":
    with open("test.html", "r", encoding="utf-8") as f:
        html = f.read()

    results = audit_structured_data(html, "https://example.com")

    if results:
        print(json.dumps({"status": "issues_found", "findings": results}, indent=2))
    else:
        print(json.dumps({
            "status": "pass",
            "message": "No structured data issues detected.",
            "findings": [],
        }, indent=2))