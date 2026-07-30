(function () {
    if (typeof Chart === "undefined") return;

    const brandColors = {
        primary: "#E63946",
        gold: "#F4D35E",
        mint: "#2A9D8F",
        muted: "#E9E5DA",
    };

    const chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { font: { family: "Inter, sans-serif", size: 11 }, boxWidth: 12 },
            },
        },
    };

    function readJsonScript(id) {
        const el = document.getElementById(id);
        if (!el?.textContent) return null;
        try {
            return JSON.parse(el.textContent);
        } catch {
            return null;
        }
    }

    function showEmptyChart(el, message) {
        const wrap = el?.closest(".ops-chart-wrap");
        if (!wrap) return;
        el.hidden = true;
        let note = wrap.querySelector(".ops-chart-empty");
        if (!note) {
            note = document.createElement("p");
            note.className = "ops-chart-empty";
            wrap.appendChild(note);
        }
        note.textContent = message;
    }

    const revenueEl = document.getElementById("ops-revenue-chart");
    const revenueData = readJsonScript("ops-revenue-data");
    if (revenueEl && revenueData?.length) {
        new Chart(revenueEl, {
            type: "line",
            data: {
                labels: revenueData.map((r) => r.day),
                datasets: [
                    {
                        label: "Deposits (KES)",
                        data: revenueData.map((r) => r.total),
                        borderColor: brandColors.primary,
                        backgroundColor: "rgba(230, 57, 70, 0.12)",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 4,
                    },
                    {
                        label: "House profit (KES)",
                        data: revenueData.map((r) => r.house),
                        borderColor: brandColors.mint,
                        backgroundColor: "transparent",
                        tension: 0.35,
                        pointRadius: 3,
                    },
                ],
            },
            options: {
                ...chartDefaults,
                scales: {
                    y: { beginAtZero: true, grid: { color: "rgba(233, 229, 218, 0.6)" } },
                    x: { grid: { display: false } },
                },
            },
        });
    } else if (revenueEl) {
        showEmptyChart(revenueEl, "No completed payments in the last 30 days yet.");
    }

    const giftsEl = document.getElementById("ops-gifts-chart");
    const giftsData = readJsonScript("ops-gifts-data");
    if (giftsEl && giftsData?.length) {
        new Chart(giftsEl, {
            type: "bar",
            data: {
                labels: giftsData.map((r) => r.day),
                datasets: [
                    {
                        label: "Gifts",
                        data: giftsData.map((r) => r.count),
                        backgroundColor: brandColors.primary,
                        borderRadius: 6,
                    },
                ],
            },
            options: {
                ...chartDefaults,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: "rgba(233, 229, 218, 0.6)" } },
                    x: { grid: { display: false } },
                },
            },
        });
    } else if (giftsEl) {
        showEmptyChart(giftsEl, "No gifts received in the last 7 days yet.");
    }

    const statusEl = document.getElementById("ops-status-chart");
    const statusData = readJsonScript("ops-status-data");
    if (statusEl && statusData?.length) {
        const statusColors = {
            completed: brandColors.mint,
            pending: brandColors.gold,
            failed: brandColors.primary,
            cancelled: "#9ca3af",
        };
        new Chart(statusEl, {
            type: "doughnut",
            data: {
                labels: statusData.map((r) => r.label),
                datasets: [
                    {
                        data: statusData.map((r) => r.value),
                        backgroundColor: statusData.map(
                            (r) => statusColors[r.status] || brandColors.muted
                        ),
                        borderWidth: 2,
                        borderColor: "#fff",
                    },
                ],
            },
            options: {
                ...chartDefaults,
                cutout: "58%",
            },
        });
    } else if (statusEl) {
        showEmptyChart(statusEl, "No payment records yet.");
    }

    const breakdownEl = document.getElementById("ops-breakdown-chart");
    const breakdownData = readJsonScript("ops-breakdown-data");
    if (breakdownEl && breakdownData?.length) {
        new Chart(breakdownEl, {
            type: "pie",
            data: {
                labels: breakdownData.map((r) => r.label),
                datasets: [
                    {
                        data: breakdownData.map((r) => r.value),
                        backgroundColor: [brandColors.mint, brandColors.primary, brandColors.gold],
                        borderWidth: 2,
                        borderColor: "#fff",
                    },
                ],
            },
            options: chartDefaults,
        });
    } else if (breakdownEl) {
        showEmptyChart(breakdownEl, "No revenue to break down yet.");
    }
})();
