const { normalizeUrl } = require("./url-utils");

const urls = [
    "https://example.com/about/",
    "https://example.com/about#team",
    "https://example.com/products/",
    "https://example.com/"
];

for (const url of urls) {
    console.log(url);
    console.log("→", normalizeUrl(url));
    console.log();
}