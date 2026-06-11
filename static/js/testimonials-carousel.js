(function () {
    function initTestimonialsCarousel() {
        const carousel = document.querySelector("[data-testimonials-carousel]");
        if (!carousel || carousel.dataset.carouselReady === "true") return;
        carousel.dataset.carouselReady = "true";

        const slides = Array.from(carousel.querySelectorAll(".testimonial-slide"));
        const dots = Array.from(carousel.querySelectorAll("[data-carousel-dot]"));
        if (slides.length < 2) return;

        let index = slides.findIndex((slide) => slide.classList.contains("is-active"));
        if (index < 0) index = 0;

        let timer = null;
        const intervalMs = 3000;
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        function updateUI() {
            slides.forEach((slide, slideIndex) => {
                const isActive = slideIndex === index;
                slide.classList.toggle("is-active", isActive);
                slide.setAttribute("aria-hidden", String(!isActive));
            });

            dots.forEach((dot, dotIndex) => {
                const isActive = dotIndex === index;
                dot.classList.toggle("is-active", isActive);
                dot.setAttribute("aria-selected", String(isActive));
            });
        }

        function goTo(nextIndex) {
            index = (nextIndex + slides.length) % slides.length;
            updateUI();
        }

        function next() {
            goTo(index + 1);
        }

        function prev() {
            goTo(index - 1);
        }

        function stopAutoplay() {
            if (timer !== null) {
                window.clearInterval(timer);
                timer = null;
            }
        }

        function startAutoplay() {
            if (reducedMotion) return;
            stopAutoplay();
            timer = window.setInterval(next, intervalMs);
        }

        carousel.addEventListener("click", (event) => {
            if (event.target.closest("[data-carousel-prev]")) {
                event.preventDefault();
                prev();
                startAutoplay();
                return;
            }

            if (event.target.closest("[data-carousel-next]")) {
                event.preventDefault();
                next();
                startAutoplay();
                return;
            }

            const dot = event.target.closest("[data-carousel-dot]");
            if (dot) {
                event.preventDefault();
                const targetIndex = Number(dot.getAttribute("data-carousel-dot"));
                if (!Number.isNaN(targetIndex)) {
                    goTo(targetIndex);
                    startAutoplay();
                }
            }
        });

        carousel.addEventListener("mouseenter", stopAutoplay);
        carousel.addEventListener("mouseleave", startAutoplay);

        updateUI();
        startAutoplay();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initTestimonialsCarousel);
    } else {
        initTestimonialsCarousel();
    }
})();
