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
    
    // Simplified mobile behavior - no overlay, no body overflow blocking
    localStorage.setItem('sidebarOpen', sidebar.classList.contains('open'));
  }

  function initSidebar() {
    const isMobile = window.innerWidth <= 1024;
    const isOpen = !isMobile && localStorage.getItem('sidebarOpen') === 'true';
    
    // Only auto-open sidebar on desktop
    if (isOpen && !isMobile) {
      sidebar.classList.add('open');
      hamburger.classList.add('active');
      body.classList.add('sidebar-open');
    } else {
      // Always close sidebar on mobile by default
      if (isMobile) {
        sidebar.classList.remove('open');
        hamburger.classList.remove('active');
        body.classList.remove('sidebar-open');
      }
    }

    hamburger.addEventListener('click', toggleSidebar);
    
    // Simplified click outside to close - only on mobile and doesn't use overlay
    document.addEventListener('click', function(e) {
      if (
        window.innerWidth <= 992 &&
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !hamburger.contains(e.target)
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
            const menuKey = parentMenu.querySelector('.nav-text').textContent.trim();            localStorage.setItem(`submenu_${menuKey}`, 'open');
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

  // Auto-close sidebar when navigation link is clicked on mobile
  function addMobileNavHandlers() {
    const navLinks = document.querySelectorAll('.nav-link, .submenu-link');
    
    navLinks.forEach(link => {
      link.addEventListener('click', function() {
        // Close sidebar on mobile when navigating
        if (window.innerWidth <= 992 && sidebar.classList.contains('open')) {
          setTimeout(() => {
            toggleSidebar();
          }, 150); // Small delay to allow navigation to start
        }
      });
    });
  }

  // Init
  initSidebar();
  initSubmenus();
  setActiveMenu();
  initMessages();
  addMobileNavHandlers();
});
