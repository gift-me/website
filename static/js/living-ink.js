/**
 * Living Ink — cursor-aware glow + click ripple for CTA surfaces.
 */
(function () {
    const PRIMARY_SELECTORS = [
        ".ink-btn--primary",
        ".cta-primary",
        ".btn.btn-primary",
        "button.btn-primary",
        ".dash-btn-primary",
        ".auth-submit",
        ".btn-next",
        ".gift-modal-submit",
        ".settings-save",
    ].join(", ");

    const SECONDARY_SELECTORS = [
        ".ink-btn--secondary",
        ".btn.btn-outline",
        ".dash-btn-accent",
    ].join(", ");

    const EASE = 0.14;
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function isPrimary(el) {
        return el.matches(PRIMARY_SELECTORS) || el.classList.contains("ink-btn--primary");
    }

    function ensureLayers(el, withRipple) {
        if (!el.querySelector(".ink-btn__glow")) {
            const glow = document.createElement("span");
            glow.className = "ink-btn__glow";
            glow.setAttribute("aria-hidden", "true");
            el.prepend(glow);
        }
        if (withRipple && !el.querySelector(".ink-btn__ripple")) {
            const ripple = document.createElement("span");
            ripple.className = "ink-btn__ripple";
            ripple.setAttribute("aria-hidden", "true");
            el.prepend(ripple);
        }
    }

    function bindInkSurface(el) {
        if (el.dataset.inkInit === "true") return;
        el.dataset.inkInit = "true";

        if (!el.classList.contains("ink-btn")) {
            el.classList.add("ink-btn");
        }

        const primary = isPrimary(el);
        ensureLayers(el, primary && !prefersReducedMotion);

        let glowX = 50;
        let glowY = 50;
        let targetX = 50;
        let targetY = 50;
        let rafId = null;

        function tick() {
            glowX += (targetX - glowX) * EASE;
            glowY += (targetY - glowY) * EASE;
            el.style.setProperty("--ink-x", `${glowX}%`);
            el.style.setProperty("--ink-y", `${glowY}%`);

            if (Math.abs(targetX - glowX) > 0.08 || Math.abs(targetY - glowY) > 0.08) {
                rafId = requestAnimationFrame(tick);
            } else {
                rafId = null;
            }
        }

        function scheduleTick() {
            if (prefersReducedMotion) return;
            if (!rafId) rafId = requestAnimationFrame(tick);
        }

        function setTargetFromEvent(e) {
            const rect = el.getBoundingClientRect();
            if (!rect.width || !rect.height) return;
            targetX = Math.min(100, Math.max(0, ((e.clientX - rect.left) / rect.width) * 100));
            targetY = Math.min(100, Math.max(0, ((e.clientY - rect.top) / rect.height) * 100));
            scheduleTick();
        }

        el.addEventListener("pointerenter", () => {
            if (el.disabled || el.classList.contains("is-disabled")) return;
            el.classList.add("is-ink-hover");
        });

        el.addEventListener("pointerleave", () => {
            el.classList.remove("is-ink-hover", "is-ink-active");
            targetX = 50;
            targetY = 50;
            scheduleTick();
        });

        el.addEventListener("pointermove", (e) => {
            if (!el.classList.contains("is-ink-hover")) return;
            setTargetFromEvent(e);
        });

        el.addEventListener("pointerdown", (e) => {
            if (el.disabled || el.classList.contains("is-disabled")) return;
            el.classList.add("is-ink-active");
            setTargetFromEvent(e);

            if (primary && !prefersReducedMotion) {
                const ripple = el.querySelector(".ink-btn__ripple");
                if (ripple) {
                    const rect = el.getBoundingClientRect();
                    ripple.style.left = `${e.clientX - rect.left}px`;
                    ripple.style.top = `${e.clientY - rect.top}px`;
                    ripple.classList.remove("is-rippling");
                    void ripple.offsetWidth;
                    ripple.classList.add("is-rippling");
                }
            }
        });

        el.addEventListener("pointerup", () => {
            el.classList.remove("is-ink-active");
        });

        el.addEventListener("pointercancel", () => {
            el.classList.remove("is-ink-active");
        });
    }

    function initLivingInk(root) {
        const scope = root || document;
        scope.querySelectorAll(`${PRIMARY_SELECTORS}, ${SECONDARY_SELECTORS}`).forEach(bindInkSurface);
    }

    window.initLivingInk = initLivingInk;

    document.addEventListener("DOMContentLoaded", () => initLivingInk());

    document.addEventListener("htmx:afterSwap", (e) => {
        if (e.detail && e.detail.target) initLivingInk(e.detail.target);
    });
})();
