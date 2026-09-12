const { chromium } = require("playwright");
const { extractPageData } = require("../extractor/html-extractor");

async function main() {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    await page.goto("http://localhost:3000/normal-page");

    const data = await extractPageData(
        page,
        "http://localhost:3000/normal-page"
    );
console.log(JSON.stringify({
    title: data.title,
    titleCount: data.titleCount,
    description: data.description,
    descriptionCount: data.descriptionCount,
    canonical: data.canonical,
    headings: data.headings,
    wordCount: data.wordCount,
    links: data.links,
    images: data.images
}, null, 2));

    await browser.close();
}

main();