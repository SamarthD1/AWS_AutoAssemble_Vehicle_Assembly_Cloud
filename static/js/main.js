// AutoAssemble Vehicle Assembly Portal - Core Logic

// Theme Toggle Functionality
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initModalClosers();
});

// Initialize Theme based on localStorage or system preferences
function initTheme() {
    const themeToggleBtn = document.getElementById("theme-toggle");
    if (!themeToggleBtn) return;

    // Get theme from local storage or default to media preference
    let activeTheme = localStorage.getItem("color-scheme");
    
    if (!activeTheme) {
        // Respect system preference
        activeTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }

    applyTheme(activeTheme);

    // Click handler for toggle button
    themeToggleBtn.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
        const newTheme = currentTheme === "light" ? "dark" : "light";
        applyTheme(newTheme);
        localStorage.setItem("color-scheme", newTheme);
    });

    // Listen for OS system theme updates
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
        if (!localStorage.getItem("color-scheme")) {
            const systemTheme = e.matches ? "dark" : "light";
            applyTheme(systemTheme);
        }
    });
}

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    // Sync the HTML color-scheme meta
    const metaColorScheme = document.querySelector('meta[name="color-scheme"]');
    if (metaColorScheme) {
        metaColorScheme.content = theme === "dark" ? "dark" : "light";
    }
}

// Modal opening/closing logic
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add("show");
        document.body.style.overflow = "hidden"; // Prevent background scroll
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove("show");
        document.body.style.overflow = "auto";
    }
}

function initModalClosers() {
    // Close modal when clicking on close button
    const closeButtons = document.querySelectorAll(".close-btn, .btn-close-modal");
    closeButtons.forEach(btn => {
        btn.addEventListener("click", (e) => {
            const modal = e.target.closest(".modal");
            if (modal) {
                closeModal(modal.id);
            }
        });
    });

    // Close modal when clicking outside content area
    window.addEventListener("click", (e) => {
        if (e.target.classList.contains("modal")) {
            closeModal(e.target.id);
        }
    });
}

// Chart.js initialization helper
function initDashboardCharts(statusData, monthlyData, workloadData) {
    // Theme-aware colors
    const isDark = () => document.documentElement.getAttribute("data-theme") === "dark" || 
                         (!document.documentElement.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);

    const getColors = () => {
        const textMuted = isDark() ? "hsl(210, 15%, 70%)" : "hsl(210, 30%, 40%)";
        const gridColor = isDark() ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.05)";
        return { textMuted, gridColor };
    };

    // 1. Production Status Chart (Doughnut)
    const statusCtx = document.getElementById("statusChart");
    if (statusCtx) {
        const labels = Object.keys(statusData);
        const data = Object.values(statusData);
        
        const colors = {
            'Completed': 'hsl(145, 80%, 40%)',
            'In Progress': 'hsl(205, 90%, 45%)',
            'Quality Check': 'hsl(35, 90%, 45%)',
            'Delayed': 'hsl(355, 80%, 45%)',
            'Planned': 'hsl(210, 20%, 50%)'
        };

        const bgColors = labels.map(label => colors[label] || 'hsl(210, 20%, 50%)');

        const chart = new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: bgColors,
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: getColors().textMuted,
                            font: { family: 'Inter', size: 12 }
                        }
                    }
                }
            }
        });

        // Re-render chart text color on theme toggle
        document.getElementById("theme-toggle")?.addEventListener("click", () => {
            setTimeout(() => {
                const colors = getColors();
                chart.options.plugins.legend.labels.color = colors.textMuted;
                chart.update();
            }, 50);
        });
    }

    // 2. Monthly Production Chart (Bar)
    const monthlyCtx = document.getElementById("monthlyChart");
    if (monthlyCtx) {
        const months = Object.keys(monthlyData);
        const counts = Object.values(monthlyData);

        const chart = new Chart(monthlyCtx, {
            type: 'bar',
            data: {
                labels: months,
                datasets: [{
                    label: 'Vehicles Assembled',
                    data: counts,
                    backgroundColor: 'rgba(20, 110, 220, 0.75)',
                    borderColor: 'rgb(20, 110, 220)',
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: getColors().textMuted, font: { family: 'Inter' } }
                    },
                    y: {
                        grid: { color: getColors().gridColor },
                        ticks: { color: getColors().textMuted, font: { family: 'Inter' }, stepSize: 1 },
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });

        document.getElementById("theme-toggle")?.addEventListener("click", () => {
            setTimeout(() => {
                const colors = getColors();
                chart.options.scales.x.ticks.color = colors.textMuted;
                chart.options.scales.y.ticks.color = colors.textMuted;
                chart.options.scales.y.grid.color = colors.gridColor;
                chart.update();
            }, 50);
        });
    }

    // 3. Employee Workload Chart (Horizontal Bar)
    const workloadCtx = document.getElementById("workloadChart");
    if (workloadCtx) {
        const employeeNames = Object.keys(workloadData);
        const taskCounts = Object.values(workloadData);

        const chart = new Chart(workloadCtx, {
            type: 'bar',
            data: {
                labels: employeeNames,
                datasets: [{
                    label: 'Assigned Active Tasks',
                    data: taskCounts,
                    backgroundColor: 'rgba(220, 140, 20, 0.75)',
                    borderColor: 'rgb(220, 140, 20)',
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { color: getColors().gridColor },
                        ticks: { color: getColors().textMuted, font: { family: 'Inter' }, stepSize: 1 },
                        beginAtZero: true
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: getColors().textMuted, font: { family: 'Inter' } }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });

        document.getElementById("theme-toggle")?.addEventListener("click", () => {
            setTimeout(() => {
                const colors = getColors();
                chart.options.scales.x.ticks.color = colors.textMuted;
                chart.options.scales.x.grid.color = colors.gridColor;
                chart.options.scales.y.ticks.color = colors.textMuted;
                chart.update();
            }, 50);
        });
    }
}
