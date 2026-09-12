const http = require("http");
const fs = require("fs");
const path = require("path");

const BASE_DIR = __dirname;

function readFile(filename) {
    return fs.readFileSync(
        path.join(BASE_DIR, filename),
        "utf8"
    );
}

const server = http.createServer((req, res) => {

    // JS rendering test
    if (req.url === "/js-test.html") {
        const html = readFile("js-test.html");

        res.writeHead(200, {
            "Content-Type": "text/html"
        });

        res.end(html);
        return;
    }

    // Non-text audit test
    if (req.url === "/crawl-test-nontext.html") {
        const html = readFile("crawl-test-nontext.html");

        res.writeHead(200, {
            "Content-Type": "text/html"
        });

        res.end(html);
        return;
    }

    // Main crawlability test
    if (req.url === "/crawl-test.html") {
        const html = readFile("crawl-test.html");

        res.writeHead(200, {
            "Content-Type": "text/html"
        });

        res.end(html);
        return;
    }

    // 404 test
    if (req.url === "/missing-page") {
        res.writeHead(404, {
            "Content-Type": "text/html"
        });

        res.end("Page Not Found");
        return;
    }

    // Normal page
    if (req.url === "/normal-page") {
        res.writeHead(200, {
            "Content-Type": "text/html"
        });

        res.end(`
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="description" content="Learn more about our company and services.">
            <link rel="canonical" href="http://localhost:3000/normal-page">
        </head>
        <body>
            <h1>Normal Page</h1>
            <p>This is a normal page.</p>
        </body>
        </html>
        `);

        return;
    }

    // Duplicate title test
    if (req.url === "/duplicate-title") {
        res.writeHead(200, {
            "Content-Type": "text/html"
        });

        res.end(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>First Title</title>
            <title>Second Title</title>

            <meta name="description"
                content="Test page for duplicate title detection.">

            <link
                rel="canonical"
                href="http://localhost:3000/duplicate-title">
        </head>

        <body>
            <h1>Duplicate Title Test</h1>

            <p>
                This page is used to test multiple title detection.
            </p>
        </body>
        </html>
        `);

        return;
    }

    // Duplicate description test
    if (req.url === "/duplicate-description") {
        res.writeHead(200, {
            "Content-Type": "text/html"
        });

        res.end(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>First Title</title>

            <meta
                name="description"
                content="Test page for duplicate description detection.">

            <meta
                name="description"
                content="Test page for duplicate description detection.">

            <link
                rel="canonical"
                href="http://localhost:3000/duplicate-description">
        </head>

        <body>
            <h1>Duplicate Description Test</h1>

            <p>
                This page is used to test multiple description detection.
            </p>
        </body>
        </html>
        `);

        return;
    }

    // JS UI rendering test
    if (req.url === "/js-ui-test.html") {
        const html = readFile("js-ui-test.html");

        res.writeHead(200, {
            "Content-Type": "text/html"
        });

        res.end(html);
        return;
    }

    // Robots.txt
    if (req.url === "/robots.txt") {
        const robots = readFile("robots.txt");

        res.writeHead(200, {
            "Content-Type": "text/plain"
        });

        res.end(robots);
        return;
    }

    // Unknown route
    res.writeHead(404, {
        "Content-Type": "text/plain"
    });

    res.end("Not Found");
});

server.listen(3000, () => {
    console.log("Server running at http://localhost:3000");
});