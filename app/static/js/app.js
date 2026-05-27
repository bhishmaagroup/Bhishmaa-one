// Bhishmaa One - Core App Script

document.addEventListener("DOMContentLoaded", function() {
    // Restore and set theme
    const activeTheme = localStorage.getItem("bhishmaa_theme") || "light";
    document.documentElement.setAttribute("data-theme", activeTheme);
    
    // Auto-close bootstrap alerts after 4s
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 4000);
    });
});

// Theme switcher
function toggleTheme() {
    const root = document.documentElement;
    const currentTheme = root.getAttribute("data-theme") || "light";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    
    root.setAttribute("data-theme", newTheme);
    localStorage.setItem("bhishmaa_theme", newTheme);
}

// Sidebar responsive toggle
function toggleSidebar() {
    const sidebar = document.getElementById("appSidebar");
    if (sidebar) {
        if (window.innerWidth < 992) {
            sidebar.classList.toggle("show-mobile");
        } else {
            sidebar.classList.toggle("collapsed");
        }
    }
}

// Close sidebar on mobile when clicking outside
document.addEventListener("click", function(e) {
    if (window.innerWidth < 992) {
        const sidebar = document.getElementById("appSidebar");
        const toggleBtn = document.getElementById("sidebarToggle");
        if (sidebar && sidebar.classList.contains("show-mobile")) {
            if (!sidebar.contains(e.target) && (!toggleBtn || !toggleBtn.contains(e.target))) {
                sidebar.classList.remove("show-mobile");
            }
        }
    }
});
