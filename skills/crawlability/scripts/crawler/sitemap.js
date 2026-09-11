const { XMLParser } = require("fast-xml-parser");

async function fetchText(url) {
    try {
        const response = await fetch(url, {
            signal: AbortSignal.timeout(10000)
        });

        if (!response.ok) return null;

        return await response.text();
    } catch {
        return null;
    }
}

async function getSitemapUrls(startUrl) {
    const origin = new URL(startUrl).origin;

    const robotsUrl = `${origin}/robots.txt`;
    const robotsText = await fetchText(robotsUrl);

    const sitemapUrls = [];

    // 1. Find Sitemap: entries in robots.txt
    if (robotsText) {
        for (const line of robotsText.split("\n")) {
            if (line.toLowerCase().startsWith("sitemap:")) {
                const sitemap = line.substring(8).trim();

                if (sitemap) {
                    sitemapUrls.push(sitemap);
                }
            }
        }
    }

    // 2. Fallback locations
    if (sitemapUrls.length === 0) {
        sitemapUrls.push(
            `${origin}/sitemap.xml`,
            `${origin}/sitemap_index.xml`
        );
    }

    return sitemapUrls;
}

async function parseSitemap(sitemapUrl, visited = new Set()) {
    if (visited.has(sitemapUrl)) {
        return [];
    }

    visited.add(sitemapUrl);

    const xml = await fetchText(sitemapUrl);

    if (!xml) {
        return [];
    }

    try {
        const parser = new XMLParser();
        const data = parser.parse(xml);

        // Normal sitemap
        if (data.urlset?.url) {
            const urls = Array.isArray(data.urlset.url)
                ? data.urlset.url
                : [data.urlset.url];

            return urls
                .map(item => item.loc)
                .filter(Boolean);
        }

        // Sitemap index
        if (data.sitemapindex?.sitemap) {
            const sitemaps = Array.isArray(data.sitemapindex.sitemap)
                ? data.sitemapindex.sitemap
                : [data.sitemapindex.sitemap];

            const results = [];

            for (const sitemap of sitemaps) {
                if (!sitemap.loc) continue;

                const urls = await parseSitemap(
                    sitemap.loc,
                    visited
                );

                results.push(...urls);
            }

            return results;
        }
    } catch (error) {
        console.log("Invalid sitemap:", sitemapUrl);
    }

    return [];
}

async function discoverSitemap(startUrl) {
    const sitemapUrls = await getSitemapUrls(startUrl);

    const allUrls = [];

    for (const sitemapUrl of sitemapUrls) {
        const urls = await parseSitemap(sitemapUrl);
        allUrls.push(...urls);
    }

    // Only keep URLs from the target website
    const origin = new URL(startUrl).origin;

    return [...new Set(
        allUrls.filter(url => {
            try {
                return new URL(url).origin === origin;
            } catch {
                return false;
            }
        })
    )];
}

module.exports = { discoverSitemap };