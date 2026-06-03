document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("contribute-modal");
    if (!modal) return;

    const form = document.getElementById("contribute-form");
    const stateForm = document.getElementById("contrib-state-form");
    const stateLoading = document.getElementById("contrib-state-loading");
    const stateSuccess = document.getElementById("contrib-state-success");
    const titleEl = document.getElementById("contribute-modal-title");
    const subEl = document.getElementById("contribute-modal-sub");
    const errorEl = document.getElementById("contribute-modal-error");
    const giftIdInput = document.getElementById("contrib-gift-id");
    const wishlistIdInput = document.getElementById("contrib-wishlist-id");
    const amountWrap = document.getElementById("contrib-amount-wrap");
    const amountInput = document.getElementById("contrib-amount");
    const messageInput = document.getElementById("contrib-message");
    const messageCount = document.getElementById("contrib-message-count");
    const submitLabel = document.getElementById("contrib-submit-label");
    const submitIcon = document.getElementById("contrib-submit-icon");
    const whatsappLink = document.getElementById("contrib-whatsapp-share");

    const pageType = modal.dataset.pageType || "gift";
    const pageSlug = modal.dataset.pageSlug || "";
    const defaultSubmitLabel = pageType === "wishlist" ? "Fulfill my wish" : "Gift";
    let pollTimer = null;

    function getCsrfToken() {
        const input = form?.querySelector("[name=csrfmiddlewaretoken]");
        if (input?.value) return input.value;
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    function showState(state) {
        if (stateForm) stateForm.hidden = state !== "form";
        if (stateLoading) stateLoading.hidden = state !== "loading";
        if (stateSuccess) stateSuccess.hidden = state !== "success";
    }

    function showError(message) {
        if (!errorEl) return;
        if (message) {
            errorEl.textContent = message;
            errorEl.hidden = false;
        } else {
            errorEl.hidden = true;
            errorEl.textContent = "";
        }
    }

    function stopPolling() {
        if (pollTimer) {
            window.clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    function openModal(config) {
        stopPolling();
        showState("form");
        showError("");

        if (giftIdInput) giftIdInput.value = config.giftId || "";
        if (wishlistIdInput) wishlistIdInput.value = config.wishlistId || "";
        if (titleEl) titleEl.textContent = config.title || "Send a gift";
        if (subEl) {
            if (config.subtitle) {
                subEl.textContent = config.subtitle;
                subEl.hidden = false;
            } else {
                subEl.hidden = true;
            }
        }
        if (submitLabel) submitLabel.textContent = config.submitLabel || defaultSubmitLabel;
        if (submitIcon) {
            submitIcon.className = config.wishlistId
                ? "fa-solid fa-heart"
                : "fa-solid fa-gift";
        }

        if (amountWrap && amountInput) {
            const showAmount = config.showAmount !== false;
            amountWrap.hidden = !showAmount;
            amountInput.required = showAmount;
            if (showAmount) amountInput.removeAttribute("readonly");
            amountInput.value = config.amount || "";
        }

        if (form) form.reset();
        if (giftIdInput) giftIdInput.value = config.giftId || "";
        if (wishlistIdInput) wishlistIdInput.value = config.wishlistId || "";
        if (amountInput && config.amount) amountInput.value = config.amount;
        if (messageCount) messageCount.textContent = "0";

        modal.hidden = false;
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        stopPolling();
        modal.hidden = true;
        document.body.style.overflow = "";
        showState("form");
        showError("");
    }

    function pollPaymentStatus(paymentId) {
        stopPolling();
        pollTimer = window.setInterval(async () => {
            try {
                const res = await fetch(`/api/mpesa/status/${paymentId}/`, {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                });
                const data = await res.json();
                if (!data.success) return;

                if (data.status === "completed") {
                    stopPolling();
                    showState("success");
                    if (whatsappLink && data.share?.url) {
                        whatsappLink.href = data.share.url;
                    }
                } else if (data.status === "failed" || data.status === "cancelled") {
                    stopPolling();
                    showState("form");
                    showError(data.result_desc || "Payment failed. Please try again.");
                }
            } catch (err) {
                /* keep polling */
            }
        }, 2500);

        window.setTimeout(() => {
            stopPolling();
            if (!stateLoading?.hidden) {
                showState("form");
                showError("Payment is taking longer than expected. If you paid, refresh the page.");
            }
        }, 120000);
    }

    async function submitPayment(event) {
        event.preventDefault();
        showError("");

        const payload = {
            page_type: pageType,
            slug: pageSlug,
            gift_id: giftIdInput?.value || "",
            wishlist_item_id: wishlistIdInput?.value || "",
            amount: amountInput?.value || "",
            sender_name: document.getElementById("contrib-name")?.value || "",
            payer_phone: document.getElementById("contrib-phone")?.value || "",
            message: messageInput?.value || "",
        };

        showState("loading");

        try {
            const res = await fetch("/api/mpesa/stk-push/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify(payload),
            });
            const data = await res.json();

            if (!res.ok || !data.success) {
                showState("form");
                showError(data.error || "Could not start payment.");
                return;
            }

            pollPaymentStatus(data.payment_id);
        } catch (err) {
            showState("form");
            showError("Network error. Please try again.");
        }
    }

    if (form) {
        form.addEventListener("submit", submitPayment);
    }

    modal.querySelectorAll("[data-close-contribute]").forEach((el) => {
        el.addEventListener("click", closeModal);
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modal.hidden) closeModal();
    });

    if (messageInput && messageCount) {
        messageInput.addEventListener("input", () => {
            messageCount.textContent = String(messageInput.value.length);
        });
    }

    window.ContributeModal = { open: openModal, close: closeModal };
});
