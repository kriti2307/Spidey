import json
from bs4 import BeautifulSoup


def audit_non_text(html: str, url: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    findings = []

    images = soup.find_all("img")

    for index, img in enumerate(images):
        alt = img.get("alt")

        if alt is None:
            findings.append({
                "id": f"NT001-{index}",
                "title": "Image may contain information that is not available as text",
                "severity": "medium",
                "evidence": (
                    f"Image #{index + 1} has no alt text, so any meaningful "
                    "information conveyed by the image may not be available as text."
                ),
                "suggested_action": {
                    "summary": (
                      "Provide a text equivalent when the image contains important "
                      "information needed to understand the page."
                  ),
                    "priority": "medium"
                }
            })

    return findings


if __name__ == "__main__":
    with open("test.html", "r", encoding="utf-8") as f:
        html = f.read()

    results = audit_non_text(
        html,
        "https://example.com"
    )

    if results:
        print(json.dumps({
            "status": "issues_found",
            "findings": results
        }, indent=2))
    else:
        print(json.dumps({
            "status": "pass",
            "message": "No non-text content issues detected.",
            "findings": []
        }, indent=2))