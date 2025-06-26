document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.querySelector('input[name="q"]');
    const rows = document.querySelectorAll("tbody tr");
    const noAdminsDiv = document.querySelector(".no-results-found");
    const noAdminsDefault = document.querySelector(".no-customers");

    if (!searchInput) return;

    // Prevent Enter key from submitting the form
    searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault(); // Stops page reload or form submission
        }
    });

    searchInput.addEventListener("input", function () {
        const query = this.value.toLowerCase().trim();
        let anyVisible = false;

        rows.forEach(row => {
            const cells = row.querySelectorAll("td");
            const name = cells[1]?.textContent.toLowerCase();
            
            // Only check name column
            const matches = name.includes(query);

            row.style.display = matches ? "" : "none";
            if (matches) anyVisible = true;
        });

        // Hide default message during search
        if (noAdminsDefault) noAdminsDefault.style.display = "none";

        // Show/hide no-results-found
        if (noAdminsDiv) {
            noAdminsDiv.classList.toggle("d-none", anyVisible || !query);
        }
    });
});
