(function () {
    const modal = document.getElementById("ops-gift-modal");
    const openAddBtn = document.getElementById("ops-open-add-gift");
    const form = document.getElementById("ops-gift-form");
    const imageInput = document.getElementById("ops-gift-image");
    const preview = document.getElementById("ops-gift-preview");
    const previewWrap = document.getElementById("ops-gift-preview-wrap");
    const modalTitle = document.getElementById("ops-gift-modal-title");
    const modalSub = document.getElementById("ops-gift-modal-sub");
    const submitBtn = document.getElementById("ops-gift-submit");
    const giftIdInput = document.getElementById("ops-gift-id");
    const nameInput = document.getElementById("ops-gift-name");
    const amountInput = document.getElementById("ops-gift-amount");
    const descInput = document.getElementById("ops-gift-description");
    const orderInput = document.getElementById("ops-gift-order");
    const activeInput = document.getElementById("ops-gift-active");
    const imageHint = document.getElementById("ops-gift-image-hint");

    function openModal() {
        if (!modal) return;
        modal.hidden = false;
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        if (!modal) return;
        modal.hidden = true;
        document.body.style.overflow = "";
        if (!modal.dataset.autoOpen) {
            const url = new URL(window.location.href);
            if (url.searchParams.has("edit")) {
                url.searchParams.delete("edit");
                window.history.replaceState({}, "", url.pathname);
            }
        }
    }

    function resetAddForm() {
        if (!form) return;
        form.reset();
        if (giftIdInput) giftIdInput.value = "";
        if (activeInput) activeInput.checked = true;
        if (orderInput) orderInput.value = "0";
        if (imageInput) {
            imageInput.required = true;
            imageInput.value = "";
        }
        if (imageHint) imageHint.textContent = "Required for new gifts.";
        if (preview) preview.removeAttribute("src");
        if (previewWrap) previewWrap.hidden = true;
        if (modalTitle) modalTitle.textContent = "Add gift";
        if (modalSub) modalSub.textContent = "Create a new gift for the public catalog.";
        if (submitBtn) submitBtn.textContent = "Add gift";
    }

    if (openAddBtn) {
        openAddBtn.addEventListener("click", () => {
            resetAddForm();
            openModal();
        });
    }

    document.querySelectorAll("[data-close-gift-modal]").forEach((el) => {
        el.addEventListener("click", closeModal);
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && modal && !modal.hidden) closeModal();
    });

    if (imageInput && preview && previewWrap) {
        imageInput.addEventListener("change", () => {
            const file = imageInput.files?.[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (event) => {
                preview.src = event.target?.result || "";
                previewWrap.hidden = false;
            };
            reader.readAsDataURL(file);
        });
    }

    if (modal?.dataset.autoOpen === "1") {
        openModal();
        if (imageInput) imageInput.required = false;
    }
})();
