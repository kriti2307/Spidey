const { chromium } = require("playwright");
const QUIET = process.env.CRAWL_JSON === "1";

function log(...args) {
    if (!QUIET) {
        console.log(...args);
    }
}

const {
    normalizeUrl,
    isSameOrigin,
    isProbablyCrawlableUrl
} = require("./url-utils")

const {
    getRobotsRules,
    isAllowed,
    getCrawlDelay
} = require("./robots");

const {
    loadPage
} = require("./page-loader");

const {
    discoverSitemap
} = require("./sitemap");

const {
    detectRenderGap
} = require("../renderer/render-gap");

const {
    extractPageData
} = require("../extractor/html-extractor");

const {
    runRenderChecks
} = require("../audit/render-checks");

const {
    runCrawlChecks
} = require("../audit/crawl-checks");

const {
    runHtmlChecks
} = require("../audit/html-checks");

const {
    createRateLimiter
} = require("./rate-limit");


async function crawlWebsite(startUrl, maxPages = 20) {

    const browser = await chromium.launch({
        headless: true
    });

    const page = await browser.newPage();

    // robots.txt
    const robotsResult = await getRobotsRules(startUrl);

const robots = robotsResult.rules;
const robotsText = robotsResult.text;

const crawlDelay = getCrawlDelay(robots);

    const waitBeforeRequest = createRateLimiter(
    crawlDelay > 0 ? crawlDelay : 100
);

    // sitemap.xml
    const sitemapUrls = await discoverSitemap(
    startUrl,
    robotsText
);

    log("Sitemap discovered:", sitemapUrls.length);

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
            if (!queue.includes(normalized)) {
    queue.push(normalized);
}
        }
    }

    const visited = new Set();
    const results = [];
    const blockedUrls = [];

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

            log(
                "Blocked by robots.txt:",
                currentUrl
            );

            blockedUrls.push(currentUrl);

            continue;
        }

        visited.add(currentUrl);

        log(
            `[${visited.size}/${maxPages}]`,
            currentUrl
        );

        // Load page
        await waitBeforeRequest();
        const result = await loadPage(
            page,
            currentUrl
        );

        log(
            "Redirects:",
            result.redirects
        );

        let renderGap = null;

        if (result.success) {
            try {
                renderGap = await detectRenderGap(
                    page,
                    currentUrl,
                    result.rawHtml
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

        let html = null;

        if (result.success) {
            try {
                html = await page.content();
            } catch (error) {
                html = null;
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
            url: result.requestedUrl,
            finalUrl: result.finalUrl,
            status: result.status,
            success: result.success,
            redirects: result.redirects,
            error: result.error,
            errorType: result.errorType,

            html,

            pageData,
            renderGap,

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

            log(
                "Link extraction failed:",
                error.message
            );
        }
    }

    await browser.close();

    return {
        site: startUrl,
        sitemapUrls,
        blockedUrls,
        pages: results
    };
}


module.exports = {
    crawlWebsite
};

if (require.main === module) {
    const startUrl = process.argv[2];

    if (!startUrl) {
        console.error("Usage: node crawler.js <url> [maxPages]");
        process.exit(1);
    }

    const maxPages = Number(process.argv[3]) || 20;

    crawlWebsite(startUrl, maxPages)
        .then(audit => {
            console.log(JSON.stringify(audit));
        })
        .catch(error => {
            console.error(error);
            process.exit(1);
        });
}