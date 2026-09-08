import json
from bs4 import BeautifulSoup

def check_visible_content_conflicts(soup, data, index):
    findings = []

    if not isinstance(data, dict):
        return findings

    # Extract visible text from the page
    visible_text = soup.get_text(" ", strip=True).lower()

    fields_to_check = ["name", "description", "telephone"]

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
                    "priority": "medium"
                }
            })

    return findings


def audit_structured_data(html: str, url: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    findings = []

    # Finding all JSON-LD blocks
    json_ld_blocks = soup.find_all(
        "script",
        attrs={"type": "application/ld+json"}
    )

    if not json_ld_blocks:
        findings.append({
            "id": "SD001",
            "title": "No structured data detected",
            "severity": "medium",
            "evidence": "No JSON-LD structured data was found on the page.",
            "suggested_action": {
                "summary": "Add relevant Schema.org structured data.",
                "priority": "medium"
            }
        })

        return findings

    valid_blocks = 0
    structured_values = {}

    for index, block in enumerate(json_ld_blocks):
        raw = block.string

        if not raw:
            continue

        try:
            data = json.loads(raw)
            valid_blocks += 1
                        # Look for conflicting values across JSON-LD blocks
            if isinstance(data, dict):
                for key in ["name", "url", "datePublished", "dateModified"]:
                    if key in data:
                        value = str(data[key]).strip()

                        if key in structured_values:
                            previous = structured_values[key]

                            if previous != value:
                                findings.append({
                                    "id": f"SD005-{index}",
                                    "title": f"Conflicting structured data: {key}",
                                    "severity": "high",
                                    "evidence": (
                                        f"Multiple JSON-LD blocks contain different "
                                        f"values for '{key}': "
                                        f"'{previous}' vs '{value}'."
                                    ),
                                    "suggested_action": {
                                        "summary": (
                                            f"Ensure all structured-data blocks use "
                                            f"the same authoritative '{key}' value."
                                        ),
                                        "priority": "high"
                                    }
                                })
                        else:
                            structured_values[key] = value

        except json.JSONDecodeError:
            findings.append({
                "id": f"SD002-{index}",
                "title": "Invalid JSON-LD structured data",
                "severity": "high",
                "evidence": "A JSON-LD block could not be parsed as valid JSON.",
                "suggested_action": {
                    "summary": "Fix the malformed JSON-LD.",
                    "priority": "high"
                }
            })
            continue

        # Basic Schema.org check
        if isinstance(data, dict):
            findings.extend(
                check_visible_content_conflicts(soup, data, index)
            )

            if "@context" not in data:
                findings.append({
                    "id": f"SD003-{index}",
                    "title": "Structured data missing @context",
                    "severity": "medium",
                    "evidence": "A JSON-LD object was found without an @context property.",
                    "suggested_action": {
                        "summary": "Add the appropriate Schema.org @context.",
                        "priority": "medium"
                    }
                })

            if "@type" not in data:
                findings.append({
                    "id": f"SD004-{index}",
                    "title": "Structured data missing @type",
                    "severity": "medium",
                    "evidence": "A JSON-LD object was found without an @type property.",
                    "suggested_action": {
                        "summary": "Specify the appropriate Schema.org type.",
                        "priority": "medium"
                    }
                })

    return findings


if __name__ == "__main__":
    with open("test.html", "r", encoding="utf-8") as f:
        html = f.read()

    results = audit_structured_data(
        html,
        "https://example.com"
    )

    print(json.dumps(results, indent=2))