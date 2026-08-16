/* ==========================================================================
   Prime Paint & Home Services — main.js
   Vanilla JS, no dependencies. Everything degrades gracefully without it.
   ========================================================================== */
(function () {
  'use strict';

  /* ---------------------------------------------------- mobile nav ----- */
  function initNav() {
    var toggle = document.querySelector('.nav-toggle');
    var nav = document.getElementById('site-nav');
    if (!toggle || !nav) return;

    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    // Close the menu after tapping a link (single-page anchors included).
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a') && window.innerWidth < 780) {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });

    // Reset state when resizing up to the desktop layout.
    window.addEventListener('resize', function () {
      if (window.innerWidth >= 780) {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ------------------------------------------- current year in footer -- */
  function initYear() {
    var nodes = document.querySelectorAll('[data-year]');
    var year = String(new Date().getFullYear());
    for (var i = 0; i < nodes.length; i++) nodes[i].textContent = year;
  }

  /* ------------------------------------------ gallery photo fallback --- */
  /* Marks tiles whose image file has not been added yet, so the page never
     shows a broken-image icon. Remove nothing — just drop real photos into
     images/gallery/ using the filenames in gallery.html. */
  function initGalleryFallback() {
    var imgs = document.querySelectorAll('.gallery__item img');
    for (var i = 0; i < imgs.length; i++) {
      (function (img) {
        function flag() {
          var item = img.closest('.gallery__item');
          if (item) item.classList.add('is-missing');
        }
        if (img.complete && img.naturalWidth === 0) flag();
        img.addEventListener('error', flag);
      })(imgs[i]);
    }
  }

  /* --------------------------------------------------- gallery filter -- */
  function initGalleryFilter() {
    var bar = document.querySelector('.filter-bar');
    var items = document.querySelectorAll('.gallery__item');
    if (!bar || !items.length) return;

    bar.addEventListener('click', function (e) {
      var btn = e.target.closest('.filter-btn');
      if (!btn) return;

      var filter = btn.getAttribute('data-filter');
      var buttons = bar.querySelectorAll('.filter-btn');
      for (var i = 0; i < buttons.length; i++) {
        var active = buttons[i] === btn;
        buttons[i].classList.toggle('is-active', active);
        buttons[i].setAttribute('aria-pressed', active ? 'true' : 'false');
      }

      var shown = 0;
      for (var j = 0; j < items.length; j++) {
        var cat = items[j].getAttribute('data-category') || '';
        var match = filter === 'all' || cat === filter;
        items[j].hidden = !match;
        if (match) shown++;
      }

      var count = document.querySelector('[data-gallery-count]');
      if (count) {
        var tpl;
        if (shown === items.length) tpl = count.getAttribute('data-count-all') || 'Showing all {n} projects';
        else if (shown === 1) tpl = count.getAttribute('data-count-one') || 'Showing {n} project';
        else tpl = count.getAttribute('data-count-many') || 'Showing {n} projects';
        count.textContent = tpl.replace('{n}', shown);
      }
    });
  }

  /* ------------------------------------------------- estimate forms ---- */
  /* Handles every Netlify form on the page (contact page + the quick form on
     the home page). Each form submits in the background and swaps itself for
     the thank-you panel named in its data-thanks attribute. Wording comes from
     data-msg-* attributes so the Spanish pages override it without new code. */
  function initEstimateForms() {
    var forms = document.querySelectorAll('form[data-netlify]');

    for (var i = 0; i < forms.length; i++) {
      wireForm(forms[i]);
    }
  }

  function wireForm(form) {
    var status = form.querySelector('.form-status');
    var thanksId = form.getAttribute('data-thanks');
    var thanks = thanksId ? document.getElementById(thanksId) : null;

    function msg(key, fallback) {
      return form.getAttribute('data-msg-' + key) || fallback;
    }

    function setError(field, message) {
      if (!field) return;
      var wrap = field.closest('.field');
      if (!wrap) return;
      var slot = wrap.querySelector('.error');
      wrap.classList.toggle('has-error', !!message);
      if (slot) slot.textContent = message || '';
    }

    function showStatus(text, kind) {
      if (!status) return;
      status.textContent = text;
      status.className = 'form-status is-visible' + (kind ? ' form-status--' + kind : '');
    }

    function digits(value) {
      return value.replace(/\D/g, '');
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var name = form.elements.name;
      var phone = form.elements.phone;
      var email = form.elements.email;
      var ok = true;

      setError(name, '');
      setError(phone, '');
      setError(email, '');

      if (name && !name.value.trim()) {
        setError(name, msg('name', 'Please enter your name.'));
        ok = false;
      }

      var hasPhone = phone ? digits(phone.value).length >= 10 : false;
      var hasEmail = email ? /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()) : false;

      if (phone && email) {
        // either one is enough to reach the customer back
        if (!hasPhone && !hasEmail) {
          setError(phone, msg('contact', 'Add a phone number or an email so we can reply.'));
          ok = false;
        } else {
          if (phone.value.trim() && !hasPhone) {
            setError(phone, msg('phone', 'Please enter a 10-digit phone number.'));
            ok = false;
          }
          if (email.value.trim() && !hasEmail) {
            setError(email, msg('email', 'Please check the email address.'));
            ok = false;
          }
        }
      } else if (phone && !hasPhone) {
        setError(phone, msg('phone', 'Please enter a 10-digit phone number.'));
        ok = false;
      } else if (email && !hasEmail) {
        setError(email, msg('email', 'Please check the email address.'));
        ok = false;
      }

      if (!ok) {
        var bad = form.querySelector('.has-error input, .has-error select, .has-error textarea');
        if (bad) bad.focus();
        return;
      }

      var button = form.querySelector('button[type="submit"]');
      if (button) button.disabled = true;
      showStatus(msg('sending', 'Sending your request…'));

      var body = new URLSearchParams(new FormData(form)).toString();

      fetch(form.getAttribute('action') || window.location.pathname, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body
      }).then(function (res) {
        if (!res.ok) throw new Error('Bad response ' + res.status);
        if (status) status.className = 'form-status';
        form.reset();
        form.hidden = true;
        if (thanks) {
          thanks.hidden = false;
          thanks.focus();
          thanks.scrollIntoView({ block: 'center' });
        }
      }).catch(function () {
        if (button) button.disabled = false;
        showStatus(msg('error',
          'Sorry — that did not go through. Please call 413-486-0396 or message us on Facebook and we will take it from there.'), 'error');
      });
    });
  }

  /* ------------------------------------------------- reveal on scroll -- */
  function initReveal() {
    var items = document.querySelectorAll('.reveal');
    if (!items.length) return;

    if (!('IntersectionObserver' in window)) {
      for (var i = 0; i < items.length; i++) items[i].classList.add('is-in');
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });

    for (var j = 0; j < items.length; j++) io.observe(items[j]);
  }

  function init() {
    initNav();
    initYear();
    initGalleryFallback();
    initGalleryFilter();
    initEstimateForms();
    initReveal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
