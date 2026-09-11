const { chromium } = require("playwright");

const {
    loadPage
} = require("../crawler/page-loader");

async function main() {

    const browser = await chromium.launch({
        headless: true
    });

    const page = await browser.newPage();

    const result = await loadPage(
        page,
        "https://example.com"
    );

    console.log(
        JSON.stringify(result, null, 2)
    );

    await browser.close();
}

main();