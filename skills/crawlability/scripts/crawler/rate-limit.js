function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Create a simple request rate limiter.
 *
 * The caller should provide the delay required by robots.txt,
 * or a small default safety delay when no crawl-delay exists.
 */
function createRateLimiter(delayMs = 100) {
    // Never allow a negative/invalid delay.
    const safeDelay = Math.max(0, Number(delayMs) || 0);

    let lastRequest = 0;

    return async function wait() {
        const now = Date.now();
        const elapsed = now - lastRequest;

        if (elapsed < safeDelay) {
            await sleep(safeDelay - elapsed);
        }

        lastRequest = Date.now();
    };
}

module.exports = {
    createRateLimiter
};