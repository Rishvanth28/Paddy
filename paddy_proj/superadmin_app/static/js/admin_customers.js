document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.querySelector('input[name="q"]');
    const rows = document.querySelectorAll("tbody tr");
    const noCustomersDiv = document.querySelector(".no-customers");
    const noResultsFoundDiv = document.querySelector(".no-results-found");

    // Prevent form submission on Enter
    searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault(); // Stops form submission
        }
    });

    searchInput.addEventListener("input", function () {
        const query = this.value.toLowerCase().trim();
        let anyVisible = false;
        let hasCustomerRows = false;

        rows.forEach(row => {
            // Skip the "no-customers" row - it's handled separately
            if (row.classList.contains('no-customers')) {
                return;
            }
            
            hasCustomerRows = true;
            const cells = row.querySelectorAll("td");

            const customerID = cells[0].textContent.toLowerCase();
            const fullName = cells[1].textContent.toLowerCase();
            const email = cells[2].textContent.toLowerCase();
            const phoneNumber = cells[3].textContent.toLowerCase();
            const company = cells[4].textContent.toLowerCase();
            const gst = cells[5].textContent.toLowerCase();

            const matches =
                customerID.includes(query) ||
                fullName.includes(query) ||
                email.includes(query) ||
                phoneNumber.includes(query) ||
                company.includes(query) ||
                gst.includes(query);

            row.style.display = matches ? "" : "none";
            if (matches) anyVisible = true;
        });

        // Handle the display logic
        if (query === "") {
            // When search is empty, show original state
            if (noCustomersDiv) {
                noCustomersDiv.style.display = hasCustomerRows ? "none" : "";
            }
            if (noResultsFoundDiv) {
                noResultsFoundDiv.classList.add("d-none");
            }
        } else {
            // When searching, hide the no-customers message and show no-results if needed
            if (noCustomersDiv) {
                noCustomersDiv.style.display = "none";
            }
            if (noResultsFoundDiv) {
                noResultsFoundDiv.classList.toggle("d-none", anyVisible);
            }
        }
    });
});