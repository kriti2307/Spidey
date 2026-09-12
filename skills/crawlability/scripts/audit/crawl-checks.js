const { createFinding } = require("./finding");
const { normalizeUrl } = require("../crawler/url-utils");


function checkHttpStatus(page) {

    const findings = [];

    if (!page.success) {
    const errorTitles = {
        "timeout": "Page timed out during crawling",
        "dns-error": "Domain could not be resolved",
        "connection-error": "Connection to page failed",
        "http2-error": "HTTP/2 connection failed during crawling",
        "navigation-error": "Page navigation failed"
    };

    const errorRecommendations = {
        "timeout":
            "Reduce server response time and ensure the page can be reached within a reasonable crawler timeout.",
        "dns-error":
            "Ensure the domain resolves correctly and is reachable by automated crawlers.",
        "connection-error":
            "Ensure the server accepts connections from automated crawlers.",
        "http2-error":
            "Verify HTTP/2 compatibility and ensure the server can reliably serve automated crawler requests.",
        "navigation-error":
            "Ensure the page can be reached successfully by automated crawlers."
        };
        
    const errorType =
        page.errorType || "navigation-error";

    findings.push(
        createFinding({
            type: "crawlability",
            severity:
                errorType === "http2-error"
                    ? "low"
                    : errorType === "navigation-error"
                        ? "medium"
                        : "high",
            url: page.requestedUrl,
            title:
                errorTitles[errorType] ||
                "Page could not be crawled",
            evidence: [
                `Error type: ${errorType}`,
                page.error || "Request failed"
            ],
            recommendation:
                errorRecommendations[errorType] ||
                "Make the page reachable by automated crawlers."
        })
    );

    return findings;
}

    if (page.status >= 400) {

        findings.push(
            createFinding({
                type: "crawlability",
                severity: "high",
                url: page.requestedUrl,
                title: "Page returns an error status",
                evidence: [
                    `HTTP status: ${page.status}`
                ],
                recommendation:
                    "Ensure important pages return a successful HTTP response."
            })
        );
    }

    return findings;
}


function checkRedirects(page) {

    const findings = [];

    if (page.redirects.length >= 3) {

        findings.push(
            createFinding({
                type: "crawlability",
                severity: "medium",
                url: page.requestedUrl,
                title: "Long redirect chain detected",
                evidence: [
                    `${page.redirects.length} redirects occurred before reaching the final URL.`,
                    `Final URL: ${page.finalUrl}`
                ],
                recommendation:
                    "Reduce unnecessary redirect hops and point links directly to the final URL."
            })
        );
    }

    return findings;
}


function checkFinalUrl(page) {
    const findings = [];

    if (!page.success || !page.finalUrl) {
        return findings;
    }

    const requestedNormalized = normalizeUrl(
        page.requestedUrl
    );

    const finalNormalized = normalizeUrl(
        page.finalUrl
    );

    // Ignore harmless URL normalization
    if (requestedNormalized === finalNormalized) {
        return findings;
    }

    findings.push(
        createFinding({
            type: "crawlability",
            severity: "low",
            url: page.requestedUrl,
            title: "URL redirects to another page",
            evidence: [
                `Requested: ${page.requestedUrl}`,
                `Final: ${page.finalUrl}`
            ],
            recommendation:
                "Prefer linking directly to the final destination URL."
        })
    );

    return findings;
}

function runCrawlChecks(page) {

    return [
        ...checkHttpStatus(page),
        ...checkRedirects(page),
        ...checkFinalUrl(page)
    ];
}


module.exports = {
    runCrawlChecks
};