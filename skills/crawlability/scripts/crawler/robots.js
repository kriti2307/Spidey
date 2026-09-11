const robotsParser = require("robots-parser");

async function getRobotsRules(startUrl) {

    const url = new URL(startUrl);

    const robotsUrl = `${url.origin}/robots.txt`;

    try {

        const response = await fetch(robotsUrl);

        if (!response.ok) {
            return null;
        }

        const robotsText = await response.text();

        return robotsParser(
            robotsUrl,
            robotsText
        );

    } catch (error) {

        return null;
    }
}


function isAllowed(robots, url) {

    if (!robots) {
        return true;
    }

    return robots.isAllowed(
        url,
        "AdobeRound3Crawler"
    );
}


function getCrawlDelay(robots) {
    if (!robots) {
        return 0;
    }

    const delay = robots.getCrawlDelay(
        "AdobeRound3Crawler"
    );

    return typeof delay === "number"
        ? delay * 1000
        : 0;
}

module.exports = {
    getRobotsRules,
    isAllowed,
    getCrawlDelay
};