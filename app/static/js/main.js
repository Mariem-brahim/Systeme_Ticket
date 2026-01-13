/* ============================================================
   Autorité de Régulation — main.js
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  /* ── CSRF : injecter le token dans tous les formulaires POST ── */
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
  if (csrfToken) {
    document.querySelectorAll('form').forEach(function (form) {
      const method = (form.getAttribute('method') || 'get').toLowerCase();
      if (method === 'post' && !form.querySelector('input[name="csrf_token"]')) {
        const input = document.createElement('input');
        input.type  = 'hidden';
        input.name  = 'csrf_token';
        input.value = csrfToken;
        form.appendChild(input);
      }
    });
  }

  /* ── AUTO-DISMISS ALERTS ────────────────────────────────── */
  document.querySelectorAll('.alert[data-auto-dismiss]').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity .4s';
      el.style.opacity    = '0';
      setTimeout(function () { el.remove(); }, 400);
    }, 4500);
  });

  /* ── CONFIRMATION AVANT ACTION SENSIBLE ─────────────────── */
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (!confirm(el.getAttribute('data-confirm'))) e.preventDefault();
    });
  });

  /* ── HAMBURGER MENU ─────────────────────────────────────── */
  const toggle = document.getElementById('navbar-toggle');
  const nav    = document.getElementById('navbar-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      const open = nav.classList.toggle('open');
      toggle.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', open);
    });
    /* Ferme le menu au clic ailleurs */
    document.addEventListener('click', function (e) {
      if (!toggle.contains(e.target) && !nav.contains(e.target)) {
        nav.classList.remove('open');
        toggle.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ── SHOW/HIDE PASSWORD ──────────────────────────────────── */
  document.querySelectorAll('.btn-toggle-password').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const input = btn.closest('.input-password-wrapper').querySelector('input');
      if (!input) return;
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      /* Changer l'icône */
      btn.querySelector('.icon-eye').style.display     = isPassword ? 'none'   : '';
      btn.querySelector('.icon-eye-off').style.display = isPassword ? ''       : 'none';
      btn.setAttribute('aria-label', isPassword ? 'Masquer' : 'Afficher');
    });
  });

  /* ── TOGGLE SPÉCIALITÉ (formulaire admin) ────────────────── */
  const roleSelect      = document.getElementById('role-select');
  const specialiteGroup = document.getElementById('specialite-group');
  const specialiteInput = document.getElementById('specialite');
  if (roleSelect && specialiteGroup) {
    function toggleSpecialite() {
      const isTech = roleSelect.value === 'technicien';
      specialiteGroup.style.display = isTech ? '' : 'none';
      if (specialiteInput) specialiteInput.required = isTech;
    }
    roleSelect.addEventListener('change', toggleSpecialite);
    toggleSpecialite();
  }

  /* ── LIEN ACTIF DANS LA NAVBAR ───────────────────────────── */
  const path = window.location.pathname;
  document.querySelectorAll('.navbar-nav .nav-link').forEach(function (a) {
    const href = a.getAttribute('href');
    if (href && href !== '/' && path.startsWith(href)) a.classList.add('active');
  });

  /* ── COMPTEUR DE CARACTÈRES POUR TEXTAREA ────────────────── */
  document.querySelectorAll('textarea[maxlength]').forEach(function (ta) {
    const max = parseInt(ta.getAttribute('maxlength'));
    let counter = ta.id
      ? document.querySelector('.char-counter[data-for="' + ta.id + '"]')
      : null;
    if (!counter) {
      counter = document.createElement('span');
      counter.className = 'form-hint text-muted';
      ta.parentNode.insertBefore(counter, ta.nextSibling);
    }
    function update() {
      const left = max - ta.value.length;
      counter.textContent = left + ' car. restant' + (left !== 1 ? 's' : '');
      counter.style.color = left < 50 ? 'var(--danger)' : '';
    }
    ta.addEventListener('input', update);
    update();
  });

  /* ── FILTRES : SOUMISSION AUTO ───────────────────────────── */
  document.querySelectorAll('.filter-bar select').forEach(function (sel) {
    sel.addEventListener('change', function () { this.closest('form').submit(); });
  });

});
