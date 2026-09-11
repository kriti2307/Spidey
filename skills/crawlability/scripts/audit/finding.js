function createFinding({
    type,
    severity,
    url,
    title,
    evidence,
    recommendation
}) {
    return {
        type,
        severity,
        url,
        title,
        evidence,
        recommendation
    };
}

module.exports = {
    createFinding
};