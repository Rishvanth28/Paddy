const toggleItems = document.querySelectorAll('.submenu-toggle');

// Function to update chevron direction
function updateChevron(chevron, isVisible) {
    chevron.style.transform = isVisible ? 'rotate(0deg)' : 'rotate(-90deg)';
}

// Function to set visibility
function setSubmenuVisibility(item, submenu, chevron, isVisible) {
    submenu.style.display = isVisible ? 'block' : 'none';
    updateChevron(chevron, isVisible);

    // Save the state to localStorage
    const key = item.dataset.id;
    if (key) {
        localStorage.setItem(`submenu_open_${key}`, isVisible);
    }
}

// Toggle submenu visibility on click
toggleItems.forEach((item, index) => {
    // Assign a unique data-id if not present
    if (!item.dataset.id) {
        item.dataset.id = `submenu-${index}`;
    }

    item.addEventListener('click', () => {
        const submenu = item.nextElementSibling;
        const chevron = item.querySelector('.chevron');
        const isVisible = submenu.style.display === 'block';

        setSubmenuVisibility(item, submenu, chevron, !isVisible);
    });
});

// On page load
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

    // Set chevron and submenu based on saved visibility
    toggleItems.forEach((item, index) => {
        if (!item.dataset.id) {
            item.dataset.id = `submenu-${index}`;
        }

        const key = item.dataset.id;
        const savedState = localStorage.getItem(`submenu_open_${key}`) === 'true';
        const submenu = item.nextElementSibling;
        const chevron = item.querySelector('.chevron');

        setSubmenuVisibility(item, submenu, chevron, savedState);
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
