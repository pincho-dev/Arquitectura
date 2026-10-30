let currentMode = 'login'; // 'login' | 'register'

const tabLogin = document.getElementById('tab-login');
const tabRegister = document.getElementById('tab-register');
const formTitle = document.getElementById('form-title');
const submitBtn = document.getElementById('submit-btn');
const authForm = document.getElementById('auth-form');
const grupoNombre = document.getElementById('grupo-nombre');
const inputNombre = document.getElementById('nombre');
const mensajeError = document.getElementById('auth-error');

function cambiarModo(modo) {
  currentMode = modo;
  const esRegistro = modo === 'register';
  tabLogin.classList.toggle('active', !esRegistro);
  tabRegister.classList.toggle('active', esRegistro);
  formTitle.textContent = esRegistro ? 'Crear cuenta' : 'Iniciar sesión';
  submitBtn.querySelector('span').textContent = esRegistro ? 'Registrarse' : 'Entrar';
  grupoNombre.hidden = !esRegistro;
  inputNombre.required = esRegistro;
  mensajeError.hidden = true;
}

tabLogin.addEventListener('click', () => cambiarModo('login'));
tabRegister.addEventListener('click', () => cambiarModo('register'));

authForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const correo = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const cuerpo = currentMode === 'login'
    ? { correo, password }
    : { nombre: inputNombre.value.trim(), correo, password };

  submitBtn.disabled = true;
  mensajeError.hidden = true;
  try {
    const data = await api(currentMode === 'login' ? '/auth/login' : '/auth/registro', { metodo: 'POST', cuerpo });
    Sesion.guardar(data);
    // Si se llegó aquí desde un sticker NFC, se vuelve a reclamar la matera.
    const volverA = sessionStorage.getItem('volver_a');
    sessionStorage.removeItem('volver_a');
    window.location.href = volverA || 'dashboard.html';
  } catch (err) {
    mensajeError.textContent = err instanceof ErrorApi ? err.message : 'No fue posible comunicarse con el servidor.';
    mensajeError.hidden = false;
  } finally {
    submitBtn.disabled = false;
  }
});

if (sessionStorage.getItem('volver_a')) {
  document.querySelector('.auth-footer-note').textContent =
    'Inicia sesión o crea tu cuenta para agregar la matera que acabas de escanear.';
}
