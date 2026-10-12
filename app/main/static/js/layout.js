// ── Sidebar collapse ──────────────────────────────────────────
const body       = document.body;
const toggleBtn  = document.getElementById('sidebarToggle');
const toggleIcon = document.getElementById('toggleIcon');
const mobileBtn  = document.getElementById('mobileMenuBtn');
const backButton = document.getElementById('sidebarBackButton');

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

// ── Botón volver ────────────────────────────────────────────────


backButton?.addEventListener('click', () => {
  const dashboardUrl = backButton.dataset.dashboardUrl;
  const previousPage = document.referrer;

  const isInternalPage =
    previousPage &&
    previousPage.startsWith(window.location.origin);

  if (isInternalPage && window.history.length > 1) {
    window.history.back();
    return;
  }

  window.location.href = dashboardUrl;
});

// ── Notificaciones ─────────────────────────────────────────────

const notificationTrigger =
  document.getElementById('notificationTrigger');

const notificationDropdown =
  document.getElementById('notificationDropdown');

const notificationCount =
  document.getElementById('notificationCount');

const notificationReadAll =
  document.getElementById('notificationReadAll');


notificationTrigger?.addEventListener('click', (event) => {

  event.stopPropagation();

  notificationDropdown?.classList.toggle('open');

  // Cerrar menú de usuario si está abierto
  userDropdown?.classList.remove('open');
});


notificationDropdown?.addEventListener('click', (event) => {
  event.stopPropagation();
});


document.addEventListener('click', () => {
  notificationDropdown?.classList.remove('open');
});


function actualizarContadorNotificaciones(cantidad) {

  if (!notificationCount) {
    return;
  }

  if (cantidad > 0) {

    notificationCount.textContent = cantidad;
    notificationCount.style.display = 'flex';

  } else {

    notificationCount.textContent = '';
    notificationCount.style.display = 'none';
  }
}


document
  .querySelectorAll('.notification-mark-read')
  .forEach(button => {

    button.addEventListener('click', async (event) => {

      event.stopPropagation();

      const url = button.dataset.url;

      if (!url) {
        return;
      }

      try {

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
          }
        });

        if (!response.ok) {
          throw new Error(
            'No se pudo marcar la notificación como leída.'
          );
        }

        const data = await response.json();

        const notificationItem =
          button.closest('.notification-item');

        notificationItem?.classList.remove('unread');

        button.remove();

        actualizarContadorNotificaciones(
          data.pendientes
        );

        if (data.pendientes === 0) {
          notificationReadAll?.remove();
        }

      } catch (error) {

        console.error(
          'Error al marcar notificación:',
          error
        );
      }
    });
  });


notificationReadAll?.addEventListener(
  'click',
  async (event) => {

    event.stopPropagation();

    const url = notificationReadAll.dataset.url;

    if (!url) {
      return;
    }

    try {

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest'
        }
      });

      if (!response.ok) {
        throw new Error(
          'No se pudieron marcar las notificaciones.'
        );
      }

      document
        .querySelectorAll('.notification-item.unread')
        .forEach(item => {
          item.classList.remove('unread');
        });


      document
        .querySelectorAll('.notification-mark-read')
        .forEach(button => {
          button.remove();
        });


      actualizarContadorNotificaciones(0);

      notificationReadAll.remove();

    } catch (error) {

      console.error(
        'Error al marcar todas las notificaciones:',
        error
      );
    }
  }
);

// ── Toast de notificación ─────────────────────────────────────

const notificationToast =
  document.getElementById('notificationToast');

const notificationToastClose =
  document.getElementById('notificationToastClose');


function cerrarNotificationToast() {

  if (!notificationToast) {
    return;
  }

  notificationToast.classList.add('hide');

  setTimeout(() => {
    notificationToast.remove();
  }, 250);
}


notificationToastClose?.addEventListener(
  'click',
  cerrarNotificationToast
);


if (notificationToast) {

  setTimeout(() => {
    cerrarNotificationToast();
  }, 8000);

}