function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function createRateLimiter(delayMs = 500) {
    let lastRequest = 0;

    return async function wait() {
        const now = Date.now();
        const elapsed = now - lastRequest;

        if (elapsed < delayMs) {
            await sleep(delayMs - elapsed);
        }

        lastRequest = Date.now();
    };
}

module.exports = {
    createRateLimiter
};