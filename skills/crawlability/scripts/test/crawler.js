const { chromium } = require("playwright");

const {
    normalizeUrl,
    isSameOrigin,
    isProbablyCrawlableUrl
} = require("./src/crawler/url-utils");

const {
    getRobotsRules,
    isAllowed,
    getCrawlDelay
} = require("./src/crawler/robots");

const {
    loadPage
} = require("./src/crawler/page-loader");

const {
    discoverSitemap
} = require("./src/crawler/sitemap");

const {
    detectRenderGap
} = require("./src/renderer/render-gap");

const {
    extractPageData
} = require("./src/extractor/html-extractor");

const {
    runRenderChecks
} = require("./src/audit/render-checks");

const {
    runCrawlChecks
} = require("./src/audit/crawl-checks");

const {
    runHtmlChecks
} = require("./src/audit/html-checks");

const {
    createRateLimiter
} = require("./src/crawler/rate-limit");


async function crawlWebsite(startUrl, maxPages = 20) {

    const browser = await chromium.launch({
        headless: true
    });

    const page = await browser.newPage();

    // robots.txt
    const robots = await getRobotsRules(startUrl);
    const crawlDelay = getCrawlDelay(robots);

    const waitBeforeRequest = createRateLimiter(
        Math.max(500, crawlDelay)
    );

    // sitemap.xml
    const sitemapUrls = await discoverSitemap(startUrl);

    console.log("Sitemap discovered:", sitemapUrls.length);

    // Initial queue
    const queue = [normalizeUrl(startUrl)];

    // Add sitemap URLs
    for (const url of sitemapUrls) {

        const normalized = normalizeUrl(url);

        if (
            normalized &&
            isSameOrigin(normalized, startUrl) &&
            isProbablyCrawlableUrl(normalized)
        ) {
            queue.push(normalized);
        }
    }

    const visited = new Set();
    const results = [];

    while (
        queue.length > 0 &&
        visited.size < maxPages
    ) {

        const currentUrl = normalizeUrl(
            queue.shift()
        );

        if (!currentUrl) continue;

        if (visited.has(currentUrl)) continue;

        // robots.txt
        if (!isAllowed(robots, currentUrl)) {

            console.log(
                "Blocked by robots.txt:",
                currentUrl
            );

            continue;
        }

        visited.add(currentUrl);

        console.log(
            `[${visited.size}/${maxPages}]`,
            currentUrl
        );

        // Load page
        await waitBeforeRequest();
        const result = await loadPage(
            page,
            currentUrl
        );

        console.log(
            "Redirects:",
            result.redirects
        );

        let renderGap = null;

        if (result.success) {
            try {
                renderGap = await detectRenderGap(
                    page,
                    currentUrl
                );
            } catch (error) {
                renderGap = {
                    detected: false,
                    error: error.message
                };
            }
        }

        let pageData = null;

        if (result.success) {
            try {
                pageData = await extractPageData(
                    page,
                    currentUrl
                );
            } catch (error) {
                pageData = {
                    error: error.message
                };
            }
        }

        const crawlFindings = runCrawlChecks(result);

        const renderFindings = runRenderChecks({
            ...result,
            renderGap
        });

        const htmlFindings = runHtmlChecks({
            ...result,
            pageData
        });

        results.push({
            ...result,
            renderGap,
            pageData,
            findings: [
                ...crawlFindings,
                ...renderFindings,
                ...htmlFindings
            ]
        });

        // Don't extract links if page failed
        if (!result.success) {
            continue;
        }

        // Find internal links
        try {

            const links = await page
                .locator("a")
                .evaluateAll(
                    anchors =>
                        anchors.map(
                            anchor => anchor.href
                        )
                );

            for (const link of links) {

                if (!isSameOrigin(
                    link,
                    startUrl
                )) {
                    continue;
                }

                const normalized =normalizeUrl(link);

                if (
                    normalized &&
                    isProbablyCrawlableUrl(normalized) &&
                    !visited.has(normalized)
                ) {
                    queue.push(normalized);
                }
            }

        } catch (error) {

            console.log(
                "Link extraction failed:",
                error.message
            );
        }
    }

    await browser.close();

    return results;
}


async function main() {

    const results = await crawlWebsite(
        "http://localhost:3000/crawl-test.html",
        10
    );

    console.log("\nCrawl complete");
    console.log(
        "Pages crawled:",
        results.length
    );

    for (const page of results) {
    console.log("\n==============================");
    console.log("URL:", page.requestedUrl);
    console.log("Status:", page.status);
    console.log("Final URL:", page.finalUrl);

    console.log("\nFindings:");

    if (page.findings.length === 0) {
        console.log("No findings");
    } else {
        console.log(
            JSON.stringify(page.findings, null, 2)
        );
    }
}
}

main();