document.addEventListener('DOMContentLoaded', function() {
  const sidebar = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');
  const mainContent = document.getElementById('main-content');
  const body = document.body;
    // Enhanced sidebar toggle functionality with smooth animations
  function toggleSidebar() {
    // Use requestAnimationFrame for smoother animations
    requestAnimationFrame(() => {
      sidebar.classList.toggle('open');
      hamburger.classList.toggle('active');
      body.classList.toggle('sidebar-open');
      
      // Simplified mobile behavior - no overlay, no body overflow blocking
      localStorage.setItem('sidebarOpen', sidebar.classList.contains('open'));
    });
  }
  // Initialize with performance optimizations
  function initSidebar() {
    const isMobile = window.innerWidth <= 1024;
    const isOpen = !isMobile && localStorage.getItem('sidebarOpen') === 'true';
    
    // Force hardware acceleration
    sidebar.style.transform = 'translateZ(0)';
    mainContent.style.transform = 'translateZ(0)';
    
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
      // Optimized click outside to close with debouncing
    let clickTimeout;
    document.addEventListener('click', function(e) {
      if (clickTimeout) clearTimeout(clickTimeout);
      
      clickTimeout = setTimeout(() => {
        if (
          window.innerWidth <= 992 &&
          sidebar.classList.contains('open') &&
          !sidebar.contains(e.target) &&
          !hamburger.contains(e.target)
        ) {
          toggleSidebar();
        }
      }, 10); // Small debounce to prevent excessive calls
    });
  }  function initSubmenus() {
    const submenuToggles = document.querySelectorAll('.submenu-toggle');
    const currentPath = window.location.pathname.replace(/\/$/, '');

    submenuToggles.forEach(toggle => {
      const parentItem = toggle.closest('.has-submenu');
      
      // Check if any submenu link in this parent matches current page
      const submenuLinks = parentItem.querySelectorAll('.submenu-link');
      let isCurrentPageInSubmenu = false;
      
      submenuLinks.forEach(submenuLink => {
        const linkPath = new URL(submenuLink.href).pathname.replace(/\/$/, '');
        if (linkPath === currentPath) {
          isCurrentPageInSubmenu = true;
        }
      });
      
      // If current page is not in this submenu, close it by default
      if (!isCurrentPageInSubmenu) {
        parentItem.classList.remove('open');
      }
      // If current page IS in this submenu, it will be opened by setActiveMenu()

      toggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        // Close all other submenus first
        document.querySelectorAll('.has-submenu.open').forEach(openSubmenu => {
          if (openSubmenu !== parentItem) {
            openSubmenu.classList.remove('open');
          }
        });
        
        // Toggle current submenu
        parentItem.classList.toggle('open');
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
          // If user is on a submenu page, keep the parent submenu open
          const parentMenu = submenuItem.closest('.has-submenu');
          if (parentMenu) {
            parentMenu.classList.add('open');
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
  }  // Auto-close sidebar when navigation link is clicked on mobile with smooth transition
  function addMobileNavHandlers() {
    const navLinks = document.querySelectorAll('.nav-link, .submenu-link');
    
    navLinks.forEach(link => {
      link.addEventListener('click', function() {
        // Close sidebar on mobile when navigating with smooth delay
        if (window.innerWidth <= 992 && sidebar.classList.contains('open')) {
          requestAnimationFrame(() => {
            setTimeout(() => {
              toggleSidebar();
            }, 100); // Reduced delay for smoother UX
          });
        }
      });
    });
  }
  // Close submenus when clicking outside
  function addSubmenuClickOutsideHandler() {
    document.addEventListener('click', function(e) {
      const openSubmenus = document.querySelectorAll('.has-submenu.open');
      const currentPath = window.location.pathname.replace(/\/$/, '');
      
      openSubmenus.forEach(submenu => {
        // Check if current page is in this submenu
        const submenuLinks = submenu.querySelectorAll('.submenu-link');
        let isCurrentPageInSubmenu = false;
        
        submenuLinks.forEach(submenuLink => {
          const linkPath = new URL(submenuLink.href).pathname.replace(/\/$/, '');
          if (linkPath === currentPath) {
            isCurrentPageInSubmenu = true;
          }
        });
        
        // If click is outside the submenu and not on a submenu toggle
        // AND current page is not in this submenu, then close it
        if (!submenu.contains(e.target) && 
            !e.target.closest('.submenu-toggle') && 
            !isCurrentPageInSubmenu) {
          submenu.classList.remove('open');
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
  addSubmenuClickOutsideHandler();
});
