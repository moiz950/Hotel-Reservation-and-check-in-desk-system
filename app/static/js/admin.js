/* ============================================================
   HOTEL RESERVATION & CHECK-IN DESK SYSTEM
   Admin panel interactivity — app/static/js/admin.js
   ============================================================ */

(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {

        /* ---------- Sidebar toggle (mobile) ---------- */
        var sidebarToggle = document.getElementById("sidebarToggle");
        var sidebar = document.getElementById("adminSidebar");

        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener("click", function () {
                sidebar.classList.toggle("open");
            });

            // Close the sidebar when a navigation link is clicked (mobile)
            sidebar.querySelectorAll("a").forEach(function (link) {
                link.addEventListener("click", function () {
                    sidebar.classList.remove("open");
                });
            });

            // Close when clicking outside the sidebar on small screens
            document.addEventListener("click", function (e) {
                if (sidebar.classList.contains("open") &&
                    !sidebar.contains(e.target) &&
                    !sidebarToggle.contains(e.target)) {
                    sidebar.classList.remove("open");
                }
            });
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

        /* ---------- Auto-print for invoice print page ---------- */
        if (document.body.classList.contains("print-page") || document.querySelector(".invoice")) {
            // Give the browser a moment to render fonts/layout before printing
            setTimeout(function () {
                window.print();
            }, 400);
        }

        /* ---------- Confirm dialogs for inline forms ---------- */
        // Templates already use onsubmit="return confirm(...)" — this is a
        // progressive enhancement for any form carrying data-confirm.
        document.querySelectorAll("form[data-confirm]").forEach(function (form) {
            form.addEventListener("submit", function (e) {
                var message = form.getAttribute("data-confirm");
                if (message && !window.confirm(message)) {
                    e.preventDefault();
                }
            });
        });

        /* ---------- Auto-submit selects (status changers) ---------- */
        // Templates use onchange="this.form.submit()" — this is a fallback
        // for any select carrying data-autosubmit.
        document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
            select.addEventListener("change", function () {
                if (select.form) select.form.submit();
            });
        });

        /* ---------- Table row hover helper (visual only) ---------- */
        // No-op placeholder kept for future enhancements.
    });
})();