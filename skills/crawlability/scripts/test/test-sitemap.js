const { discoverSitemap } = require("./src/crawler/sitemap");

async function main() {
    const urls = await discoverSitemap("https://www.wikipedia.org");

    console.log("Sitemap URLs:", urls.slice(0, 20));
    console.log("Count:", urls.length);
}

main();