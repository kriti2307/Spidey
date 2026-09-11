const { chromium } = require("playwright");

async function main() {
    const browser = await chromium.launch({
        headless: true
    });

    const page = await browser.newPage();

    await page.goto("https://example.com");

    console.log("Title:", await page.title());

    console.log("URL:", page.url());

    console.log("HTML:");

    const html = await page.content();

    console.log(html);

    await browser.close();
}

main();