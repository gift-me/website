document.addEventListener("DOMContentLoaded", () => {
    const customBtn = document.getElementById("open-custom-gift");

    if (customBtn && window.ContributeModal) {
        customBtn.addEventListener("click", () => {
            window.ContributeModal.open({
                title: "Custom gift",
                showAmount: true,
                submitLabel: "Gift",
            });
        });
    }

    document.querySelectorAll(".gift-card[data-gift-id]").forEach((card) => {
        card.addEventListener("click", () => {
            if (!window.ContributeModal) return;
            window.ContributeModal.open({
                title: card.dataset.giftName || "Send a gift",
                subtitle: `KES ${card.dataset.giftAmount}`,
                giftId: card.dataset.giftId,
                amount: card.dataset.giftAmount,
                showAmount: false,
                submitLabel: "Gift",
            });
        });
    });
});
