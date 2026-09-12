const { crawlWebsite } = require("../crawler/crawler");

async function main() {
    const audit = await crawlWebsite(
        "http://localhost:3000/crawl-test-nontext.html",
        10
    );

    console.log(JSON.stringify(audit));
}

main().catch(error => {
    console.error(error);
    process.exit(1);
});