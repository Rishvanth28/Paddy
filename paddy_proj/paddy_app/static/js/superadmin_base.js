const toggleItems = document.querySelectorAll('.submenu-toggle');

// Function to update chevron based on submenu visibility
function updateChevron(chevron, isVisible) {
    chevron.style.transform = isVisible ? 'rotate(0deg)' : 'rotate(270deg)';
}

// Toggle submenu visibility
toggleItems.forEach((item) => {
    item.addEventListener('click', () => {
        const submenu = item.nextElementSibling;
        const chevron = item.querySelector('.chevron');

        const isVisible = window.getComputedStyle(submenu).display === 'block';

        submenu.style.display = isVisible ? 'none' : 'block';
        updateChevron(chevron, !isVisible);
    });
});

// On page load, set chevron direction based on visibility
window.addEventListener('DOMContentLoaded', () => {
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll('.menu li');

    // Highlight active menu item
    menuItems.forEach(item => {
        const link = item.querySelector('a');
        if (link && link.getAttribute('href') === currentPath) {
            item.classList.add('active');
        }
    });

    // Hide submenus by default and reset chevron
    toggleItems.forEach((item) => {
        const submenu = item.nextElementSibling;
        const chevron = item.querySelector('.chevron');
        submenu.style.display = 'none'; // hide submenu
        updateChevron(chevron, false);  // chevron down
    });

    // Load preferred language
    const savedLanguage = localStorage.getItem('preferred_language') || 'en';
    document.getElementById('language-select').value = savedLanguage;
    loadTranslations(savedLanguage);
});

// Hamburger toggle
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// Internationalization logic
let translations = {};
let currentLanguage = 'en';

async function changeLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('preferred_language', lang);
    await loadTranslations(lang);
}

async function loadTranslations(lang) {
    try {
        const response = await fetch(`{% static 'js/i18n/' %}${lang}.json`);
        if (!response.ok) {
            console.error(`Failed to load language file: ${lang}.json`);
            return;
        }

        translations = await response.json();
        updatePageText();
    } catch (error) {
        console.error('Error loading translations:', error);
    }
}

function updatePageText() {
    const elements = document.querySelectorAll('.i18n');
    elements.forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[key]) {
            element.textContent = translations[key];
        }
    });
}
