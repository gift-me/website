document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("payout-modal");
    if (!modal) return;

    const detailsForm = document.getElementById("payout-details-form");
    const verifyForm = document.getElementById("payout-verify-form");
    const stateForm = document.getElementById("payout-state-form");
    const stateVerify = document.getElementById("payout-state-verify");
    const stateLoading = document.getElementById("payout-state-loading");
    const stateSuccess = document.getElementById("payout-state-success");
    const errorEl = document.getElementById("payout-modal-error");
    const verifyHint = document.getElementById("payout-verify-hint");
    const successMessage = document.getElementById("payout-success-message");
    const backBtn = document.getElementById("payout-back-btn");
    const sendCodeBtn = document.getElementById("payout-send-code-btn");
    const submitBtn = document.getElementById("payout-submit-btn");

    let authorizationId = null;
    let pollTimer = null;

    function getCsrfToken() {
        const input = detailsForm?.querySelector("[name=csrfmiddlewaretoken]");
        if (input?.value) return input.value;
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
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

    function setBusy(button, busy, label) {
        if (!button) return;
        button.disabled = busy;
        if (label) button.textContent = label;
    }

    function showState(state) {
        if (stateForm) stateForm.hidden = state !== "form";
        if (stateVerify) stateVerify.hidden = state !== "verify";
        if (stateLoading) stateLoading.hidden = state !== "loading";
        if (stateSuccess) stateSuccess.hidden = state !== "success";
    }

    function stopPolling() {
        if (pollTimer) {
            window.clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    function resetModal() {
        stopPolling();
        authorizationId = null;
        showError("");
        showState("form");
        verifyForm?.reset();
        setBusy(sendCodeBtn, false, "Send code");
        setBusy(submitBtn, false, "Confirm payout");
    }

    function openModal() {
        resetModal();
        modal.hidden = false;
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        modal.hidden = true;
        document.body.style.overflow = "";
        resetModal();
    }

    document.getElementById("open-payout-modal")?.addEventListener("click", openModal);
    modal.querySelectorAll('[data-close-modal="payout-modal"]').forEach((el) => {
        el.addEventListener("click", closeModal);
    });
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modal.hidden) closeModal();
    });

    backBtn?.addEventListener("click", () => {
        showError("");
        showState("form");
    });

    async function pollPayoutStatus(payoutId) {
        stopPolling();
        pollTimer = window.setInterval(async () => {
            try {
                const response = await fetch(`/api/payout/status/${payoutId}/`, {
                    headers: { Accept: "application/json" },
                });
                const data = await response.json();
                if (!data.success) return;

                if (data.status === "approved") {
                    stopPolling();
                    if (successMessage) {
                        successMessage.textContent =
                            data.result_desc || "Payout completed. Funds sent to your M-Pesa.";
                    }
                    showState("success");
                    window.setTimeout(() => window.location.reload(), 1800);
                } else if (data.status === "failed" || data.status === "rejected") {
                    stopPolling();
                    showState("verify");
                    showError(data.result_desc || "Payout failed. Try again.");
                }
            } catch (error) {
                /* keep polling */
            }
        }, 3000);
    }

    detailsForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        showError("");
        setBusy(sendCodeBtn, true, "Sending…");

        const formData = new FormData(detailsForm);
        const payload = {
            amount: formData.get("amount"),
            payout_phone: formData.get("payout_phone"),
        };

        try {
            const response = await fetch("/api/payout/initiate/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || "Could not send verification code.");
            }

            authorizationId = data.authorization_id;
            if (verifyHint) {
                verifyHint.textContent = data.message || "Enter the code sent to your email.";
            }
            showState("verify");
            document.getElementById("payout-code")?.focus();
        } catch (error) {
            showError(error.message || "Could not send verification code.");
        } finally {
            setBusy(sendCodeBtn, false, "Send code");
        }
    });

    verifyForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        showError("");

        if (!authorizationId) {
            showError("Start the payout again.");
            showState("form");
            return;
        }

        showState("loading");
        setBusy(submitBtn, true, "Processing…");

        const formData = new FormData(verifyForm);
        const payload = {
            authorization_id: authorizationId,
            code: formData.get("code"),
        };

        try {
            const response = await fetch("/api/payout/verify/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || "Payout could not be processed.");
            }

            if (successMessage) {
                successMessage.textContent =
                    data.message || "Payout submitted. M-Pesa is processing your transfer.";
            }

            if (data.status === "approved") {
                showState("success");
                window.setTimeout(() => window.location.reload(), 1800);
            } else {
                showState("loading");
                pollPayoutStatus(data.payout_id);
            }
        } catch (error) {
            showState("verify");
            showError(error.message || "Payout could not be processed.");
        } finally {
            setBusy(submitBtn, false, "Confirm payout");
        }
    });
});
