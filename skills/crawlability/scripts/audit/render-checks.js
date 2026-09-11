const { createFinding } = require("./finding");

function runRenderChecks(page) {
    const findings = [];

    const gap = page.renderGap;

    if (!gap || !gap.detected) {
        return findings;
    }

    const {
        textAdded,
        headingsAdded,
        linksAdded
    } = gap.difference;

    /*
     * Strong evidence:
     * Large amount of text appears only after JS,
     * or multiple meaningful headings appear.
     */
    if (
        textAdded >= 500 ||
        headingsAdded >= 2
    ) {
        findings.push(
            createFinding({
                type: "js-rendering",
                severity: "high",
                url: page.requestedUrl,
                title:
                    "Important page content depends on JavaScript",
                evidence: gap.evidence.map(
                    item => item.detail
                ),
                recommendation:
                    "Ensure important content is available in the initial HTML response or provide reliable server-side rendering."
            })
        );

        return findings;
    }

    /*
     * Medium confidence:
     * A meaningful amount of text OR one new heading
     * appears after rendering.
     */
    if (
        textAdded >= 200 ||
        headingsAdded >= 1
    ) {
        findings.push(
            createFinding({
                type: "js-rendering",
                severity: "medium",
                url: page.requestedUrl,
                title:
                    "Important content appears after JavaScript rendering",
                evidence: gap.evidence.map(
                    item => item.detail
                ),
                recommendation:
                    "Ensure important page content is available in the initial HTML response rather than relying entirely on client-side rendering."
            })
        );
    }

    /*
     * A small number of dynamically added links alone
     * is not enough evidence of a problem.
     */

    return findings;
}

module.exports = {
    runRenderChecks
};