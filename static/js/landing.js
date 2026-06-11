function initHeaderScroll() {
    const header = document.querySelector("[data-landing-header]");
    if (!header) return;

    const mobileMenu = document.getElementById("mobile-menu");
    let ticking = false;

    function updateHeader() {
        const scrolled = window.scrollY > 12;
        const menuOpen = mobileMenu && !mobileMenu.hidden;

        if (scrolled || menuOpen) {
            header.classList.remove("header-top");
            header.classList.add("header-glass");
        } else {
            header.classList.add("header-top");
            header.classList.remove("header-glass");
        }
        ticking = false;
    }

    window.addEventListener(
        "scroll",
        () => {
            if (!ticking) {
                window.requestAnimationFrame(updateHeader);
                ticking = true;
            }
        },
        { passive: true }
    );

    updateHeader();
}

function initMobileMenu() {
    const toggle = document.getElementById("mobile-menu-toggle");
    const menu = document.getElementById("mobile-menu");
    const header = document.querySelector("[data-landing-header]");
    if (!toggle || !menu) return;

    const bars = toggle.querySelectorAll(".mobile-bar");

    function setOpen(open) {
        toggle.setAttribute("aria-expanded", String(open));
        document.body.classList.toggle("overflow-hidden", open);

        if (open) {
            menu.hidden = false;
            menu.offsetHeight;
            menu.classList.remove("pointer-events-none", "opacity-0", "border-transparent");
            menu.classList.add(
                "pointer-events-auto",
                "opacity-100",
                "border-line/60",
                "bg-background/95",
                "backdrop-blur-xl"
            );
            bars[0].classList.add("translate-y-0", "rotate-45");
            bars[0].classList.remove("-translate-y-[5px]");
            bars[1].classList.add("opacity-0", "scale-x-0");
            bars[2].classList.add("translate-y-0", "-rotate-45");
            bars[2].classList.remove("translate-y-[5px]");
            if (header) {
                header.classList.remove("header-top");
                header.classList.add("header-glass");
            }
        } else {
            menu.classList.add("pointer-events-none", "opacity-0", "border-transparent");
            menu.classList.remove(
                "pointer-events-auto",
                "opacity-100",
                "border-line/60",
                "bg-background/95",
                "backdrop-blur-xl"
            );
            bars[0].classList.remove("translate-y-0", "rotate-45");
            bars[0].classList.add("-translate-y-[5px]");
            bars[1].classList.remove("opacity-0", "scale-x-0");
            bars[2].classList.remove("translate-y-0", "-rotate-45");
            bars[2].classList.add("translate-y-[5px]");
            window.setTimeout(() => {
                if (toggle.getAttribute("aria-expanded") !== "true") {
                    menu.hidden = true;
                }
            }, 300);
            if (header && window.scrollY <= 12) {
                header.classList.add("header-top");
                header.classList.remove("header-glass");
            }
        }
    }

    toggle.addEventListener("click", () => {
        setOpen(toggle.getAttribute("aria-expanded") !== "true");
    });

    menu.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => setOpen(false));
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
            setOpen(false);
        }
    });
}

function initActiveNav() {
    const links = document.querySelectorAll("[data-nav-link]");
    if (!links.length) return;

    const sections = [];
    links.forEach((link) => {
        const id = link.dataset.navSection;
        if (!id) return;
        const section = document.getElementById(id);
        if (section) sections.push({ id, el: section });
    });

    if (!sections.length) return;

    const linkMap = new Map();
    links.forEach((link) => {
        const id = link.dataset.navSection;
        if (!linkMap.has(id)) linkMap.set(id, []);
        linkMap.get(id).push(link);
    });

    function setActive(id) {
        links.forEach((link) => {
            link.classList.toggle("is-active", link.dataset.navSection === id);
        });
    }

    const observer = new IntersectionObserver(
        (entries) => {
            const visible = entries
                .filter((e) => e.isIntersecting)
                .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
            if (visible.length) {
                setActive(visible[0].target.id);
            }
        },
        { rootMargin: "-40% 0px -45% 0px", threshold: [0, 0.15, 0.4] }
    );

    sections.forEach(({ el }) => observer.observe(el));

    if (window.location.hash) {
        const id = window.location.hash.slice(1);
        if (linkMap.has(id)) setActive(id);
    }
}

function initScrollReveal() {
    const items = document.querySelectorAll(".reveal");
    if (!items.length) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        items.forEach((el) => el.classList.add("is-visible"));
        return;
    }

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    items.forEach((el) => observer.observe(el));
}

function initSmoothScroll() {
    document.querySelectorAll('a[href*="#"]').forEach((anchor) => {
        anchor.addEventListener("click", (e) => {
            const href = anchor.getAttribute("href");
            if (!href || !href.includes("#")) return;

            const hashIndex = href.indexOf("#");
            const id = href.slice(hashIndex);
            if (id === "#") return;

            const onHome = window.location.pathname === "/" || window.location.pathname.endsWith("/");
            const isSamePage = href.startsWith("#") || (href.startsWith(window.location.pathname) && onHome);

            if (!isSamePage && !href.startsWith("#")) return;

            const target = document.querySelector(id);
            if (!target) return;

            e.preventDefault();
            const headerOffset = document.querySelector("[data-landing-header]")?.offsetHeight || 68;
            const top = target.getBoundingClientRect().top + window.scrollY - headerOffset - 16;
            window.scrollTo({ top, behavior: "smooth" });
            history.replaceState(null, "", id);
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initHeaderScroll();
    initMobileMenu();
    initActiveNav();
    initScrollReveal();
    initSmoothScroll();
});
