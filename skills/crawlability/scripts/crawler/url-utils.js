function normalizeUrl(url) {
    try {
        const parsed = new URL(url);

        // Remove #section
        parsed.hash = "";

        // Remove trailing slash
        if (parsed.pathname !== "/") {
            parsed.pathname =
                parsed.pathname.replace(/\/+$/, "");
        }

        // Remove tracking parameters
        const trackingParams = [
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "fbclid",
            "gclid"
        ];

        for (const param of trackingParams) {
            parsed.searchParams.delete(param);
        }

        // Sort remaining parameters
        parsed.searchParams.sort();

        return parsed.toString();

    } catch {
        return null;
    }
}


function isSameOrigin(url, startUrl) {
    try {
        const urlObject = new URL(url);
        const startObject = new URL(startUrl);

        return (
            urlObject.protocol === startObject.protocol &&
            urlObject.hostname === startObject.hostname &&
            urlObject.port === startObject.port
        );

    } catch {
        return false;
    }
}


function isProbablyCrawlableUrl(url) {
    try {
        const parsed = new URL(url);

        // Don't crawl fragments
        if (parsed.hash) {
            return false;
        }

        // Don't crawl common non-HTML resources
        const ignoredExtensions = [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".svg",
            ".pdf",
            ".zip",
            ".doc",
            ".docx",
            ".ppt",
            ".pptx",
            ".xls",
            ".xlsx",
            ".mp4",
            ".mp3",
            ".css",
            ".wav",
            ".js",
            ".json",
            ".xml"
        ];

        const path = parsed.pathname.toLowerCase();

        if (
            ignoredExtensions.some(
                extension => path.endsWith(extension)
            )
        ) {
            return false;
        }

        return true;

    } catch {
        return false;
    }
}


module.exports = {
    normalizeUrl,
    isSameOrigin,
    isProbablyCrawlableUrl
};