(function () {
    function csrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : "";
    }

    const body = document.body;
    const sidebar = document.getElementById("ops-sidebar");
    const sidebarToggle = document.getElementById("ops-sidebar-toggle");
    const mobileMenuBtn = document.getElementById("ops-mobile-menu-btn");
    const sidebarBackdrop = document.getElementById("ops-sidebar-backdrop");

    function setSidebarOpen(open) {
        body.classList.toggle("ops-sidebar-open", open);
        if (sidebarBackdrop) sidebarBackdrop.hidden = !open;
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", () => {
            body.classList.toggle("ops-sidebar-collapsed");
            try {
                localStorage.setItem(
                    "ops-sidebar-collapsed",
                    body.classList.contains("ops-sidebar-collapsed") ? "1" : "0"
                );
            } catch (_) {}
        });
    }

    if (localStorage.getItem("ops-sidebar-collapsed") === "1") {
        body.classList.add("ops-sidebar-collapsed");
    }

    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener("click", () => {
            setSidebarOpen(!body.classList.contains("ops-sidebar-open"));
        });
    }

    if (sidebarBackdrop) {
        sidebarBackdrop.addEventListener("click", () => setSidebarOpen(false));
    }

    if (sidebar) {
        sidebar.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => {
                if (window.matchMedia("(max-width: 768px)").matches) {
                    setSidebarOpen(false);
                }
            });
        });
    }

    const modal = document.getElementById("ops-house-modal");
    const openBtn = document.getElementById("ops-open-house-payout");
    const submitBtn = document.getElementById("ops-house-submit");
    const errorEl = document.getElementById("ops-house-error");

    function closeModal() {
        if (modal) modal.hidden = true;
    }

    if (openBtn && modal) {
        openBtn.addEventListener("click", () => {
            modal.hidden = false;
            if (errorEl) errorEl.hidden = true;
        });
    }

    document.querySelectorAll("[data-close-house-modal]").forEach((el) => {
        el.addEventListener("click", closeModal);
    });

    if (submitBtn) {
        submitBtn.addEventListener("click", async () => {
            const amount = document.getElementById("ops-house-amount")?.value;
            const phone = document.getElementById("ops-house-phone")?.value;
            if (!amount || !phone) return;

            submitBtn.disabled = true;
            try {
                const res = await fetch("/ops/house-payout/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-CSRFToken": csrfToken(),
                    },
                    body: new URLSearchParams({ amount, payout_phone: phone }),
                });
                const data = await res.json();
                if (!data.success) {
                    if (errorEl) {
                        errorEl.textContent = data.error || "Payout failed.";
                        errorEl.hidden = false;
                    }
                    return;
                }
                window.location.reload();
            } catch {
                if (errorEl) {
                    errorEl.textContent = "Network error. Try again.";
                    errorEl.hidden = false;
                }
            } finally {
                submitBtn.disabled = false;
            }
        });
    }
})();
