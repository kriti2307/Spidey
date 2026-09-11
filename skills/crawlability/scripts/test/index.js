const url = "https://example.com";

async function main() {
    const response = await fetch(url);

    console.log("Status:", response.status);

    const html = await response.text();

    const titleMatch = html.match(/<title[^>]*>(.*?)<\/title>/i);

    const title = titleMatch ? titleMatch[1] : null;

    console.log("Title:", title);
}

main();