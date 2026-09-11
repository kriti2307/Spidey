async function analyzePage(page, response) {

    const data = await page.evaluate(() => {

        // -------------------------
        // Title
        // -------------------------

        const title = document.title.trim();


        // -------------------------
        // Meta description
        // -------------------------

        const descriptionElement =
            document.querySelector(
                'meta[name="description"]'
            );

        const description =
            descriptionElement
                ?.getAttribute("content")
                ?.trim() || null;


        // -------------------------
        // Headings
        // -------------------------

        const h1 = Array.from(
            document.querySelectorAll("h1")
        ).map(element =>
            element.innerText.trim()
        );

        const h2 = Array.from(
            document.querySelectorAll("h2")
        ).map(element =>
            element.innerText.trim()
        );


        // -------------------------
        // Visible text
        // -------------------------

        const visibleText =
            document.body.innerText
                .replace(/\s+/g, " ")
                .trim();

        const words =
            visibleText
                ? visibleText.split(/\s+/).length
                : 0;


        // -------------------------
        // Links
        // -------------------------

        const links = Array.from(
            document.querySelectorAll("a")
        ).map(anchor => ({
            text: anchor.innerText.trim(),
            href: anchor.href
        }));


        // -------------------------
        // Images
        // -------------------------

        const images = Array.from(
            document.querySelectorAll("img")
        ).map(image => ({
            src: image.src,
            alt: image.getAttribute("alt")
        }));


        // -------------------------
        // Canonical
        // -------------------------

        const canonicalElement =
            document.querySelector(
                'link[rel="canonical"]'
            );

        const canonical =
            canonicalElement?.href || null;


        // -------------------------
        // Robots meta
        // -------------------------

        const robotsElement =
            document.querySelector(
                'meta[name="robots"]'
            );

        const robots =
            robotsElement
                ?.getAttribute("content")
                ?.trim() || null;


        // -------------------------
        // JSON-LD
        // -------------------------

        const jsonLdScripts =
            Array.from(
                document.querySelectorAll(
                    'script[type="application/ld+json"]'
                )
            );

        const jsonLd = [];

        for (const script of jsonLdScripts) {

            try {

                const parsed =
                    JSON.parse(script.textContent);

                jsonLd.push(parsed);

            } catch (error) {

                jsonLd.push({
                    invalid: true
                });

            }
        }


        return {
            title,
            description,
            h1,
            h2,
            visibleText,
            wordCount: words,
            links,
            images,
            canonical,
            robots,
            jsonLd
        };
    });


    return {
        url: page.url(),

        status: response
            ? response.status()
            : null,

        ...data
    };
}


module.exports = {
    analyzePage
};