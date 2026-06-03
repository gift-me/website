function formatCountdown(totalSeconds) {
    if (totalSeconds <= 0) {
        return "Happy Birthday! The celebration is live.";
    }
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    return `${days} Days ${hours} Hours ${minutes} Minutes`;
}

function initCountdown() {
    const box = document.querySelector("[data-countdown]");
    if (!box) return;
    const text = box.querySelector(".countdown-text");
    let remaining = Number(box.dataset.countdown || 0);
    text.textContent = `Birthday starts in ${formatCountdown(remaining)}`;
    window.setInterval(() => {
        remaining = Math.max(remaining - 60, 0);
        text.textContent = `Birthday starts in ${formatCountdown(remaining)}`;
    }, 60000);
}

function initGiftAnimationHooks() {
    const wall = document.getElementById("gift-wall");
    if (!wall) return;
    const notes = wall.querySelectorAll(".gift-note");
    notes.forEach((note, idx) => {
        note.style.animationDelay = `${idx * 80}ms`;
        note.animate(
            [{ opacity: 0, transform: "translateY(7px)" }, { opacity: 1, transform: "translateY(0)" }],
            { duration: 400, easing: "ease-out", fill: "forwards" }
        );
    });
}

function initQrCode() {
    if (typeof QRCode === "undefined") return;

    document.querySelectorAll("[data-qr-url]").forEach((box) => {
        const url = (box.dataset.qrUrl || "").trim();
        if (!url) return;
        box.innerHTML = "";
        new QRCode(box, {
            text: url,
            width: 130,
            height: 130,
        });
    });
}

function downloadQrFromBox(boxId, filename) {
    const qrBox = document.getElementById(boxId);
    if (!qrBox) return;
    const img = qrBox.querySelector("img");
    const canvas = qrBox.querySelector("canvas");
    let dataUrl = "";

    if (canvas) {
        dataUrl = canvas.toDataURL("image/png");
    } else if (img && img.src) {
        const temp = document.createElement("canvas");
        temp.width = img.naturalWidth || img.width || 130;
        temp.height = img.naturalHeight || img.height || 130;
        temp.getContext("2d").drawImage(img, 0, 0);
        dataUrl = temp.toDataURL("image/png");
    }

    if (!dataUrl) return;

    const link = document.createElement("a");
    link.href = dataUrl;
    link.download = filename || "giftme-qr.png";
    link.click();
}

function initQrDownload() {
    document.querySelectorAll(".qr-download").forEach((btn) => {
        btn.addEventListener("click", () => {
            downloadQrFromBox(btn.dataset.qrTarget, btn.dataset.qrFilename);
        });
    });
}

function initGiftAutoAmount() {
    const optionField = document.getElementById("id_option");
    const amountField = document.getElementById("id_amount");
    if (!optionField || !amountField) return;
    const mapping = {};
    optionField.querySelectorAll("option").forEach((opt) => {
        const text = opt.textContent || "";
        const match = text.match(/KES\s*(\d+(\.\d+)?)/i);
        mapping[opt.value] = match ? match[1] : "";
    });
    optionField.addEventListener("change", () => {
        const fixedAmount = mapping[optionField.value];
        if (fixedAmount) {
            amountField.value = fixedAmount;
            amountField.setAttribute("readonly", "readonly");
        } else {
            amountField.removeAttribute("readonly");
            if (!amountField.value) amountField.value = "";
        }
    });
    optionField.dispatchEvent(new Event("change"));
}

function initDashboardTabs() {
    const tabButtons = document.querySelectorAll(".dash-tab[data-tab-target], .tab-btn[data-tab-target]");
    if (!tabButtons.length) return;
    tabButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const targetId = button.getAttribute("data-tab-target");
            const isDash = button.classList.contains("dash-tab");
            const btnSelector = isDash ? ".dash-tab" : ".tab-btn";
            const panelSelector = isDash ? ".dash-tab-panel" : ".tab-panel";
            document.querySelectorAll(btnSelector).forEach((b) => b.classList.remove("active"));
            document.querySelectorAll(panelSelector).forEach((panel) => panel.classList.remove("active"));
            button.classList.add("active");
            const targetPanel = document.getElementById(targetId);
            if (targetPanel) targetPanel.classList.add("active");
        });
    });
}

function initCopyLink() {
    document.querySelectorAll("[data-copy-link]").forEach((trigger) => {
        trigger.addEventListener("click", async () => {
            const link = trigger.getAttribute("data-copy-link");
            if (!link) return;
            try {
                await navigator.clipboard.writeText(link);
            } catch (error) {
                /* ignore */
            }
        });
    });
}

function initCopyButtons() {
    document.querySelectorAll("[data-copy-target]").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const el = document.getElementById(btn.dataset.copyTarget);
            if (!el) return;
            const text = (el.textContent || "").trim();
            try {
                await navigator.clipboard.writeText(text);
                btn.classList.add("copied");
                window.setTimeout(() => btn.classList.remove("copied"), 1500);
            } catch (error) {
                /* ignore */
            }
        });
    });

    document.querySelectorAll("[data-copy-text]").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const text = btn.dataset.copyText;
            if (!text) return;
            try {
                await navigator.clipboard.writeText(text);
            } catch (error) {
                /* ignore */
            }
        });
    });
}

function initModal(modalId, openerIds) {
    const modal = document.getElementById(modalId);
    if (!modal) return { open: () => {}, close: () => {} };

    function openModal() {
        modal.hidden = false;
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        modal.hidden = true;
        document.body.style.overflow = "";
    }

    openerIds.forEach((id) => {
        const btn = document.getElementById(id);
        if (btn) btn.addEventListener("click", openModal);
    });

    modal.querySelectorAll(`[data-close-modal="${modalId}"]`).forEach((el) => {
        el.addEventListener("click", closeModal);
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modal.hidden) closeModal();
    });

    return { open: openModal, close: closeModal };
}

function initWishlistModal() {
    initModal("wishlist-modal", ["open-wishlist-modal", "open-wishlist-modal-2"]);

    const rowsContainer = document.getElementById("wishlist-rows");
    const addRowBtn = document.getElementById("add-wishlist-row");
    const maxRows = 10;

    if (!rowsContainer || !addRowBtn) return;

    function updateAddButton() {
        const count = rowsContainer.querySelectorAll("[data-wishlist-row]").length;
        addRowBtn.hidden = count >= maxRows;
    }

    addRowBtn.addEventListener("click", () => {
        const count = rowsContainer.querySelectorAll("[data-wishlist-row]").length;
        if (count >= maxRows) return;

        const row = document.createElement("div");
        row.className = "wishlist-item-row";
        row.dataset.wishlistRow = "";
        row.innerHTML = `
            <div class="field">
                <label>Item name</label>
                <input name="wish_title" placeholder="Item name" required>
            </div>
            <div class="field">
                <label>Target amount (KES)</label>
                <input name="wish_target" type="number" min="1" step="1" placeholder="5000" required>
            </div>
        `;
        rowsContainer.appendChild(row);
        updateAddButton();
        row.querySelector("input")?.focus();
    });

    updateAddButton();
}

function initWithdrawModal() {
    initModal("withdraw-modal", ["open-withdraw-modal"]);
}

function initProfileNoticeDismiss() {
    const notice = document.getElementById("profile-notice");
    const closeBtn = document.getElementById("dismiss-profile-notice");
    if (!notice || !closeBtn) return;
    closeBtn.addEventListener("click", () => {
        notice.classList.add("is-hidden");
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initCountdown();
    initGiftAnimationHooks();
    initQrCode();
    initQrDownload();
    initGiftAutoAmount();
    initDashboardTabs();
    initCopyLink();
    initCopyButtons();
    initWishlistModal();
    initWithdrawModal();
    initProfileNoticeDismiss();
});
