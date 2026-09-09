import json
from bs4 import BeautifulSoup


def get_link_description(link):
    """
    Get the descriptive name of a link from:
    1. Visible text
    2. Image alt text
    """
    link_text = link.get_text(" ", strip=True)

    if link_text:
        return link_text.strip()

    image_alts = []

    for img in link.find_all("img"):
        alt = img.get("alt")

        if alt:
            alt = alt.strip()

            if alt:
                image_alts.append(alt)

    return " ".join(image_alts)


def audit_non_text(html: str, url: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    findings = []

    # -------------------------
    # PDF checks
    # -------------------------

    pdf_links = soup.find_all(
        "a",
        href=lambda href: href and ".pdf" in href.lower()
    )

    for index, link in enumerate(pdf_links):
        pdf_url = link.get("href")
        link_description = get_link_description(link)
        normalized_description = link_description.lower().strip()

        # PDF may contain information not represented on the webpage
        findings.append({
            "id": f"NT003-{index}",
            "title": "PDF content may not have a webpage text equivalent",
            "type": "warning",
            "severity": "medium",
            "confidence": "medium",
            "evidence": (
                f"The page links to a PDF: "
                f"{link_description or pdf_url}. "
                "Important information may be available only inside the document."
            ),
            "suggested_action": {
                "summary": (
                    "Provide important PDF information as searchable "
                    "webpage text or a concise HTML summary."
                ),
                "priority": "medium"
            }
        })

        # Generic or missing link description
        generic_pdf_text = {
            "",
            "click here",
            "here",
            "download",
            "download pdf",
            "pdf",
            "view",
            "read more",
            "learn more"
        }

        if normalized_description in generic_pdf_text:
            findings.append({
                "id": f"NT004-{index}",
                "title": "PDF link has non-descriptive text",
                "type": "warning",
                "severity": "low",
                "confidence": "high",
                "evidence": (
                    f"The PDF link uses the text "
                    f"'{link_description or '[empty]'}', "
                    "which gives little information about the document."
                ),
                "suggested_action": {
                    "summary": (
                        "Use descriptive link text or descriptive "
                        "image alt text that identifies the document."
                    ),
                    "priority": "low"
                }
            })

    # -------------------------
    # Image checks
    # -------------------------

    images = soup.find_all("img")

    for index, img in enumerate(images):
        alt = img.get("alt")

        # No alt attribute
        if alt is None:
            findings.append({
                "id": f"NT001-{index}",
                "title": "Image may contain information that is not available as text",
                "type": "issue",
                "severity": "medium",
                "confidence": "medium",
                "evidence": (
                    f"Image #{index + 1} has no alt text. "
                    "If the image conveys meaningful information, "
                    "that information may not be available as text."
                ),
                "suggested_action": {
                    "summary": (
                        "Provide a meaningful text alternative when "
                        "the image conveys important information."
                    ),
                    "priority": "medium"
                }
            })

            continue

        alt = alt.strip()

        # Empty alt can legitimately indicate a decorative image
        if alt == "":
            continue

        # Very generic alt text
        generic_alt = {
            "image",
            "photo",
            "picture",
            "graphic",
            "icon",
            "logo"
        }

        if alt.lower() in generic_alt:
            findings.append({
                "id": f"NT002-{index}",
                "title": "Image has a generic text alternative",
                "type": "warning",
                "severity": "low",
                "confidence": "high",
                "evidence": (
                    f"Image #{index + 1} uses the generic alt text "
                    f"'{alt}', which may not communicate its actual "
                    "information."
                ),
                "suggested_action": {
                    "summary": (
                        "Replace generic alt text with a meaningful "
                        "description when the image is informative."
                    ),
                    "priority": "low"
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