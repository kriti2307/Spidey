const { createFinding } = require("./finding");

function runHtmlChecks(page) {
    const findings = [];
    const data = page.pageData;

    if (
        !data ||
        data.error ||
        !page.success ||
        (page.status && page.status >= 400)
    ) {
        return findings;
    }
    const hiddenWordCount = data.hiddenText
    ? data.hiddenText
        .join(" ")
        .split(/\s+/)
        .filter(Boolean)
        .length
    : 0;

    if (hiddenWordCount >= 50) {
        findings.push(
            createFinding({
                type: "html-extraction",
                severity: "medium",
                url: page.requestedUrl,
                title:
                    "Substantial content is hidden from the visible page",
                evidence: [
                    `${hiddenWordCount} words were found inside hidden elements.`
                ],
                recommendation:
                    "Keep important information in visible, readable HTML instead of hiding it from users."
            })
        );
    }

    // 1. Missing title
    if (!data.title) {
        findings.push(
            createFinding({
                type: "html-extraction",
                severity: "medium",
                url: page.requestedUrl,
                title: "Page has no title",
                evidence: [
                    "No <title> element was found."
                ],
                recommendation:
                    "Add a clear, descriptive title to the page."
            })
        );
    }

    if (data.titleCount > 1) {
        findings.push(
            createFinding({
                type: "html-extraction",
                severity: "low",
                url: page.requestedUrl,
                title: "Page contains multiple title elements",
                evidence: [
                    `${data.titleCount} <title> elements were found.`
                ],
                recommendation:
                    "Use a single <title> element that clearly describes the page."
            })
        );
    }

    // 2. Missing H1
    const h1Count = data.headings.filter(
        heading => heading.level === 1
    ).length;

    if (
    h1Count === 0 &&
    data.wordCount >= 100 &&
    data.headings.length >= 2
    ) {
        findings.push(
            createFinding({
                type: "html-extraction",
                severity: "medium",
                url: page.requestedUrl,
                title: "Page lacks a primary heading",
                evidence: [
                    "No <h1> element was found.",
                    `${data.wordCount} visible words were extracted.`,
                    `${data.headings.length} other headings were found.`
                ],
                recommendation:
                    "Add a clear primary heading that identifies the page's main topic."
            })
        );
    }

    // 3. Missing canonical URL
    if (!data.canonical) {
        findings.push(
            createFinding({
                type: "html-extraction",
                severity: "low",
                url: page.requestedUrl,
                title: "Page has no canonical URL",
                evidence: [
                    "No <link rel=\"canonical\"> element was found."
                ],
                recommendation:
                    "Add a canonical URL that identifies the preferred version of the page."
            })
        );
    }

    // 4. Canonical URL points elsewhere
    if (data.canonical) {
        try {
            const pageUrl = new URL(page.requestedUrl);
            const canonicalUrl = new URL(
                data.canonical,
                page.requestedUrl
            );

            if (canonicalUrl.origin !== pageUrl.origin) {
                findings.push(
                    createFinding({
                        type: "html-extraction",
                        severity: "medium",
                        url: page.requestedUrl,
                        title: "Canonical URL points to another domain",
                        evidence: [
                            `Canonical URL: ${canonicalUrl.href}`
                        ],
                        recommendation:
                            "Use a canonical URL on the same domain unless cross-domain canonicalization is intentional."
                    })
                );
            } else if (
                canonicalUrl.pathname !== pageUrl.pathname ||
                canonicalUrl.search !== pageUrl.search
            ) {
                findings.push(
                    createFinding({
                        type: "html-extraction",
                        severity: "medium",
                        url: page.requestedUrl,
                        title: "Canonical URL points to a different page",
                        evidence: [
                            `Page URL: ${pageUrl.href}`,
                            `Canonical URL: ${canonicalUrl.href}`
                        ],
                        recommendation:
                            "Set the canonical URL to the preferred version of this page."
                    })
                );
            }
        } catch {
            findings.push(
                createFinding({
                    type: "html-extraction",
                    severity: "medium",
                    url: page.requestedUrl,
                    title: "Canonical URL is invalid",
                    evidence: [
                        `Canonical URL: ${data.canonical}`
                    ],
                    recommendation:
                        "Use a valid absolute or page-resolvable canonical URL."
                })
            );
        }
    }
    // Meta description
    if (!data.description) {
        findings.push(
            createFinding({
                type: "html-extraction",
                severity: "low",
                url: page.requestedUrl,
                title: "Page has no meta description",
                evidence: [
                    "No meta description was found."
                ],
                recommendation:
                    "Add a concise meta description that summarizes the page's main content."
            })
        );
    }

    if (data.descriptionCount > 1) {
        findings.push(
            createFinding({
                type: "html-extraction",
                severity: "low",
                url: page.requestedUrl,
                title: "Page contains multiple meta descriptions",
                evidence: [
                    `${data.descriptionCount} meta description elements were found.`
                ],
                recommendation:
                    "Use a single meta description that accurately summarizes the page."
            })
        );
    }

    // 5. Very little visible text
    if (data.wordCount < 20 && data.headings.length === 0) {
        findings.push(
            createFinding({
                type: "html-extraction",
                severity: "low",
                url: page.requestedUrl,
                title: "Page exposes very little visible text",
                evidence: [
                    `Only ${data.wordCount} visible words were extracted.`
                ],
                recommendation:
                    "Ensure important page information is exposed as readable HTML text."
            })
        );
    }

    // 6. Images without alt text
    const imagesWithoutAlt = data.images.filter(
        image =>
            !image.hasAlt &&
            image.role !== "presentation" &&
            !image.ariaHidden
    );

    if (imagesWithoutAlt.length > 0) {
        findings.push(
            createFinding({
                type: "html-extraction",
                severity: "low",
                url: page.requestedUrl,
                title: "Images are missing alternative text",
                evidence: [
                    `${imagesWithoutAlt.length} image(s) are missing an alt attribute.`
                ],
                recommendation:
                    "Add alt text to informative images. Decorative images should use alt=\"\"."
            })
        );
    }

    return findings;
}

module.exports = {
    runHtmlChecks
};