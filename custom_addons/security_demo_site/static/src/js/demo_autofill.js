// Auto-fill login form when a demo account card is clicked.
// Plain JS: the login page is server-rendered before OWL initializes.

(function () {
    function fillForm(login, password) {
        var loginField = document.querySelector('input[name="login"]');
        var passwordField = document.querySelector('input[name="password"]');
        if (loginField) loginField.value = login;
        if (passwordField) passwordField.value = password;
        // Give visual feedback
        if (loginField) loginField.dispatchEvent(new Event('input'));
    }

    document.addEventListener('click', function (e) {
        var card = e.target.closest('.dg_demo_card[data-login]');
        if (!card) return;
        fillForm(card.dataset.login, card.dataset.password || 'Demo2026!');
    });
})();
