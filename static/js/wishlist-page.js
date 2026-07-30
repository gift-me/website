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
