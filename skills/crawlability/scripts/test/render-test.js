const { chromium } = require("playwright");
const fs = require("fs");

async function main() {

    const browser = await chromium.launch({
        headless: true
    });

    const page = await browser.newPage();

    const filePath = "file://" + process.cwd() + "/test-page.html";

    // Get the raw HTML directly from the file
    const rawHtml = fs.readFileSync("test-page.html", "utf-8");

    // Load the page in a real browser
    await page.goto(filePath);

    // Get the HTML after JavaScript execution
    const renderedHtml = await page.content();

    console.log("Raw HTML length:", rawHtml.length);
    console.log("Rendered HTML length:", renderedHtml.length);

    await browser.close();
}

main();