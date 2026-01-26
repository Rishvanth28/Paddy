document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.querySelector('input[name="q"]');
    const rows = document.querySelectorAll("tbody tr");
    const noCustomersDiv = document.querySelector(".no-subscribers");
    const noResultsFoundDiv = document.querySelector(".no-results-found");

    // Prevent form submission on Enter
    searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault(); // Stops form submission
        }
    });

    // Search logic
    searchInput.addEventListener("input", function () {
        const query = this.value.toLowerCase().trim();
        let anyVisible = false;

        rows.forEach(row => {
            const cells = row.querySelectorAll("td");

            const customerID = cells[0].textContent.toLowerCase();
            const fullName = cells[1].textContent.toLowerCase();

            const matches =
                customerID.includes(query) ||
                fullName.includes(query);

            row.style.display = matches ? "" : "none";
            if (matches) anyVisible = true;
        });

        if (noCustomersDiv) {
            noCustomersDiv.style.display = "none"; // always hide the default one during search
        }

        if (noResultsFoundDiv) {
            noResultsFoundDiv.classList.toggle("d-none", anyVisible);
        }
    });
});
