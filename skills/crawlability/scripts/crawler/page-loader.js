async function loadPage(page, url) {

    const result = {
        requestedUrl: url,
        finalUrl: null,
        status: null,
        success: false,
        redirects: [],
        error: null,
        errorType: null
    };

    const responseHandler = response => {

        const status = response.status();

        const responseUrl = response.url();

        const redirectStatuses = [
            301,
            302,
            303,
            307,
            308
        ];

        const request = response.request();

        if (
            redirectStatuses.includes(status) &&
            request.resourceType() === "document"
        ) {
            result.redirects.push({
                url: responseUrl,
                status
            });
        }
    };

    page.on("response", responseHandler);

    try {

        const response = await page.goto(url, {
            waitUntil: "domcontentloaded",
            timeout: 30000
        });

        if (response) {
            result.status = response.status();
        }

        result.finalUrl = page.url();

        result.success = true;

        return {
            ...result,
            response
        };

    } catch (error) {   
        result.error = error.message;

        if (error.message.includes("Timeout")) {
            result.errorType = "timeout";
        } else if (
            error.message.includes("ERR_NAME_NOT_RESOLVED") ||
            error.message.includes("ENOTFOUND")
        ) {
            result.errorType = "dns-error";
        } else if (
            error.message.includes("ERR_CONNECTION_REFUSED") ||
            error.message.includes("ECONNREFUSED")
        ) {
            result.errorType = "connection-error";
        } else if (
            error.message.includes("ERR_HTTP2_PROTOCOL_ERROR")
        ) {
            result.errorType = "http2-error";
        } else {
            result.errorType = "navigation-error";
        }

        result.finalUrl = null;

            return {
                ...result,
                response: null
        };

    } finally {

        page.off(
            "response",
            responseHandler
        );
    }
}


module.exports = {
    loadPage
};