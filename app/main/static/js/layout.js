// ── Sidebar collapse ──────────────────────────────────────────
const body       = document.body;
const toggleBtn  = document.getElementById('sidebarToggle');
const toggleIcon = document.getElementById('toggleIcon');
const mobileBtn  = document.getElementById('mobileMenuBtn');

if (localStorage.getItem('sidebarCollapsed') === 'true') {
  body.classList.add('sidebar-collapsed');
  toggleIcon?.classList.replace('ti-chevrons-left', 'ti-chevrons-right');
}

toggleBtn?.addEventListener('click', () => {
  const collapsed = body.classList.toggle('sidebar-collapsed');
  toggleIcon?.classList.toggle('ti-chevrons-left', !collapsed);
  toggleIcon?.classList.toggle('ti-chevrons-right', collapsed);
  localStorage.setItem('sidebarCollapsed', collapsed);
});

// ── Mobile sidebar ────────────────────────────────────────────
mobileBtn?.addEventListener('click', (e) => {
  e.stopPropagation();
  body.classList.toggle('mobile-open');
});

body.addEventListener('click', (e) => {
  if (body.classList.contains('mobile-open')) {
    const sidebar = document.getElementById('sidebar');
    if (sidebar && !sidebar.contains(e.target) && e.target !== mobileBtn) {
      body.classList.remove('mobile-open');
    }
  }
});

// ── User dropdown ─────────────────────────────────────────────
const userTrigger  = document.getElementById('userMenuTrigger');
const userDropdown = document.getElementById('userDropdown');

userTrigger?.addEventListener('click', (e) => {
  e.stopPropagation();
  userDropdown?.classList.toggle('open');
});

document.addEventListener('click', (e) => {
  if (userDropdown && !userDropdown.contains(e.target)) {
    userDropdown.classList.remove('open');
  }
});

// ── Selector de Cliente Activo (RF9) ─────────────────────────
function switchClient(clientId) {
  if (!clientId) return;

  fetch('/select-client/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({ client_id: clientId })
  })
  .then(response => {
    if (response.ok) {
      window.location.reload();
    } else {
      console.error('Error al cambiar de cliente activo');
    }
  })
  .catch(error => console.error('Error de red:', error));
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}