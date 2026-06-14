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

    const size = window.matchMedia("(max-width: 600px)").matches ? 96 : 120;

    document.querySelectorAll("[data-qr-url]").forEach((box) => {
        const url = (box.dataset.qrUrl || "").trim();
        if (!url) return;
        box.innerHTML = "";
        new QRCode(box, {
            text: url,
            width: size,
            height: size,
        });
    });
}

function getQrImageFromBox(qrBox) {
    if (!qrBox) return null;
    const img = qrBox.querySelector("img");
    const canvas = qrBox.querySelector("canvas");
    if (canvas) return canvas;
    if (img && img.src) {
        const temp = document.createElement("canvas");
        temp.width = img.naturalWidth || img.width || 120;
        temp.height = img.naturalHeight || img.height || 120;
        temp.getContext("2d").drawImage(img, 0, 0);
        return temp;
    }
    return null;
}

function wrapCanvasText(ctx, text, x, y, maxWidth, lineHeight) {
    const words = String(text).split(/\s+/);
    let line = "";
    let cy = y;
    words.forEach((word, index) => {
        const test = line ? `${line} ${word}` : word;
        if (ctx.measureText(test).width > maxWidth && line) {
            ctx.fillText(line, x, cy);
            line = word;
            cy += lineHeight;
        } else {
            line = test;
        }
        if (index === words.length - 1 && line) {
            ctx.fillText(line, x, cy);
        }
    });
    return cy;
}

function countWrappedLines(ctx, text, maxWidth) {
    const words = String(text).split(/\s+/);
    let line = "";
    let lines = 0;
    words.forEach((word, index) => {
        const test = line ? `${line} ${word}` : word;
        if (ctx.measureText(test).width > maxWidth && line) {
            lines += 1;
            line = word;
        } else {
            line = test;
        }
        if (index === words.length - 1 && line) {
            lines += 1;
        }
    });
    return Math.max(lines, 1);
}

function loadImage(src) {
    if (!src) return Promise.resolve(null);
    return new Promise((resolve) => {
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => resolve(img);
        img.onerror = () => resolve(null);
        img.src = src;
    });
}

function getQrPosterBranding() {
    const config = document.getElementById("qr-poster-config");
    return {
        logoUrl: (config?.dataset.logoUrl || "").trim(),
        siteUrl: (config?.dataset.siteUrl || "giftme.co").trim(),
    };
}

function getQrPosterCopy(type, displayName, isBirthday) {
    const name = (displayName || "them").trim();
    if (type === "wishlist") {
        return {
            title: `${name}'s wishlist`,
            subtitle:
                "Dreams deserve a chance. Scan to see what they hope for and chip in toward something that truly matters to them.",
            cta: "Every contribution brings a wish closer to reality.",
        };
    }
    if (isBirthday) {
        return {
            title: `It's ${name}'s birthday!`,
            subtitle:
                "Birthdays are about feeling loved. Scan to send a gift in seconds — thoughtful, secure, and straight from your heart.",
            cta: "Make their celebration unforgettable.",
        };
    }
    return {
        title: `Surprise ${name} with a gift`,
        subtitle:
            "Small gestures create big moments. Scan to pick a gift they'll love and pay safely with M-Pesa in just a few taps.",
        cta: "Show up for someone who matters to you.",
    };
}

async function buildQrPoster(options) {
    const { type, url, displayName, isBirthday, qrImage, logoUrl, siteUrl } = options;
    const width = 640;
    const height = 960;
    const headerHeight = 88;
    const footerHeight = 130;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");

    ctx.fillStyle = "#FFFDF8";
    ctx.fillRect(0, 0, width, height);

    const copy = getQrPosterCopy(type, displayName, isBirthday);
    const linkDisplay = url.replace(/^https?:\/\//i, "");
    const urlLineCount = linkDisplay.length > 46 ? 2 : 1;

    const qrSize = 260;
    const qrFramePad = 14;
    const gapTitleSubtitle = 22;
    const gapSubtitleCta = 30;
    const gapCtaQr = 44;
    const gapQrScan = 44;
    const gapScanUrl = 30;

    ctx.textAlign = "center";

    ctx.font = "700 32px Inter, system-ui, sans-serif";
    const titleHeight = countWrappedLines(ctx, copy.title, width - 80) * 38;

    ctx.font = "500 19px Inter, system-ui, sans-serif";
    const subtitleHeight = countWrappedLines(ctx, copy.subtitle, width - 88) * 27;

    ctx.font = "600 17px Inter, system-ui, sans-serif";
    const ctaHeight = countWrappedLines(ctx, copy.cta, width - 88) * 24;

    const qrBlockHeight = qrSize + qrFramePad * 2;
    const contentHeight =
        titleHeight +
        gapTitleSubtitle +
        subtitleHeight +
        gapSubtitleCta +
        ctaHeight +
        gapCtaQr +
        qrBlockHeight +
        gapQrScan +
        18 +
        gapScanUrl +
        urlLineCount * 20;

    const zoneTop = headerHeight;
    const zoneBottom = height - footerHeight;
    const zoneHeight = zoneBottom - zoneTop;
    const contentStartY = zoneTop + Math.max(28, (zoneHeight - contentHeight) / 2);

    ctx.fillStyle = "#E63946";
    ctx.fillRect(0, 0, width, headerHeight);
    ctx.fillStyle = "#FFFFFF";
    ctx.font = "700 30px Inter, system-ui, sans-serif";
    ctx.fillText("GiftMe", width / 2, 54);

    ctx.fillStyle = "#222222";
    ctx.font = "700 32px Inter, system-ui, sans-serif";
    const titleEnd = wrapCanvasText(ctx, copy.title, width / 2, contentStartY, width - 80, 38);

    ctx.fillStyle = "#6b7280";
    ctx.font = "500 19px Inter, system-ui, sans-serif";
    const subtitleEnd = wrapCanvasText(
        ctx,
        copy.subtitle,
        width / 2,
        titleEnd + gapTitleSubtitle,
        width - 88,
        27
    );

    ctx.fillStyle = "#2A9D8F";
    ctx.font = "600 17px Inter, system-ui, sans-serif";
    const ctaEnd = wrapCanvasText(
        ctx,
        copy.cta,
        width / 2,
        subtitleEnd + gapSubtitleCta,
        width - 88,
        24
    );

    const qrFrameTop = ctaEnd + gapCtaQr;
    const qrX = (width - qrSize) / 2;
    const qrY = qrFrameTop + qrFramePad;

    ctx.fillStyle = "#FFFFFF";
    ctx.strokeStyle = "#E9E5DA";
    ctx.lineWidth = 2;
    ctx.beginPath();
    if (typeof ctx.roundRect === "function") {
        ctx.roundRect(qrX - qrFramePad, qrFrameTop, qrSize + qrFramePad * 2, qrBlockHeight, 14);
    } else {
        ctx.rect(qrX - qrFramePad, qrFrameTop, qrSize + qrFramePad * 2, qrBlockHeight);
    }
    ctx.fill();
    ctx.stroke();

    if (qrImage) {
        ctx.drawImage(qrImage, qrX, qrY, qrSize, qrSize);
    }

    const scanY = qrY + qrSize + gapQrScan;
    ctx.fillStyle = "#6b7280";
    ctx.font = "600 15px Inter, system-ui, sans-serif";
    ctx.fillText("Scan with your phone · Pay with M-Pesa", width / 2, scanY);

    ctx.fillStyle = "#222222";
    ctx.font = "500 14px Inter, system-ui, sans-serif";
    const urlLines =
        linkDisplay.length > 46 ? [linkDisplay.slice(0, 46), linkDisplay.slice(46)] : [linkDisplay];
    urlLines.forEach((line, i) => {
        ctx.fillText(line, width / 2, scanY + gapScanUrl + i * 20);
    });

    const footerY = height - footerHeight;
    ctx.fillStyle = "#F4F0E8";
    ctx.fillRect(0, footerY, width, footerHeight);

    const logoImg = await loadImage(logoUrl);
    const logoMaxW = 120;
    const logoMaxH = 44;
    let logoDrawW = 0;
    let logoDrawH = 0;
    if (logoImg) {
        const scale = Math.min(logoMaxW / logoImg.width, logoMaxH / logoImg.height, 1);
        logoDrawW = logoImg.width * scale;
        logoDrawH = logoImg.height * scale;
        ctx.drawImage(logoImg, (width - logoDrawW) / 2, footerY + 18, logoDrawW, logoDrawH);
    }

    const poweredY = footerY + (logoImg ? 18 + logoDrawH + 22 : 36);
    ctx.fillStyle = "#222222";
    ctx.font = "600 16px Inter, system-ui, sans-serif";
    ctx.fillText("Powered by GiftMe", width / 2, poweredY);

    ctx.fillStyle = "#6b7280";
    ctx.font = "500 15px Inter, system-ui, sans-serif";
    ctx.fillText(siteUrl.replace(/^https?:\/\//i, "").replace(/\/$/, ""), width / 2, poweredY + 24);

    return canvas;
}

async function downloadQrFromBox(boxId, filename, meta = {}) {
    const qrBox = document.getElementById(boxId);
    const qrImage = getQrImageFromBox(qrBox);
    if (!qrImage) return;

    const branding = getQrPosterBranding();
    const url = (qrBox?.dataset.qrUrl || "").trim();
    const poster = await buildQrPoster({
        type: meta.type || "gift",
        url,
        displayName: meta.displayName || "",
        isBirthday: meta.isBirthday === "1" || meta.isBirthday === true,
        qrImage,
        logoUrl: branding.logoUrl,
        siteUrl: branding.siteUrl,
    });

    const link = document.createElement("a");
    link.href = poster.toDataURL("image/png");
    link.download = filename || "giftme-qr.png";
    link.click();
}

function initQrDownload() {
    document.querySelectorAll(".qr-download").forEach((btn) => {
        btn.addEventListener("click", () => {
            downloadQrFromBox(btn.dataset.qrTarget, btn.dataset.qrFilename, {
                type: btn.dataset.qrType,
                displayName: btn.dataset.displayName,
                isBirthday: btn.dataset.isBirthday,
            });
        });
    });
}

function buildWhatsAppShareUrl(url, type, displayName, isBirthday) {
    const name = (displayName || "me").trim();
    let text = "";
    if (type === "wishlist") {
        text = `Hey! Check out my wishlist and help me fulfill a dream: ${url}`;
    } else if (isBirthday) {
        text = `It's my birthday! Send me a gift and make my day special: ${url}`;
    } else {
        text = `I'd love a surprise from you! Send me a gift on GiftMe: ${url}`;
    }
    return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

function initWhatsAppShare() {
    document.querySelectorAll(".dash-share-wa").forEach((btn) => {
        btn.addEventListener("click", () => {
            const url = (btn.dataset.shareUrl || "").trim();
            if (!url) return;
            const shareUrl = buildWhatsAppShareUrl(
                url,
                btn.dataset.shareType,
                btn.dataset.displayName,
                btn.dataset.isBirthday === "1"
            );
            window.open(shareUrl, "_blank", "noopener,noreferrer");
        });
    });
}

function initGiftDetailModal() {
    const modal = document.getElementById("gift-detail-modal");
    if (!modal) return;

    const fields = {
        sender: document.getElementById("gift-detail-sender"),
        gift: document.getElementById("gift-detail-gift"),
        amount: document.getElementById("gift-detail-amount"),
        date: document.getElementById("gift-detail-date"),
        message: document.getElementById("gift-detail-message"),
        messageWrap: document.getElementById("gift-detail-message-wrap"),
    };

    function openModal(data) {
        if (fields.sender) fields.sender.textContent = data.sender || "Anonymous";
        if (fields.gift) fields.gift.textContent = data.gift || "—";
        if (fields.amount) fields.amount.textContent = data.amount ? `KES ${data.amount}` : "—";
        if (fields.date) fields.date.textContent = data.date || "—";
        const hasMessage = Boolean(data.message?.trim());
        if (fields.messageWrap) fields.messageWrap.hidden = !hasMessage;
        if (fields.message) {
            fields.message.textContent = hasMessage ? data.message.trim() : "";
        }
        modal.hidden = false;
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        modal.hidden = true;
        document.body.style.overflow = "";
    }

    document.querySelectorAll(".dash-gift-view").forEach((btn) => {
        btn.addEventListener("click", () => {
            openModal({
                sender: btn.dataset.sender,
                gift: btn.dataset.gift,
                message: btn.dataset.message,
                amount: btn.dataset.amount,
                date: btn.dataset.date,
            });
        });
    });

    modal.querySelectorAll("[data-close-modal='gift-detail-modal']").forEach((el) => {
        el.addEventListener("click", closeModal);
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modal.hidden) closeModal();
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

function initProgressBars() {
    document.querySelectorAll("[data-progress]").forEach((el) => {
        const value = Number(el.dataset.progress);
        if (!Number.isFinite(value)) return;
        el.style.width = `${Math.min(100, Math.max(0, value))}%`;
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
    initGiftDetailModal();
    initWhatsAppShare();
    initProgressBars();
});
