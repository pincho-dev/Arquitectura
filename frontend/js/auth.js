// Configuración base de la API Flask
const API_BASE_URL = 'http://localhost:5000/api';

let currentMode = 'login'; // 'login' | 'register'

const tabLogin = document.getElementById('tab-login');
const tabRegister = document.getElementById('tab-register');
const formTitle = document.getElementById('form-title');
const submitBtn = document.getElementById('submit-btn');
const authForm = document.getElementById('auth-form');

// Manejo de pestañas
tabLogin.addEventListener('click', () => {
  currentMode = 'login';
  tabLogin.classList.add('active');
  tabRegister.classList.remove('active');
  formTitle.textContent = 'Iniciar sesión';
  submitBtn.querySelector('span').textContent = 'Entrar';
});

tabRegister.addEventListener('click', () => {
  currentMode = 'register';
  tabRegister.classList.add('active');
  tabLogin.classList.remove('active');
  formTitle.textContent = 'Crear cuenta';
  submitBtn.querySelector('span').textContent = 'Registrarse';
});

// Capa de servicio preparada para Flask
async function autenticarUsuario(credenciales, modo) {
  const endpoint = modo === 'login' ? `${API_BASE_URL}/auth/login` : `${API_BASE_URL}/auth/registro`;

  /* CUANDO CONECTES FLASK:
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credenciales)
  });
  if (!response.ok) throw new Error('Credenciales incorrectas');
  return await response.json();
  */

  // Simulación temporal de respuesta Flask con JWT:
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        token: "jwt_mock_token_flask_session_12345",
        usuario: { id: 1, nombre: "Julián", correo: credenciales.correo }
      });
    }, 400);
  });
}

authForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const correo = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;

  try {
    const data = await autenticarUsuario({ correo, password }, currentMode);
    
    // Almacenamos el JWT para las peticiones subsecuentes
    localStorage.setItem('jwt_token', data.token);
    localStorage.setItem('usuario_nombre', data.usuario.nombre);

    window.location.href = 'dashboard.html';
  } catch (err) {
    alert('Error de autenticación: ' + err.message);
  }
});