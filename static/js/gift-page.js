document.addEventListener("DOMContentLoaded", () => {
    const heroSticky = document.querySelector(".gift-hero-sticky");
    if (heroSticky) {
        let heroTicking = false;
        const updateHero = () => {
            heroSticky.classList.toggle("is-scrolled", window.scrollY > 8);
            heroTicking = false;
        };
        window.addEventListener(
            "scroll",
            () => {
                if (!heroTicking) {
                    window.requestAnimationFrame(updateHero);
                    heroTicking = true;
                }
            },
            { passive: true }
        );
        updateHero();
    }

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
