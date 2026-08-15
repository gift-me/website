document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("withdraw-modal");
    if (!modal) return;

    const detailsForm = document.getElementById("withdraw-details-form");
    const verifyForm = document.getElementById("withdraw-verify-form");
    const stateForm = document.getElementById("withdraw-state-form");
    const stateVerify = document.getElementById("withdraw-state-verify");
    const stateLoading = document.getElementById("withdraw-state-loading");
    const stateSuccess = document.getElementById("withdraw-state-success");
    const errorEl = document.getElementById("withdraw-modal-error");
    const verifyHint = document.getElementById("withdraw-verify-hint");
    const successMessage = document.getElementById("withdraw-success-message");
    const backBtn = document.getElementById("withdraw-back-btn");
    const sendCodeBtn = document.getElementById("withdraw-send-code-btn");
    const submitBtn = document.getElementById("withdraw-submit-btn");

    let authorizationId = null;
    let pollTimer = null;
    let withdrawalCompleted = false;

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
        withdrawalCompleted = false;
        showError("");
        showState("form");
        verifyForm?.reset();
        setBusy(sendCodeBtn, false, "Send code");
        setBusy(submitBtn, false, "Confirm withdrawal");
    }

    function openModal() {
        resetModal();
        modal.hidden = false;
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        const reloadAfterClose = withdrawalCompleted;
        modal.hidden = true;
        document.body.style.overflow = "";
        resetModal();
        if (reloadAfterClose) window.location.reload();
    }

    document.getElementById("open-withdraw-modal")?.addEventListener("click", openModal);
    modal.querySelectorAll('[data-close-modal="withdraw-modal"]').forEach((el) => {
        el.addEventListener("click", closeModal);
    });
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modal.hidden) closeModal();
    });

    backBtn?.addEventListener("click", () => {
        showError("");
        showState("form");
    });

    async function pollWithdrawalStatus(withdrawalId) {
        stopPolling();
        pollTimer = window.setInterval(async () => {
            try {
                const response = await fetch(`/api/withdraw/status/${withdrawalId}/`, {
                    headers: { Accept: "application/json" },
                });
                const data = await response.json();
                if (!data.success) return;

                if (data.status === "approved") {
                    stopPolling();
                    if (successMessage) {
                        successMessage.textContent =
                            data.result_desc || "Withdrawal completed. Funds sent to your M-Pesa.";
                    }
                    showState("success");
                    window.setTimeout(() => window.location.reload(), 1800);
                } else if (data.status === "failed" || data.status === "rejected") {
                    stopPolling();
                    showState("verify");
                    showError(data.result_desc || "Withdrawal failed. Try again.");
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
            const response = await fetch("/api/withdraw/initiate/", {
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
            document.getElementById("withdraw-code")?.focus();
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
            showError("Start the withdrawal again.");
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
            const response = await fetch("/api/withdraw/verify/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.error || "Withdrawal could not be processed.");
            }

            if (successMessage) {
                successMessage.textContent =
                    data.message || "Your withdrawal is being processed. It normally takes up to 24 hours.";
            }
            withdrawalCompleted = true;
            showState("success");
        } catch (error) {
            showState("verify");
            showError(error.message || "Withdrawal could not be processed.");
        } finally {
            setBusy(submitBtn, false, "Confirm withdrawal");
        }
    });
});
