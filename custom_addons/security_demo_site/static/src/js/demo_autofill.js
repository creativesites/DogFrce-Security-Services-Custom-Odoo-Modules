// Auto-fill login form when a demo account row is clicked.
// Plain JS — runs before OWL initialises (login page is server-rendered).

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
        var row = e.target.closest('.dg_demo_account[data-login]');
        if (!row) return;
        fillForm(row.dataset.login, row.dataset.password || 'Demo2026!');
    });
})();
