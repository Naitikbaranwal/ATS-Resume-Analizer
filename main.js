// Main JS
document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss alert notifications after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s ease';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
    // Theme Toggle Handler
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    
    if (themeToggleBtn && themeIcon) {
        // Update button icon based on current state
        updateThemeIcon();

        themeToggleBtn.addEventListener('click', () => {
            if (document.documentElement.classList.contains('dark-theme')) {
                document.documentElement.classList.remove('dark-theme');
                localStorage.setItem('theme', 'light');
            } else {
                document.documentElement.classList.add('dark-theme');
                localStorage.setItem('theme', 'dark');
            }
            updateThemeIcon();
        });
    }

    function updateThemeIcon() {
        if (document.documentElement.classList.contains('dark-theme')) {
            themeIcon.className = 'fa-solid fa-sun';
        } else {
            themeIcon.className = 'fa-solid fa-moon';
        }
    }
});
