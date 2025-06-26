document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.querySelector('input[name="q"]');
    const rows = document.querySelectorAll("tbody tr");
    const noCustomersDiv = document.querySelector(".no-subscribers");
    const noResultsFoundDiv = document.querySelector(".no-results-found");
    const tableResponsive = document.querySelector(".table-responsive");

    // Add scroll indicators for mobile
    function addScrollIndicators() {
        if (window.innerWidth <= 768 && tableResponsive) {
            const table = tableResponsive.querySelector('table');
            if (table && table.scrollWidth > tableResponsive.clientWidth) {
                // Add scroll indicator
                if (!tableResponsive.querySelector('.scroll-indicator')) {
                    const indicator = document.createElement('div');
                    indicator.className = 'scroll-indicator';
                    indicator.innerHTML = '<i class="fas fa-arrows-alt-h"></i> Scroll horizontally to see more';
                    indicator.style.cssText = `
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        background: rgba(0, 0, 0, 0.7);
                        color: white;
                        padding: 5px 10px;
                        border-radius: 15px;
                        font-size: 0.75rem;
                        z-index: 100;
                        animation: fadeInOut 3s ease-in-out;
                    `;
                    tableResponsive.appendChild(indicator);
                    
                    // Remove indicator after 3 seconds
                    setTimeout(() => {
                        if (indicator.parentNode) {
                            indicator.remove();
                        }
                    }, 3000);
                }
            }
        }
    }

    // Prevent form submission on Enter
    if (searchInput) {
        searchInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault(); // Stops form submission
            }
        });

        // Enhanced search logic with mobile optimization
        searchInput.addEventListener("input", function () {
            const query = this.value.toLowerCase().trim();
            let anyVisible = false;

            rows.forEach(row => {
                const cells = row.querySelectorAll("td");
                
                if (cells.length >= 6) {
                    const customerID = cells[0].textContent.toLowerCase();
                    const fullName = cells[1].textContent.toLowerCase();
                    const paymentAmount = cells[2].textContent.toLowerCase();
                    const status = cells[3].textContent.toLowerCase();
                    const startDate = cells[4].textContent.toLowerCase();
                    const endDate = cells[5].textContent.toLowerCase();

                    const matches =
                        customerID.includes(query) ||
                        fullName.includes(query) ||
                        paymentAmount.includes(query) ||
                        status.includes(query) ||
                        startDate.includes(query) ||
                        endDate.includes(query);

                    row.style.display = matches ? "" : "none";
                    if (matches) anyVisible = true;
                }
            });

            if (noCustomersDiv) {
                noCustomersDiv.style.display = "none"; // always hide the default one during search
            }

            if (noResultsFoundDiv) {
                noResultsFoundDiv.classList.toggle("d-none", anyVisible);
            }

            // Show scroll indicators after search on mobile
            setTimeout(addScrollIndicators, 100);
        });
    }

    // Add scroll indicators on page load
    addScrollIndicators();

    // Re-add scroll indicators on window resize
    window.addEventListener('resize', function() {
        setTimeout(addScrollIndicators, 200);
    });

    // Handle smooth scrolling within the curved container
    if (tableResponsive) {
        tableResponsive.addEventListener('scroll', function() {
            // Add a subtle scroll shadow effect
            const scrollTop = this.scrollTop;
            const scrollLeft = this.scrollLeft;
            
            if (scrollTop > 0) {
                this.classList.add('scrolled-vertical');
            } else {
                this.classList.remove('scrolled-vertical');
            }
            
            if (scrollLeft > 0) {
                this.classList.add('scrolled-horizontal');
            } else {
                this.classList.remove('scrolled-horizontal');
            }
        });
    }
});