// Auto-fill login form when a demo account card is clicked.
// Plain JS: the login page is server-rendered before OWL initialises.

(function () {
    function fillForm(login, password) {
        var loginField = document.querySelector('input[name="login"]');
        var passwordField = document.querySelector('input[name="password"]');
        if (loginField) {
            loginField.value = login;
            loginField.dispatchEvent(new Event('input', { bubbles: true }));
            loginField.dispatchEvent(new Event('change', { bubbles: true }));
        }
        if (passwordField) {
            passwordField.value = password;
            passwordField.dispatchEvent(new Event('input', { bubbles: true }));
            passwordField.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    function highlightCard(card) {
        card.style.background = 'rgba(255,255,255,0.22)';
        card.style.borderColor = 'rgba(255,255,255,0.5)';
        setTimeout(function () {
            card.style.background = '';
            card.style.borderColor = '';
        }, 400);
    }

    document.addEventListener('click', function (e) {
        var card = e.target.closest('[data-login]');
        if (!card) return;
        var login = card.getAttribute('data-login');
        var password = card.getAttribute('data-password') || 'Demo2026!';
        if (!login) return;
        fillForm(login, password);
        highlightCard(card);
    });
})();
