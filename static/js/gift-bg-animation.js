/**
 * Soft floating orbs + sparkle particles for gift page backgrounds.
 * Respects prefers-reduced-motion.
 */
(function () {
    const COLORS = {
        primary: [230, 57, 70],
        secondary: [244, 211, 94],
        accent: [42, 157, 143],
        pink: [253, 232, 236],
    };

    function rgba(rgb, alpha) {
        return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${alpha})`;
    }

    function rand(min, max) {
        return min + Math.random() * (max - min);
    }

    class FloatingBg {
        constructor(canvas, profile) {
            this.canvas = canvas;
            this.ctx = canvas.getContext("2d");
            this.profile = profile;
            this.orbs = [];
            this.sparkles = [];
            this.running = false;
            this.frame = 0;
            this._onResize = () => this.resize();
            window.addEventListener("resize", this._onResize);
            this.resize();
            this.seed();
        }

        seed() {
            const { w, h } = this;
            const p = this.profile;

            this.orbs = Array.from({ length: p.orbCount }, () => ({
                x: rand(0, w),
                y: rand(0, h),
                r: rand(p.orbMin, p.orbMax),
                vx: rand(-p.orbSpeed, p.orbSpeed),
                vy: rand(-p.orbSpeed, p.orbSpeed),
                color: p.orbColors[Math.floor(Math.random() * p.orbColors.length)],
                phase: rand(0, Math.PI * 2),
            }));

            this.sparkles = Array.from({ length: p.sparkleCount }, () => this.newSparkle());
        }

        newSparkle() {
            const p = this.profile;
            return {
                x: rand(0, this.w),
                y: rand(0, this.h),
                size: rand(p.sparkleMin, p.sparkleMax),
                speed: rand(p.sparkleSpeedMin, p.sparkleSpeedMax),
                drift: rand(-0.25, 0.25),
                opacity: rand(p.sparkleOpacityMin, p.sparkleOpacityMax),
                twinkle: rand(0, Math.PI * 2),
                color: p.sparkleColors[Math.floor(Math.random() * p.sparkleColors.length)],
                shape: Math.random() > 0.65 ? "rect" : "circle",
            };
        }

        resize() {
            const parent = this.canvas.parentElement;
            if (!parent) return;
            const rect = parent.getBoundingClientRect();
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            this.w = rect.width;
            this.h = rect.height;
            this.canvas.width = Math.max(1, Math.floor(this.w * dpr));
            this.canvas.height = Math.max(1, Math.floor(this.h * dpr));
            this.canvas.style.width = `${this.w}px`;
            this.canvas.style.height = `${this.h}px`;
            this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            if (this.orbs.length) this.seed();
        }

        drawOrb(orb) {
            const pulse = 1 + Math.sin(this.frame * 0.012 + orb.phase) * 0.08;
            const r = orb.r * pulse;
            const g = this.ctx.createRadialGradient(orb.x, orb.y, 0, orb.x, orb.y, r);
            g.addColorStop(0, rgba(orb.color, 0.55));
            g.addColorStop(0.45, rgba(orb.color, 0.18));
            g.addColorStop(1, rgba(orb.color, 0));
            this.ctx.fillStyle = g;
            this.ctx.beginPath();
            this.ctx.arc(orb.x, orb.y, r, 0, Math.PI * 2);
            this.ctx.fill();
        }

        drawSparkle(s) {
            const twinkle = 0.55 + Math.sin(this.frame * 0.05 + s.twinkle) * 0.45;
            this.ctx.fillStyle = rgba(s.color, s.opacity * twinkle);
            if (s.shape === "rect") {
                this.ctx.save();
                this.ctx.translate(s.x, s.y);
                this.ctx.rotate(s.twinkle);
                this.ctx.fillRect(-s.size / 2, -s.size / 4, s.size, s.size / 2);
                this.ctx.restore();
            } else {
                this.ctx.beginPath();
                this.ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
                this.ctx.fill();
            }
        }

        tick() {
            const { w, h, profile: p } = this;
            this.ctx.clearRect(0, 0, w, h);

            this.orbs.forEach((orb) => {
                orb.x += orb.vx;
                orb.y += orb.vy;
                if (orb.x < -orb.r) orb.x = w + orb.r;
                if (orb.x > w + orb.r) orb.x = -orb.r;
                if (orb.y < -orb.r) orb.y = h + orb.r;
                if (orb.y > h + orb.r) orb.y = -orb.r;
                this.drawOrb(orb);
            });

            this.sparkles.forEach((s) => {
                s.y -= s.speed;
                s.x += s.drift;
                if (s.y < -8) {
                    s.y = h + 8;
                    s.x = rand(0, w);
                }
                if (s.x < -8) s.x = w + 8;
                if (s.x > w + 8) s.x = -8;
                this.drawSparkle(s);
            });

            this.frame += 1;
        }

        loop() {
            if (!this.running) return;
            this.tick();
            this._raf = requestAnimationFrame(() => this.loop());
        }

        start() {
            if (this.running) return;
            this.running = true;
            this.loop();
        }

        stop() {
            this.running = false;
            if (this._raf) cancelAnimationFrame(this._raf);
        }

        destroy() {
            this.stop();
            window.removeEventListener("resize", this._onResize);
        }
    }

    const PROFILES = {
        hero: {
            orbCount: 5,
            orbMin: 48,
            orbMax: 110,
            orbSpeed: 0.22,
            orbColors: [COLORS.primary, COLORS.secondary, COLORS.accent, COLORS.pink],
            sparkleCount: 18,
            sparkleMin: 1,
            sparkleMax: 2.8,
            sparkleSpeedMin: 0.15,
            sparkleSpeedMax: 0.45,
            sparkleOpacityMin: 0.15,
            sparkleOpacityMax: 0.45,
            sparkleColors: [COLORS.primary, COLORS.secondary, COLORS.accent],
        },
        catalog: {
            orbCount: 0,
            orbMin: 60,
            orbMax: 140,
            orbSpeed: 0.1,
            orbColors: [COLORS.secondary, COLORS.pink, COLORS.accent],
            sparkleCount: 22,
            sparkleMin: 0.8,
            sparkleMax: 2.2,
            sparkleSpeedMin: 0.08,
            sparkleSpeedMax: 0.28,
            sparkleOpacityMin: 0.1,
            sparkleOpacityMax: 0.35,
            sparkleColors: [COLORS.primary, COLORS.secondary, COLORS.accent],
        },
    };

    function init() {
        const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const instances = [];

        document.querySelectorAll("[data-gift-bg]").forEach((canvas) => {
            const key = canvas.dataset.giftBg;
            const profile = PROFILES[key];
            if (!profile) return;
            const anim = new FloatingBg(canvas, profile);
            instances.push(anim);
            if (!reduced) anim.start();
        });

        window.addEventListener("beforeunload", () => instances.forEach((i) => i.destroy()));
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
