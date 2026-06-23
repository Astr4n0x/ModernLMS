/**
 * login.js - Django LMS version
 * Handles UI toggles and animations. Form POSTS naturally to Django.
 */
document.addEventListener('DOMContentLoaded', () => {



    // --- Password visibility toggles ---
    const passwordToggles = document.querySelectorAll('.password-toggle');
    
    passwordToggles.forEach(toggleBtn => {
        toggleBtn.addEventListener('click', () => {
            const targetId = toggleBtn.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);
            const toggleIcon = toggleBtn.querySelector('.toggle-icon');
            
            if (passwordInput && toggleIcon) {
                const isPassword = passwordInput.getAttribute('type') === 'password';
                passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
                toggleIcon.className = isPassword ? 'fas fa-eye-slash toggle-icon' : 'fas fa-eye toggle-icon';
            }
        });
    });

    // --- Loading state on submit ---
    const forms = document.querySelectorAll('.auth-section');
    
    forms.forEach(form => {
        form.addEventListener('submit', () => {
            const submitBtn = form.querySelector('.action-btn');
            if (submitBtn) {
                submitBtn.classList.add('loading');
            }
        });
    });

    // --- Shake animation if error banner is shown (from Django messages) ---
    const errorBanner = document.getElementById('error-banner');
    const loginContainer = document.getElementById('login-container');

    if (errorBanner && errorBanner.classList.contains('show') && loginContainer) {
        loginContainer.classList.add('shake');
        setTimeout(() => loginContainer.classList.remove('shake'), 600);
    }
});
