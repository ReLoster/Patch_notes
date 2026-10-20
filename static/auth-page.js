(function () {
  var mode = document.body.dataset.mode;
  var form = document.getElementById('auth-form');
  var errorEl = document.getElementById('auth-error');
  var btn = document.getElementById('auth-btn');
  var btnText = mode === 'login' ? 'Войти' : 'Зарегистрироваться';

  fetch('/api/auth/me', { credentials: 'same-origin' })
    .then(function (r) { if (r.ok) window.location.href = '/'; })
    .catch(function () {});

  function showError(msg) { errorEl.textContent = msg; }
  function setLoading(loading) {
    btn.disabled = loading;
    btn.textContent = loading ? 'Подождите…' : btnText;
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    showError('');
    setLoading(true);

    var login = document.getElementById('auth-login').value.trim();
    var password = document.getElementById('auth-pass').value;
    var confirmInput = document.getElementById('auth-pass-confirm');

    if (mode === 'register' && confirmInput && password !== confirmInput.value) {
      showError('Пароли не совпадают');
      setLoading(false);
      return;
    }

    try {
      var res = await fetch('/api/auth/' + mode, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login: login, password: password })
      });
      var data = await res.json().catch(function () { return {}; });
      if (!res.ok) {
        showError(data.error || 'Ошибка ' + res.status);
        setLoading(false);
        return;
      }
      window.location.href = '/';
    } catch (err) {
      showError('Ошибка сети. Попробуйте ещё раз.');
      setLoading(false);
    }
  });
})();