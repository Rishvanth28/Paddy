document.addEventListener('DOMContentLoaded', function() {
  // DOM Elements
  const sidebar = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');
  const mainContent = document.getElementById('main-content');
  
  // Toggle sidebar function
  function toggleSidebar() {
    sidebar.classList.toggle('open');
    hamburger.classList.toggle('active');
    localStorage.setItem('sidebarOpen', sidebar.classList.contains('open'));
  }
  
  // Initialize sidebar state
  function initSidebar() {
    const isOpen = localStorage.getItem('sidebarOpen') === 'true';
    if (isOpen) {
      sidebar.classList.add('open');
      hamburger.classList.add('active');
    }
    
    hamburger.addEventListener('click', toggleSidebar);
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
      if (window.innerWidth <= 992 && 
          sidebar.classList.contains('open') &&
          !sidebar.contains(e.target) && 
          e.target !== hamburger) {
        toggleSidebar();
      }
    });
  }
  
  // Submenu functionality
  function initSubmenus() {
    const submenuToggles = document.querySelectorAll('.submenu-toggle');
    
    submenuToggles.forEach(toggle => {
      const parentItem = toggle.closest('.has-submenu');
      const menuKey = parentItem.querySelector('.nav-text').textContent.trim();
      
      // Check saved state
      const savedState = localStorage.getItem(`submenu_${menuKey}`) === 'open';
      if (savedState) parentItem.classList.add('open');
      
      // Add click handler
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
  
  // Active menu item highlighting
  function setActiveMenu() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link, .submenu-link');
    
    navLinks.forEach(link => {
      link.classList.remove('active');
      
      // Compare paths
      const linkPath = new URL(link.href).pathname.replace(/\/$/, '');
      const currentPathClean = currentPath.replace(/\/$/, '');
      
      if (linkPath === currentPathClean) {
        link.classList.add('active');
        
        // Open parent submenu if this is a submenu item
        const submenuItem = link.closest('.submenu-item');
        if (submenuItem) {
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
  
  // Language selector functionality
  function initLanguageSelector() {
    const languageSelect = document.getElementById('language-select');
    const savedLanguage = localStorage.getItem('preferred_language') || 'en';
    languageSelect.value = savedLanguage;
    
    languageSelect.addEventListener('change', function() {
      localStorage.setItem('preferred_language', this.value);
      // Add your language change logic here
      console.log('Language changed to:', this.value);
    });
  }
  
  // Auto-hide messages
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
  
  // Initialize all functionality
  initSidebar();
  initSubmenus();
  setActiveMenu();
  initLanguageSelector();
  initMessages();
});