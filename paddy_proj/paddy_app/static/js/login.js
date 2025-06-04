document.addEventListener('DOMContentLoaded', function() {
    // Handle messages (existing functionality)
    setTimeout(function () {
        let messages = document.querySelectorAll('.messages');
        messages.forEach((message) => {
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 100); 
        });
    }, 5000);

    // Main tabs
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            const tabId = button.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });    // Handle signup form dynamic action
    const signupForm = document.getElementById('signupForm');
    const signupRole = document.getElementById('signup-role');
    
    if (signupForm && signupRole) {
        // Set initial form action
        signupForm.action = signupRole.value === 'admin' ? adminSignupUrl : customerSignupUrl;
        
        // Update form action when role changes
        signupRole.addEventListener('change', function() {
            signupForm.action = this.value === 'admin' ? adminSignupUrl : customerSignupUrl;
        });
    }

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const passwordField = form.querySelector('input[type="password"]');
            const confirmPasswordField = form.querySelector('input[name="confirm_password"]');

            if (passwordField && confirmPasswordField) {
                if (passwordField.value !== confirmPasswordField.value) {
                    e.preventDefault();
                    alert('Passwords do not match!');
                }
            }

            const phoneField = form.querySelector('input[type="tel"]');
            if (phoneField && phoneField.value) {
                const phoneRegex = /^\d{10}$/;
                if (!phoneRegex.test(phoneField.value)) {
                    e.preventDefault();
                    alert('Please enter a valid 10-digit phone number');
                }
            }

            const emailField = form.querySelector('input[type="email"]');
            if (emailField && emailField.value) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(emailField.value)) {
                    e.preventDefault();
                    alert('Please enter a valid email address');
                }
            }
        });
    });
});

