document.addEventListener("DOMContentLoaded", function() {
    const selects = document.querySelectorAll(".status-select");
    
    selects.forEach(select => {
        select.addEventListener("change", function() {
            const userId = this.dataset.userId;
            const targetDate = this.dataset.date;
            const newStatus = this.value;
            
            const tr = this.closest("tr");
            const spinner = tr.querySelector(".loader-spinner");
            const successCheck = tr.querySelector(".status-msg");
            const badgeContainer = tr.querySelector(".badge-indicator-container");
            
            // Show spinner
            spinner.classList.remove("d-none");
            successCheck.classList.add("d-none");
            
            const payload = {
                user_id: userId,
                status: newStatus,
                date: targetDate
            };
            
            fetch(QUICK_LOG_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": CSRF_TOKEN
                },
                body: JSON.stringify(payload)
            })
            .then(res => res.json().then(data => ({ status: res.status, body: data })))
            .then(res => {
                spinner.classList.add("d-none");
                if (res.status === 200) {
                    successCheck.classList.remove("d-none");
                    setTimeout(() => {
                        successCheck.classList.add("d-none");
                    }, 2000);
                    
                    // Update status label badge
                    updateBadge(badgeContainer, newStatus);
                } else {
                    alert("Error: " + (res.body.error || "Failed to save attendance logs."));
                }
            })
            .catch(err => {
                spinner.classList.add("d-none");
                console.error("Attendance update failed:", err);
                alert("Failed to connect to the server.");
            });
        });
    });
    
    function updateBadge(container, status) {
        container.innerHTML = "";
        let badgeClass = "bg-light text-muted border";
        let label = status;
        
        if (status === "Present") {
            badgeClass = "bg-success-light text-success";
        } else if (status === "Absent") {
            badgeClass = "bg-danger-light text-danger";
        } else if (status === "Half-Day") {
            badgeClass = "bg-warning-light text-warning";
        } else if (status === "Late") {
            badgeClass = "bg-orange-light text-orange";
            label = "Late Arrival";
        } else if (status === "On-Leave") {
            badgeClass = "bg-info-light text-info";
            label = "On Leave";
        }
        
        container.innerHTML = `<span class="badge ${badgeClass} rounded-pill px-2.5">${label}</span>`;
    }
});
