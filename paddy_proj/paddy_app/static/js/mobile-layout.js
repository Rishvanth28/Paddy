// Mobile Layout Enhancement Script
document.addEventListener('DOMContentLoaded', function() {
    function createMobileLayout() {
        const authContainer = document.querySelector('.auth-container');
        const authLeft = document.querySelector('.auth-left');
        
        if (!authContainer || !authLeft) return;
        
        // Check if we're on mobile (viewport width <= 768px)
        if (window.innerWidth <= 768) {
            // Check if mobile image section already exists
            let mobileImageSection = document.querySelector('.mobile-image-section');
            
            if (!mobileImageSection) {
                // Create mobile image section
                mobileImageSection = document.createElement('div');
                mobileImageSection.className = 'mobile-image-section';
                
                // Insert it before the auth-left section
                authContainer.insertBefore(mobileImageSection, authLeft);
            }
            
            // Remove background from auth-left on mobile
            authLeft.style.backgroundImage = 'none';
            authLeft.style.backgroundColor = '#ffffff';
        } else {
            // Remove mobile image section on desktop
            const mobileImageSection = document.querySelector('.mobile-image-section');
            if (mobileImageSection) {
                mobileImageSection.remove();
            }
            
            // Restore desktop styles
            authLeft.style.backgroundImage = '';
            authLeft.style.backgroundColor = '';
        }
    }
    
    // Initial setup
    createMobileLayout();
    
    // Handle window resize
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(createMobileLayout, 250);
    });
    
    // Handle orientation change
    window.addEventListener('orientationchange', function() {
        setTimeout(createMobileLayout, 300);
    });
});
