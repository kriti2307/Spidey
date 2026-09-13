function extractPageData(page, startUrl) {
    return page.evaluate((startUrl) => {
        const clean = (value) =>
            value?.replace(/\s+/g, " ").trim() || "";

        const baseUrl = new URL(startUrl);

        const semanticElements = {
            main: !!document.querySelector("main"),
            header: !!document.querySelector("header"),
            nav: !!document.querySelector("nav"),
            footer: !!document.querySelector("footer"),
            article: !!document.querySelector("article"),
            sections: document.querySelectorAll("section").length
        };

        // -----------------------------
        // Title
        // -----------------------------

        const title = clean(document.title);

        const titleCount = document.querySelectorAll("title").length;


        // -----------------------------
        // Meta description
        // -----------------------------

        const description = clean(
            document
                .querySelector('meta[name="description"]')
                ?.getAttribute("content")
        );

        const descriptionCount =
            document.querySelectorAll('meta[name="description"]').length;

        const canonical = document
            .querySelector('link[rel="canonical"]')
            ?.getAttribute("href") || null;


        // -----------------------------
        // Headings
        // -----------------------------

        const headings = Array.from(
            document.querySelectorAll(
                "h1, h2, h3, h4, h5, h6, [role='heading'][aria-level]"
            )
        )
            .map(element => ({
                level: element.matches("[role='heading']")
                    ? Number(element.getAttribute("aria-level"))
                    : Number(element.tagName.substring(1)),
                text: clean(element.innerText)
            }))
            .filter(heading => heading.text);


        // -----------------------------
        // Visible text
        // -----------------------------

        const visibleText = clean(
            document.body?.innerText
        );

        const mainElement =
            document.querySelector("main");

        const mainText = clean(
            mainElement?.innerText
        );

        const hiddenElements = Array.from(
            document.querySelectorAll(
                "[hidden], [style*='display:none'], [style*='visibility:hidden']"
            )
        );

        const hiddenText = hiddenElements
            .map(element => clean(element.innerText))
            .filter(Boolean);

        const wordCount = visibleText
            ? visibleText.split(/\s+/).length
            : 0;


        // -----------------------------
        // Links
        // -----------------------------

        const links = Array.from(
            document.querySelectorAll("a[href]")
        )
            .map(anchor => {

                const href = anchor.href;
                const text = clean(anchor.innerText);

                let type = "external";

                try {
                    const linkUrl = new URL(href);

                    if (
                        linkUrl.origin === baseUrl.origin
                    ) {
                        type = "internal";
                    }
                } catch {
                    type = "invalid";
                }

                return {
                    text,
                    href,
                    type
                };
            })
            .filter(link => link.href);


        // -----------------------------
        // Images
        // -----------------------------

        const images = Array.from(
            document.querySelectorAll("img")
        )
            .map(image => ({
                src: image.src,
                alt: image.hasAttribute("alt")
                    ? clean(image.getAttribute("alt"))
                    : null,
                hasAlt: image.hasAttribute("alt"),
                role: image.getAttribute("role"),
                ariaHidden:
                    image.getAttribute("aria-hidden") === "true"
            }))
            .filter(image => image.src);


        return {
            title,
            titleCount,
            description,
            descriptionCount,
            canonical,
            headings,
            visibleText,
            wordCount,
            mainText,
            hiddenText,
            semanticElements,
            links,
            images
        };

    }, startUrl);
}


module.exports = {
    extractPageData
};