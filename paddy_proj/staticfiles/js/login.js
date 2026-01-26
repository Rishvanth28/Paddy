document.addEventListener('DOMContentLoaded', function() {
    // Toast messages are now handled in login.html directly
    // Removed automatic message removal to avoid conflicts with toast system

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
        });    });

    // Handle signup form dynamic action
    const signupForm = document.getElementById('signupForm');
    const signupRole = document.getElementById('signup-role');
      if (signupForm && signupRole) {
        const customerFields = document.getElementById('customer-fields');
        const companyField = document.getElementById('signup-company');
        const addressField = document.getElementById('signup-address');
        
        function updateFormForRole(role) {
            // Update form action
            signupForm.action = role === 'admin' ? adminSignupUrl : customerSignupUrl;
            
            // Toggle customer fields visibility
            if (customerFields) {
                customerFields.style.display = role === 'customer' ? 'block' : 'none';
                
                // Update required attributes for customer fields
                if (companyField) companyField.required = role === 'customer';
                if (addressField) addressField.required = role === 'customer';
            }
        }
        
        // Set initial state
        updateFormForRole(signupRole.value);
        
        // Update when role changes
        signupRole.addEventListener('change', function() {
            updateFormForRole(this.value);
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

