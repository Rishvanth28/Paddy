document.addEventListener('DOMContentLoaded', function() {
  const sidebar = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');
  const mainContent = document.getElementById('main-content');
  const body = document.body;
  
  // Enhanced sidebar toggle functionality
  function toggleSidebar() {
    sidebar.classList.toggle('open');
    hamburger.classList.toggle('active');
    body.classList.toggle('sidebar-open');
    
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar.classList.contains('open')) {
      overlay.style.display = 'block';
      // Prevent scrolling when sidebar is open on mobile
      if (window.innerWidth <= 1024) {
        body.style.overflow = 'hidden';
      }
    } else {
      overlay.style.display = 'none';
      body.style.overflow = '';
    }
    localStorage.setItem('sidebarOpen', sidebar.classList.contains('open'));
  }

  function initSidebar() {
    const isMobile = window.innerWidth <= 1024;
    const isOpen = !isMobile && localStorage.getItem('sidebarOpen') === 'true';
    const overlay = document.getElementById('sidebar-overlay');
    
    // Only auto-open sidebar on desktop
    if (isOpen && !isMobile) {
      sidebar.classList.add('open');
      hamburger.classList.add('active');
      body.classList.add('sidebar-open');
      overlay.style.display = 'block';
    } else {
      overlay.style.display = 'none';
      // Always close sidebar on mobile by default
      if (isMobile) {
        sidebar.classList.remove('open');
        hamburger.classList.remove('active');
        body.classList.remove('sidebar-open');
      }
    }

    hamburger.addEventListener('click', toggleSidebar);
    overlay.addEventListener('click', function() {
      if (sidebar.classList.contains('open')) {
        toggleSidebar();
      }
    });

    document.addEventListener('click', function(e) {
      if (
        window.innerWidth <= 992 &&
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        e.target !== hamburger &&
        e.target !== overlay
      ) {
        toggleSidebar();
      }
    });
  }

  function initSubmenus() {
    const submenuToggles = document.querySelectorAll('.submenu-toggle');

    submenuToggles.forEach(toggle => {
      const parentItem = toggle.closest('.has-submenu');
      const menuKey = parentItem.querySelector('.nav-text').textContent.trim();

      const savedState = localStorage.getItem(`submenu_${menuKey}`) === 'open';
      if (savedState) parentItem.classList.add('open');

      toggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        parentItem.classList.toggle('open');
        localStorage.setItem(
          `submenu_${menuKey}`,
          parentItem.classList.contains('open') ? 'open' : 'closed'
        );
      });
    });
  }
  function setActiveMenu() {
    const currentPath = window.location.pathname.replace(/\/$/, '');
    const navLinks = document.querySelectorAll('.nav-link, .submenu-link');

    navLinks.forEach(link => {
      const linkPath = new URL(link.href).pathname.replace(/\/$/, '');

      if (linkPath === currentPath) {
        // Remove any previous active states
        document.querySelectorAll('.nav-item.active, .submenu-item.active').forEach(el => {
          el.classList.remove('active');
        });

        const navItem = link.closest('.nav-item');
        const submenuItem = link.closest('.submenu-item');

        if (navItem) {
          navItem.classList.add('active');
        }
        if (submenuItem) {
          submenuItem.classList.add('active');
          const parentMenu = submenuItem.closest('.has-submenu');
          if (parentMenu) {
            parentMenu.classList.add('open');
            const menuKey = parentMenu.querySelector('.nav-text').textContent.trim();
            localStorage.setItem(`submenu_${menuKey}`, 'open');
          }
        }
      }
    });
  }

  function initMessages() {
    const messages = document.querySelectorAll('.messages li');
    if (messages.length > 0) {
      setTimeout(() => {
        messages.forEach(msg => {
          msg.style.opacity = '0';
          setTimeout(() => msg.remove(), 300);
        });
      }, 5000);
    }
  }

  // Init
  initSidebar();
  initSubmenus();
  setActiveMenu();
  initMessages();
});
  function toggleSidebar() {
      const sidebar = document.getElementById('sidebar');
      sidebar.classList.toggle('open');
    }

    window.addEventListener('DOMContentLoaded', () => {
      const currentPath = window.location.pathname;
      const menuItems = document.querySelectorAll('.nav-menu .nav-item');

      menuItems.forEach(item => {
        const link = item.querySelector('a');
        if (link && link.getAttribute('href') === currentPath) {
          item.classList.add('active');
        }
      });
    });