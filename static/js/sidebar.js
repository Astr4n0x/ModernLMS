/**
 * sidebar.js - Django LMS version
 * Handles collapse/mobile UI only. Navigation uses real Django URLs (no preventDefault).
 */
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    // Set initial icon state based on sidebar collapsed class
    const mainIcon = document.getElementById('toggle-icon');
    if (mainIcon && sidebar.classList.contains('collapsed')) {
        mainIcon.className = 'fas fa-chevron-right';
    }

    // 1. Desktop: Collapse / Expand sidebar
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            
            // Save state to localStorage
            if (sidebar.classList.contains('collapsed')) {
                localStorage.setItem('sidebarState', 'collapsed');
            } else {
                localStorage.setItem('sidebarState', 'expanded');
            }

            const icon = document.getElementById('toggle-icon');
            if (icon) {
                icon.className = sidebar.classList.contains('collapsed')
                    ? 'fas fa-chevron-right'
                    : 'fas fa-chevron-left';
            }
        });
    }

    // 2. Mobile: Open sidebar
    if (mobileMenuBtn && sidebarOverlay) {
        mobileMenuBtn.addEventListener('click', () => {
            sidebar.classList.add('open');
            sidebarOverlay.classList.add('show');
        });

        // Close sidebar when clicking overlay
        sidebarOverlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('show');
        });
    }

    // 3. Mobile: Close sidebar after clicking a nav link (let navigation proceed normally)
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('open');
                sidebarOverlay?.classList.remove('show');
            }
            // No preventDefault - Django URL handles the redirect
        });
    });

    // 4. Auto-close mobile sidebar on resize
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            sidebar.classList.remove('open');
            sidebarOverlay?.classList.remove('show');
        }
    });

    // 5. Theme Toggle
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    if (themeToggleBtn && themeIcon) {
        const currentTheme = localStorage.getItem('theme') || 'light';
        if (currentTheme === 'dark') {
            themeIcon.classList.replace('fa-moon', 'fa-sun');
        }

        themeToggleBtn.addEventListener('click', () => {
            let theme = document.documentElement.getAttribute('data-theme');
            if (theme === 'dark') {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
                themeIcon.classList.replace('fa-sun', 'fa-moon');
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                themeIcon.classList.replace('fa-moon', 'fa-sun');
            }
        });
    }
});
