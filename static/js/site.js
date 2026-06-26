/* Studio Legale Badrane — progressive-enhancement behaviours.
 *
 * Single self-hosted module (CSP `script-src 'self'`, loaded `defer`). Every
 * behaviour is opt-in via a `data-*` hook and a no-op when its hook is absent,
 * so this one file serves every page. Nothing here is required to read the
 * site: forms submit, content shows and links work with JavaScript disabled.
 * All motion honours `prefers-reduced-motion`. No inline styles are written to
 * the DOM as attributes — dynamic values go through the CSSOM (element.style),
 * which CSP does not gate.
 */
(function () {
  "use strict";

  var prefersReduced =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hasIO = "IntersectionObserver" in window;

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  /* 1. Scroll reveal --------------------------------------------------- */
  function initReveal() {
    var els = document.querySelectorAll("[data-reveal]");
    if (!els.length) return;
    if (prefersReduced || !hasIO) {
      for (var i = 0; i < els.length; i++) els[i].classList.add("is-revealed");
      return;
    }
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var el = entry.target;
          var delay = el.getAttribute("data-reveal-delay");
          if (delay) el.style.transitionDelay = delay + "ms";
          el.classList.add("is-revealed");
          io.unobserve(el);
        });
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.06 }
    );
    els.forEach(function (el) { io.observe(el); });
  }

  /* 2. Sticky conversion bar ------------------------------------------ */
  function initStickyCta() {
    var bar = document.querySelector("[data-sticky-cta]");
    if (!bar) return;
    var sentinel = document.querySelector("[data-sticky-cta-sentinel]");
    var cookie = document.getElementById("cookie-consent-banner");
    var dismissed = false;
    var pastHero = !sentinel; // no sentinel → treat as already scrolled past

    // The cookie-consent banner is also bottom-fixed and takes precedence:
    // never show the bar while consent is still pending.
    function cookieUp() { return !!cookie && !cookie.classList.contains("hidden"); }
    function refresh() {
      if (!dismissed && pastHero && !cookieUp()) bar.classList.add("is-visible");
      else bar.classList.remove("is-visible");
    }

    var dismiss = bar.querySelector("[data-sticky-cta-dismiss]");
    if (dismiss) {
      dismiss.addEventListener("click", function () {
        dismissed = true;
        bar.classList.remove("is-visible");
        bar.classList.add("is-dismissed");
      });
    }

    if (sentinel && hasIO) {
      new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            // "Not intersecting" is true both below the fold (not yet reached)
            // and above it (scrolled past). Only the latter — top above the
            // viewport — means the user has scrolled past the hero.
            pastHero = entry.boundingClientRect.top < 0;
          });
          refresh();
        },
        { threshold: 0 }
      ).observe(sentinel);
    }
    if (cookie && "MutationObserver" in window) {
      new MutationObserver(refresh).observe(cookie, { attributes: true, attributeFilter: ["class"] });
    }
    refresh();
  }

  /* 3. Off-canvas drawer (source list) -------------------------------- */
  function initDrawer() {
    var drawer = document.querySelector("[data-drawer]");
    if (!drawer) return;
    var backdrop = document.querySelector("[data-drawer-backdrop]");
    var openers = document.querySelectorAll("[data-drawer-open]");
    var closers = drawer.querySelectorAll("[data-drawer-close]");
    var lastFocus = null;

    function focusable() {
      return drawer.querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
    }
    function onKey(e) {
      if (e.key === "Escape") { close(); return; }
      if (e.key !== "Tab") return;
      var items = focusable();
      if (!items.length) return;
      var first = items[0];
      var last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
      }
    }
    function open() {
      lastFocus = document.activeElement;
      drawer.classList.add("is-open");
      drawer.setAttribute("aria-hidden", "false");
      if (backdrop) backdrop.classList.add("is-open");
      document.body.classList.add("has-drawer-open");
      document.addEventListener("keydown", onKey);
      var items = focusable();
      if (items.length) items[0].focus();
    }
    function close() {
      drawer.classList.remove("is-open");
      drawer.setAttribute("aria-hidden", "true");
      if (backdrop) backdrop.classList.remove("is-open");
      document.body.classList.remove("has-drawer-open");
      document.removeEventListener("keydown", onKey);
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }

    drawer.setAttribute("aria-hidden", "true");
    openers.forEach(function (o) { o.addEventListener("click", open); });
    closers.forEach(function (c) { c.addEventListener("click", close); });
    if (backdrop) backdrop.addEventListener("click", close);
  }

  /* 4. Tooltips -------------------------------------------------------- */
  function initTooltips() {
    var anchors = document.querySelectorAll("[data-tooltip]");
    if (!anchors.length) return;
    var idn = 0;

    anchors.forEach(function (anchor) {
      var text = anchor.getAttribute("data-tooltip");
      if (!text) return;
      var bubble = document.createElement("span");
      bubble.className = "tooltip-bubble";
      bubble.setAttribute("role", "tooltip");
      bubble.id = "tt-" + idn++;
      bubble.textContent = text;
      document.body.appendChild(bubble);
      anchor.setAttribute("aria-describedby", bubble.id);
      if (anchor.tagName === "BUTTON" && !anchor.getAttribute("type")) {
        anchor.setAttribute("type", "button");
      }

      function place() {
        var r = anchor.getBoundingClientRect();
        var top = r.bottom + window.scrollY + 8;
        var left = r.left + window.scrollX;
        bubble.style.top = top + "px";
        // keep inside the viewport horizontally
        var maxLeft = window.scrollX + document.documentElement.clientWidth - bubble.offsetWidth - 12;
        bubble.style.left = Math.max(window.scrollX + 12, Math.min(left, maxLeft)) + "px";
      }
      function open() { place(); bubble.classList.add("is-open"); }
      function hide() { bubble.classList.remove("is-open"); }

      anchor.addEventListener("mouseenter", open);
      anchor.addEventListener("mouseleave", hide);
      anchor.addEventListener("focus", open);
      anchor.addEventListener("blur", hide);
      anchor.addEventListener("keydown", function (e) {
        if (e.key === "Escape") hide();
      });
    });
  }

  /* 5. Wizard progress ------------------------------------------------- */
  function initWizardProgress() {
    var root = document.querySelector("[data-wizard-progress]");
    if (!root) return;
    var form = root.closest("form") || document.querySelector("[data-wizard-form]");
    if (!form) return;
    var bar = root.querySelector("[data-wizard-progress-bar]");
    var label = root.querySelector("[data-wizard-progress-label]");
    var tmpl = label ? label.getAttribute("data-progress-template") || "{pct}%" : "";

    function tracked() {
      // Domain fields that build a fuller picture. They are optional by design,
      // so this measures completeness, not required-validation. Skip hidden,
      // honeypot, CSRF and the consent checkboxes (handled separately).
      return Array.prototype.filter.call(
        form.querySelectorAll("input, select, textarea"),
        function (el) {
          if (el.type === "hidden" || el.type === "checkbox" || el.type === "radio") return false;
          if (el.name === "csrfmiddlewaretoken") return false;
          if (el.closest(".is-honeypot")) return false;
          return true;
        }
      );
    }
    function filled(el) {
      if (el.type === "checkbox" || el.type === "radio") return el.checked;
      return String(el.value || "").trim() !== "";
    }
    function update() {
      var fields = tracked();
      if (!fields.length) return;
      var done = fields.filter(filled).length;
      var pct = Math.round((done / fields.length) * 100);
      if (bar) bar.style.width = pct + "%";
      root.setAttribute("aria-valuenow", String(pct));
      if (label) label.textContent = tmpl.replace("{pct}", pct).replace("{done}", done).replace("{total}", fields.length);
    }

    root.setAttribute("role", "progressbar");
    root.setAttribute("aria-valuemin", "0");
    root.setAttribute("aria-valuemax", "100");
    form.addEventListener("input", update);
    form.addEventListener("change", update);
    update();
  }

  /* 6. Light hero parallax -------------------------------------------- */
  function initParallax() {
    if (prefersReduced) return;
    var els = document.querySelectorAll("[data-parallax]");
    if (!els.length || window.innerWidth < 768) return;
    var ticking = false;
    function frame() {
      var y = window.scrollY;
      els.forEach(function (el) {
        var speed = parseFloat(el.getAttribute("data-parallax")) || 0.15;
        el.style.transform = "translate3d(0," + (y * speed).toFixed(1) + "px,0)";
      });
      ticking = false;
    }
    window.addEventListener(
      "scroll",
      function () {
        if (!ticking) { window.requestAnimationFrame(frame); ticking = true; }
      },
      { passive: true }
    );
  }

  /* 7. Magnetic CTA -------------------------------------------------------
   * A subtle pull of the element toward the cursor. Desktop + fine pointer
   * only (skipped on touch and when the user prefers reduced motion). The
   * transform is written through the CSSOM (element.style), never as an inline
   * HTML attribute, so the strict CSP style-src is respected. */
  function initMagnetic() {
    if (prefersReduced) return;
    if (!(window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches)) return;
    var els = document.querySelectorAll("[data-magnetic]");
    if (!els.length) return;
    els.forEach(function (el) {
      var strength = parseFloat(el.getAttribute("data-magnetic")) || 0.25;
      var max = 8; // cap the displacement so it stays restrained
      function move(e) {
        var r = el.getBoundingClientRect();
        var dx = (e.clientX - (r.left + r.width / 2)) * strength;
        var dy = (e.clientY - (r.top + r.height / 2)) * strength;
        dx = Math.max(-max, Math.min(max, dx));
        dy = Math.max(-max, Math.min(max, dy));
        el.style.transform = "translate(" + dx.toFixed(1) + "px," + dy.toFixed(1) + "px)";
      }
      function reset() { el.style.transform = ""; }
      el.addEventListener("mousemove", move);
      el.addEventListener("mouseleave", reset);
    });
  }

  /* 8. Light 3D tilt ------------------------------------------------------
   * A gentle perspective tilt of a card following the cursor. Same desktop /
   * fine-pointer / reduced-motion guards as the magnetic effect. */
  function initTilt() {
    if (prefersReduced) return;
    if (!(window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches)) return;
    var els = document.querySelectorAll("[data-tilt]");
    if (!els.length) return;
    els.forEach(function (el) {
      var maxDeg = parseFloat(el.getAttribute("data-tilt")) || 5;
      function move(e) {
        var r = el.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5;
        var py = (e.clientY - r.top) / r.height - 0.5;
        var rx = (-py * maxDeg).toFixed(2);
        var ry = (px * maxDeg).toFixed(2);
        el.style.transform = "perspective(900px) rotateX(" + rx + "deg) rotateY(" + ry + "deg)";
      }
      function reset() { el.style.transform = ""; }
      el.addEventListener("mousemove", move);
      el.addEventListener("mouseleave", reset);
    });
  }

  /* 9. Interactive pre-check form (P16) -------------------------------------
   * Progressive enhancement for /precheck/<slug>/: reveals conditional fields
   * (data-precheck-show-if="name:value") and tracks a live completeness bar.
   * No-JS fallback: every field stays visible and the form still submits. */
  function initPrecheckForm() {
    var form = document.querySelector("[data-precheck-form]");
    if (!form) return;
    var progress = form.querySelector("[data-precheck-progress]");
    var bar = form.querySelector("[data-precheck-progress-bar]");
    var label = form.querySelector("[data-precheck-progress-label]");
    if (progress) progress.hidden = false;

    function answered(wrapper) {
      var radios = wrapper.querySelectorAll("input[type=radio]");
      if (radios.length) return Array.prototype.some.call(radios, function (r) { return r.checked; });
      var sel = wrapper.querySelector("select");
      if (sel) return String(sel.value || "").trim() !== "";
      var inp = wrapper.querySelector("input, textarea");
      if (inp) return String(inp.value || "").trim() !== "";
      return false;
    }

    function applyConditionals() {
      var conds = form.querySelectorAll("[data-precheck-show-if]");
      Array.prototype.forEach.call(conds, function (el) {
        var spec = (el.getAttribute("data-precheck-show-if") || "").split(":");
        var name = spec[0];
        var want = spec[1];
        var current = "";
        var checked = form.querySelector("input[name='" + name + "']:checked");
        if (checked) {
          current = checked.value;
        } else {
          var ctrl = form.querySelector("select[name='" + name + "'], input[name='" + name + "']");
          if (ctrl) current = ctrl.value || "";
        }
        el.hidden = current !== want;
      });
    }

    function update() {
      applyConditionals();
      var wrappers = Array.prototype.filter.call(
        form.querySelectorAll(".precheck-field"),
        function (w) { return !w.hidden; }
      );
      if (!wrappers.length) return;
      var done = wrappers.filter(answered).length;
      var pct = Math.round((done / wrappers.length) * 100);
      if (bar) bar.style.width = pct + "%";
      if (label) label.textContent = pct + "%";
    }

    form.addEventListener("input", update);
    form.addEventListener("change", update);
    update();
  }

  ready(function () {
    initReveal();
    initStickyCta();
    initDrawer();
    initTooltips();
    initWizardProgress();
    initParallax();
    initMagnetic();
    initTilt();
    initPrecheckForm();
  });
})();
