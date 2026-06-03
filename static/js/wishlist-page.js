document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".wishlist-item-btn[data-wishlist-id]").forEach((btn) => {
        btn.addEventListener("click", () => {
            if (!window.ContributeModal) return;
            window.ContributeModal.open({
                title: btn.dataset.wishlistTitle || "Contribute",
                subtitle: `Goal: KES ${btn.dataset.wishlistTarget}`,
                wishlistId: btn.dataset.wishlistId,
                showAmount: true,
                submitLabel: "Fulfill my wish",
            });
        });
    });
});
