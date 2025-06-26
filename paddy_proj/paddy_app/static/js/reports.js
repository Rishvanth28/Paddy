/**
 * Reports Module JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Handle filter reset
    const resetButton = document.getElementById('reset-filters');
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            const form = document.getElementById('report-filter-form');
            const selects = form.querySelectorAll('select');
            const dates = form.querySelectorAll('input[type="date"]');
            
            selects.forEach(select => select.value = '');
            dates.forEach(date => date.value = '');
            
            form.submit();
        });
    }
    
    // Handle date preset changes
    const datePresetDropdown = document.getElementById('date_preset');
    const startDateField = document.getElementById('start_date');
    const endDateField = document.getElementById('end_date');
    const dateFields = document.querySelectorAll('.date-field');
    
    if (datePresetDropdown) {
        // Show/hide date fields based on initial selection
        updateDateFieldsVisibility(datePresetDropdown.value);
        
        // Handle changes to date preset
        datePresetDropdown.addEventListener('change', function() {
            const selectedPreset = this.value;
            updateDateFieldsVisibility(selectedPreset);
            
            if (selectedPreset && selectedPreset !== '') {
                // Set date values based on preset
                const dates = calculateDateRange(selectedPreset);
                if (dates) {
                    startDateField.value = dates.startDate;
                    endDateField.value = dates.endDate;
                }
            }
        });
    }
    
    function updateDateFieldsVisibility(selectedPreset) {
        if (selectedPreset === '' || selectedPreset === null) {
            // Show custom date fields for custom range
            dateFields.forEach(field => {
                field.style.display = 'flex';
            });
        } else {
            // Hide custom date fields for preset ranges
            dateFields.forEach(field => {
                field.style.display = 'none';
            });
        }
    }
    
    function calculateDateRange(preset) {
        const today = new Date();
        let startDate = new Date(today);
        let endDate = new Date(today);
        
        switch(preset) {
            case 'today':
                // Start and end are both today
                break;
                
            case 'yesterday':
                startDate.setDate(today.getDate() - 1);
                endDate.setDate(today.getDate() - 1);
                break;
                
            case 'last_7_days':
                startDate.setDate(today.getDate() - 6);
                break;
                
            case 'last_30_days':
                startDate.setDate(today.getDate() - 29);
                break;
                
            case 'last_3_months':
                startDate.setMonth(today.getMonth() - 3);
                break;
                
            case 'last_6_months':
                startDate.setMonth(today.getMonth() - 6);
                break;
                
            case 'last_year':
                startDate.setFullYear(today.getFullYear() - 1);
                break;
                
            default:
                return null;
        }
        
        return {
            startDate: formatDate(startDate),
            endDate: formatDate(endDate)
        };
    }
    
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    // Fix export links to include current parameters
    const exportLinks = document.querySelectorAll('.btn-export');
    exportLinks.forEach(link => {
        const currentUrl = new URL(link.href);
        const urlParams = new URLSearchParams(window.location.search);
        
        // Skip the export parameter itself
        for (const [key, value] of urlParams.entries()) {
            if (key !== 'export') {
                currentUrl.searchParams.set(key, value);
            }
        }
        
        link.href = currentUrl.toString();
        
        // Add animation and icons to export buttons
        if (link.classList.contains('excel')) {
            link.innerHTML = '<i class="fas fa-file-excel"></i> Export to Excel';
        } else if (link.classList.contains('pdf')) {
            link.innerHTML = '<i class="fas fa-file-pdf"></i> Export to PDF';
        }
    });
    
    // Dynamic table functionality - sorting
    const tableHeaders = document.querySelectorAll('.reports-table th[data-sort]');
    tableHeaders.forEach(header => {
        // Add sort indicator and styling
        header.classList.add('sortable');
        
        // Check if this header is the currently sorted one
        const currentSortField = new URLSearchParams(window.location.search).get('sort');
        const currentSortDir = new URLSearchParams(window.location.search).get('dir') || 'asc';
        
        if (currentSortField === header.getAttribute('data-sort')) {
            header.classList.add(currentSortDir === 'asc' ? 'sort-asc' : 'sort-desc');
        }
        
        header.addEventListener('click', function() {
            const sortField = this.getAttribute('data-sort');
            const isAsc = this.classList.contains('sort-asc');
            
            // Clear sorting classes from all headers
            tableHeaders.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            
            // Set new sort direction
            this.classList.add(isAsc ? 'sort-desc' : 'sort-asc');
            
            // Get current URL and update sort parameters
            const url = new URL(window.location);
            url.searchParams.set('sort', sortField);
            url.searchParams.set('dir', isAsc ? 'desc' : 'asc');
            
            // Navigate to the new URL
            window.location.href = url.toString();
        });
    });
    
    // Add row highlighting on click
    const tableRows = document.querySelectorAll('.reports-table tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', function() {
            // Remove highlight from all rows
            tableRows.forEach(r => r.classList.remove('row-highlight'));
            
            // Add highlight to clicked row
            this.classList.add('row-highlight');
        });
    });
    
    // Add animation to page elements
    animatePageElements();
});

// Function to add subtle animations to page elements
function animatePageElements() {
    // Add a subtle fade-in animation to the report containers
    const containers = document.querySelectorAll('.reports-table-container');
    containers.forEach((container, index) => {
        container.style.opacity = '0';
        container.style.transform = 'translateY(20px)';
        container.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        
        setTimeout(() => {
            container.style.opacity = '1';
            container.style.transform = 'translateY(0)';
        }, 100 + (index * 150));
    });
}

// Add custom CSS for row highlighting
const style = document.createElement('style');
style.textContent = `
    .row-highlight {
        background-color: #e8f4fc !important;
        box-shadow: 0 0 5px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
    }
    
    .reports-table th.sortable {
        cursor: pointer;
        position: relative;
        padding-right: 25px;
    }
    
    .reports-table th.sortable::after {
        content: "↕";
        position: absolute;
        right: 8px;
        color: rgba(255,255,255,0.7);
    }
    
    .reports-table th.sort-asc::after {
        content: "↑";
        color: white;    }
    
    .reports-table th.sort-desc::after {
        content: "↓";
        color: white;
    }
`;
document.head.appendChild(style);
