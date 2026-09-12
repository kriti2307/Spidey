const { chromium } = require("playwright");

const {
    detectRenderGap
} = require("../renderer/render-gap");

async function main() {
    const browser = await chromium.launch({
        headless: true
    });

    const page = await browser.newPage();

    const url = "http://localhost:3000/js-ui-test.html";

    const result = await detectRenderGap(page, url);

    console.log(
        JSON.stringify(result, null, 2)
    );

    await browser.close();
}

main();