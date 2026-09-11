const { request } = require("playwright");
const cheerio = require("cheerio");

async function detectRenderGap(page, url) {

    // -----------------------------
    // 1. Fetch RAW HTML
    // -----------------------------

    const context = await request.newContext();

    const response = await context.get(url);

    if (!response.ok()) {
        await context.dispose();

        return {
            url,
            detected: false,
            error: `HTTP ${response.status()}`
        };
    }

    const rawHtml = await response.text();

    await context.dispose();

    const raw = extractRawContent(rawHtml,url);

    

function extractRawContent(html, baseUrl) {
    const $ = cheerio.load(html);

    $("script, style, noscript, template").remove();

    $("[hidden]").remove();
    $("[aria-hidden='true']").remove();
    $("[style*='display:none']").remove();
    $("[style*='display: none']").remove();
    $("[style*='visibility:hidden']").remove();
    $("[style*='visibility: hidden']").remove();

    const text = $("body")
        .text()
        .replace(/\s+/g, " ")
        .trim();

    const headings = $("h1, h2, h3")
        .map((_, element) =>
            $(element)
                .text()
                .replace(/\s+/g, " ")
                .trim()
        )
        .get()
        .filter(Boolean);

    const links = $("a[href]")
        .map((_, element) => {
            const href = $(element).attr("href");

            try {
                return new URL(href, baseUrl).href;
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


    // -----------------------------
    // 2. Render with browser
    // -----------------------------

    await page.goto(url, {
        waitUntil: "domcontentloaded",
        timeout: 30000
    });

    // Allow delayed JS to execute
    await page.waitForFunction(() => {
        const body = document.body;

        if (!body) return false;

        const text = body.innerText.trim();

        const headings = document.querySelectorAll(
            "h1, h2, h3"
        ).length;

        const links = document.querySelectorAll(
            "a[href]"
        ).length;

        return (
            text.length >= 50 ||
            headings > 0 ||
            links > 2
        );
    }, {
        timeout: 5000
    }).catch(() => {});

const rendered = await page.evaluate(() => {
    return {
        text: document.body?.innerText || "",

        headings: Array.from(
            document.querySelectorAll("h1, h2, h3")
        )
            .map(el => el.innerText.trim())
            .filter(Boolean),

        links: Array.from(
            document.querySelectorAll("a[href]")
        )
            .map(a => ({
                text: a.innerText.trim(),
                href: a.href
            }))
            .filter(link => link.href)
    };
});


// Find content that appeared only after JS rendering
const newHeadings = findNewItems(
    raw.headings,
    rendered.headings
);

const newLinks = findNewItems(
    raw.links,
    rendered.links.map(link => link.href)
);


const textAdded =
    rendered.text.length - raw.text.length;

const headingsAdded =
    rendered.headings.length - raw.headings.length;

const linksAdded =
    rendered.links.length - raw.links.length;

    // -----------------------------
    // 4. Evidence
    // -----------------------------

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

        detected: evidence.length > 0,

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
}


function extractRawContent(html) {

    // Remove JS and CSS
    const cleaned = html
        .replace(/<script[\s\S]*?<\/script>/gi, "")
        .replace(/<style[\s\S]*?<\/style>/gi, "");


    // Extract text
    const text = cleaned
        .replace(/<[^>]+>/g, " ")
        .replace(/\s+/g, " ")
        .trim();


    // Extract headings
    const headings =
        cleaned.match(
            /<h[1-3][^>]*>[\s\S]*?<\/h[1-3]>/gi
        ) || [];


    // Extract links
    const links =
        cleaned.match(
            /<a\s[^>]*href=["'][^"']+["']/gi
        ) || [];


    return {
        text,
        headings,
        links
    };
}

function findNewItems(rawItems, renderedItems) {
    const rawSet = new Set(
        rawItems.map(item => item.toLowerCase().trim())
    );

    return renderedItems.filter(
        item => !rawSet.has(item.toLowerCase().trim())
    );
}


module.exports = {
    detectRenderGap
};