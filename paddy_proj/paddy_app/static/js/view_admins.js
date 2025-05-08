document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.querySelector('input[name="q"]');
    const rows = document.querySelectorAll("tbody tr");
    const noAdminsDiv = document.querySelector(".no-results-found");
    const noAdminsDefault = document.querySelector(".no-customers");

    if (!searchInput) return;

    searchInput.addEventListener("input", function () {
        const query = this.value.toLowerCase().trim();
        let anyVisible = false;

        rows.forEach(row => {
            const cells = row.querySelectorAll("td");
            const adminId = cells[0]?.textContent.toLowerCase();
            const name = cells[1]?.textContent.toLowerCase();
            const email = cells[2]?.textContent.toLowerCase();
            const phone = cells[3]?.textContent.toLowerCase();

            const matches =
                adminId.includes(query) ||
                name.includes(query) ||
                email.includes(query) ||
                phone.includes(query);

            if (matches) {
                row.style.display = "";
                anyVisible = true;
            } else {
                row.style.display = "none";
            }
        });

        // Hide default message during search
        if (noAdminsDefault) noAdminsDefault.style.display = "none";

        // Show/hide no-results-found
        if (noAdminsDiv) {
            if (query && !anyVisible) {
                noAdminsDiv.classList.remove("d-none");
            } else {
                noAdminsDiv.classList.add("d-none");
            }
        }
    });
});
