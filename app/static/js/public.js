/* ============================================================
   HOTEL RESERVATION & CHECK-IN DESK SYSTEM
   Public site interactivity — app/static/js/public.js
   ============================================================ */

(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {

        /* ---------- Mobile navigation toggle ---------- */
        var navToggle = document.getElementById("navToggle");
        var mainNav = document.getElementById("mainNav");

        if (navToggle && mainNav) {
            navToggle.addEventListener("click", function () {
                var expanded = mainNav.classList.toggle("open");
                navToggle.classList.toggle("active");
                navToggle.setAttribute("aria-expanded", expanded ? "true" : "false");
            });

            // Close the mobile menu when a link inside it is clicked
            mainNav.querySelectorAll("a").forEach(function (link) {
                link.addEventListener("click", function () {
                    mainNav.classList.remove("open");
                    navToggle.classList.remove("active");
                    navToggle.setAttribute("aria-expanded", "false");
                });
            });
        }

        /* ---------- Sticky header shadow on scroll ---------- */
        var siteHeader = document.getElementById("siteHeader");
        if (siteHeader) {
            var onScroll = function () {
                if (window.scrollY > 10) {
                    siteHeader.classList.add("scrolled");
                } else {
                    siteHeader.classList.remove("scrolled");
                }
            };
            window.addEventListener("scroll", onScroll, { passive: true });
            onScroll();
        }

        /* ---------- Hero slider ---------- */
        var hero = document.getElementById("heroSlider");
        if (hero) {
            var slides = hero.querySelectorAll(".hero-slide");
            var dots = hero.querySelectorAll(".hero-dot");
            var prevBtn = hero.querySelector(".hero-prev");
            var nextBtn = hero.querySelector(".hero-next");
            var current = 0;
            var timer = null;
            var INTERVAL = 6000;

            function showSlide(index) {
                if (!slides.length) return;
                // Wrap around
                index = (index + slides.length) % slides.length;
                current = index;

                slides.forEach(function (slide, i) {
                    slide.classList.toggle("active", i === current);
                });
                dots.forEach(function (dot, i) {
                    dot.classList.toggle("active", i === current);
                });
            }

            function nextSlide() { showSlide(current + 1); }
            function prevSlide() { showSlide(current - 1); }

            function startAuto() {
                stopAuto();
                if (slides.length > 1) {
                    timer = setInterval(nextSlide, INTERVAL);
                }
            }

            function stopAuto() {
                if (timer) {
                    clearInterval(timer);
                    timer = null;
                }
            }

            // Dots
            dots.forEach(function (dot) {
                dot.addEventListener("click", function () {
                    showSlide(parseInt(dot.getAttribute("data-slide"), 10) || 0);
                    startAuto(); // reset timer
                });
            });

            // Arrows
            if (prevBtn) {
                prevBtn.addEventListener("click", function () {
                    prevSlide();
                    startAuto();
                });
            }
            if (nextBtn) {
                nextBtn.addEventListener("click", function () {
                    nextSlide();
                    startAuto();
                });
            }

            // Pause on hover, resume on leave
            hero.addEventListener("mouseenter", stopAuto);
            hero.addEventListener("mouseleave", startAuto);

            // Touch swipe support
            var touchStartX = 0;
            hero.addEventListener("touchstart", function (e) {
                touchStartX = e.changedTouches[0].screenX;
            }, { passive: true });
            hero.addEventListener("touchend", function (e) {
                var diff = e.changedTouches[0].screenX - touchStartX;
                if (Math.abs(diff) > 50) {
                    if (diff < 0) { nextSlide(); } else { prevSlide(); }
                    startAuto();
                }
            }, { passive: true });

            startAuto();
        }

        /* ---------- Flash message dismissal ---------- */
        var flashCloseButtons = document.querySelectorAll(".flash-close");
        flashCloseButtons.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var flash = btn.closest(".flash");
                if (flash) {
                    flash.style.transition = "opacity 0.3s ease, transform 0.3s ease";
                    flash.style.opacity = "0";
                    flash.style.transform = "translateY(-6px)";
                    setTimeout(function () {
                        flash.remove();
                    }, 300);
                }
            });
        });

        // Auto-dismiss success/info flashes after 6 seconds
        document.querySelectorAll(".flash-success, .flash-info").forEach(function (flash) {
            setTimeout(function () {
                if (flash.parentNode) {
                    flash.style.transition = "opacity 0.4s ease";
                    flash.style.opacity = "0";
                    setTimeout(function () {
                        if (flash.parentNode) flash.remove();
                    }, 400);
                }
            }, 6000);
        });

        /* ---------- Reservation date validation ---------- */
        var checkInInput = document.getElementById("check_in");
        var checkOutInput = document.getElementById("check_out");

        function validateDates() {
            if (!checkInInput || !checkOutInput) return;
            if (checkInInput.value && checkOutInput.value) {
                if (checkOutInput.value <= checkInInput.value) {
                    checkOutInput.setCustomValidity("Check-out date must be after check-in date.");
                } else {
                    checkOutInput.setCustomValidity("");
                }
            }
        }

        if (checkInInput) {
            checkInInput.addEventListener("change", function () {
                // Ensure check-out is at least one day after check-in
                if (checkOutInput && checkInInput.value) {
                    var min = new Date(checkInInput.value);
                    min.setDate(min.getDate() + 1);
                    checkOutInput.min = min.toISOString().split("T")[0];
                }
                validateDates();
            });
        }
        if (checkOutInput) {
            checkOutInput.addEventListener("change", validateDates);
        }
        validateDates();

        /* ---------- Smooth scroll for in-page anchors ---------- */
        document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
            anchor.addEventListener("click", function (e) {
                var targetId = anchor.getAttribute("href");
                if (targetId.length > 1) {
                    var target = document.querySelector(targetId);
                    if (target) {
                        e.preventDefault();
                        target.scrollIntoView({ behavior: "smooth", block: "start" });
                    }
                }
            });
        });

        /* ---------- Reveal-on-scroll animation ---------- */
        var revealEls = document.querySelectorAll(".reveal");
        if ("IntersectionObserver" in window && revealEls.length) {
            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("revealed");
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.12 });
            revealEls.forEach(function (el) { observer.observe(el); });
        } else {
            revealEls.forEach(function (el) { el.classList.add("revealed"); });
        }
    });
})();