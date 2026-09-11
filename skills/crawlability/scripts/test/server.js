const http = require("http");
const fs = require("fs");

const server = http.createServer((req, res) => {
    if (req.url === "/js-test.html") {
        const html = fs.readFileSync("js-test.html", "utf8");

        res.writeHead(200, {
            "Content-Type": "text/html"
        });

        res.end(html);
        return;
    }
    if (req.url === "/crawl-test.html") {
    const html = fs.readFileSync(
        "crawl-test.html",
        "utf8"
    );

    res.writeHead(200, {
        "Content-Type": "text/html"
    });

    res.end(html);
    return;
}

if (req.url === "/missing-page") {
    res.writeHead(404, {
        "Content-Type": "text/html"
    });

    res.end("Page Not Found");
    return;
}

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

            <meta name="description" content="Test page for duplicate title detection.">
            <link rel="canonical" href="http://localhost:3000/duplicate-title">
        </head>

        <body>
            <h1>Duplicate Title Test</h1>
            <p>This page is used to test multiple title detection.</p>
        </body>
        </html>
    `);

    return;
}
if (req.url === "/duplicate-description") {
    res.writeHead(200, {
        "Content-Type": "text/html"
    });

    res.end(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>First Title</title>

            <meta name="description" content="Test page for duplicate description detection.">
            <meta name="description" content="Test page for duplicate description detection.">
            <link rel="canonical" href="http://localhost:3000/duplicate-description">
        </head>

        <body>
            <h1>Duplicate Description Test</h1>
            <p>This page is used to test multiple description detection.</p>
        </body>
        </html>
    `);

    return;
}
// if (req.url === "/slow-page") {
//     setTimeout(() => {
//         res.writeHead(200, {
//             "Content-Type": "text/html"
//         });

//         res.end(`
//             <!DOCTYPE html>
//             <html>
//             <head>
//                 <title>Slow Page</title>
//             </head>
//             <body>
//                 <h1>Slow Page</h1>
//             </body>
//             </html>
//         `);
//     }, 35000);

//     return;
// }
if (req.url === "/js-ui-test.html") {
    const html = fs.readFileSync(
        "js-ui-test.html",
        "utf8"
    );

    res.writeHead(200, {
        "Content-Type": "text/html"
    });

    res.end(html);
    return;
}
if (req.url === "/robots.txt") {
    const robots = fs.readFileSync(
        "robots.txt",
        "utf8"
    );

    res.writeHead(200, {
        "Content-Type": "text/plain"
    });

    res.end(robots);
    return;
}


    res.writeHead(404);
    res.end("Not Found");
});

server.listen(3000, () => {
    console.log("Server running at http://localhost:3000");
});