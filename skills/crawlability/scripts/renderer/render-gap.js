const cheerio = require("cheerio");

const RENDER_WAIT_MS = 1000;

/**
 * Detect content that appears only after client-side rendering.
 *
 * IMPORTANT:
 * crawler.js has already navigated to this page.
 * This function must NOT perform another network navigation.
 */
async function detectRenderGap(page, url, rawHtml = null) {
    try {
        // Reuse HTML captured from the initial document response.
        // If unavailable, use the current page content instead of
        // performing another HTTP request.
        const initialHtml = rawHtml || await page.content();

        const raw = extractRawContent(
            initialHtml,
            url
        );

        // Give client-side JavaScript a short opportunity to
        // add meaningful content.
        await new Promise(
            resolve => setTimeout(
                resolve,
                RENDER_WAIT_MS
            )
        );

        const rendered = await page.evaluate(() => {
            return {
                text: document.body?.innerText || "",

                headings: Array.from(
                    document.querySelectorAll(
                        "h1, h2, h3"
                    )
                )
                    .map(el =>
                        el.innerText.trim()
                    )
                    .filter(Boolean),

                links: Array.from(
                    document.querySelectorAll(
                        "a[href]"
                    )
                )
                    .map(a => a.href)
                    .filter(Boolean)
            };
        });

        const newHeadings = findNewItems(
            raw.headings,
            rendered.headings
        );

        const newLinks = findNewItems(
            raw.links,
            rendered.links
        );

        const textAdded =
            rendered.text.length -
            raw.text.length;

        const headingsAdded =
            rendered.headings.length -
            raw.headings.length;

        const linksAdded =
            rendered.links.length -
            raw.links.length;

        const evidence = [];

        if (textAdded >= 100) {
            evidence.push({
                type: "text",
                detail:
                    `${textAdded} additional characters appeared after rendering`
            });
        }

        if (headingsAdded > 0) {
            evidence.push({
                type: "headings",
                detail:
                    `${headingsAdded} additional headings appeared after rendering`
            });
        }

        if (linksAdded > 0) {
            evidence.push({
                type: "links",
                detail:
                    `${linksAdded} additional links appeared after rendering`
            });
        }

        return {
            url,

            detected:
                evidence.length > 0,

            evidence,

            newContent: {
                headings: newHeadings,
                links: newLinks
            },

            raw: {
                textLength: raw.text.length,
                headingCount: raw.headings.length,
                linkCount: raw.links.length
            },

            rendered: {
                textLength: rendered.text.length,
                headingCount: rendered.headings.length,
                linkCount: rendered.links.length
            },

            difference: {
                textAdded,
                headingsAdded,
                linksAdded
            }
        };

    } catch (error) {
        return {
            url,
            detected: false,
            evidence: [],
            error: error.message
        };
    }
}


function extractRawContent(
    html,
    baseUrl
) {
    const $ = cheerio.load(html);

    $(
        "script, style, noscript, template"
    ).remove();

    $("[hidden]").remove();

    $(
        "[aria-hidden='true']"
    ).remove();

    $(
        "[style*='display:none']"
    ).remove();

    $(
        "[style*='display: none']"
    ).remove();

    $(
        "[style*='visibility:hidden']"
    ).remove();

    $(
        "[style*='visibility: hidden']"
    ).remove();

    const text = $("body")
        .text()
        .replace(/\s+/g, " ")
        .trim();

    const headings = $(
        "h1, h2, h3"
    )
        .map((_, element) =>
            $(element)
                .text()
                .replace(/\s+/g, " ")
                .trim()
        )
        .get()
        .filter(Boolean);

    const links = $(
        "a[href]"
    )
        .map((_, element) => {
            const href =
                $(element).attr("href");

            try {
                return new URL(
                    href,
                    baseUrl
                ).href;
            } catch {
                return null;
            }
        })
        .get()
        .filter(Boolean);

    return {
        text,
        headings,
        links
    };
}


function findNewItems(
    rawItems,
    renderedItems
) {
    const rawSet = new Set(
        rawItems.map(
            item =>
                item
                    .toLowerCase()
                    .trim()
        )
    );

    return renderedItems.filter(
        item =>
            !rawSet.has(
                item
                    .toLowerCase()
                    .trim()
            )
    );
}


module.exports = {
    detectRenderGap
};