// Cliente de la API compartido por todas las pantallas.
// El host se toma de la página: así funciona igual en el PC (localhost) que
// desde el teléfono en la red local (ej. 192.168.1.12), que es como se abre
// la URL del sticker NFC.
const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:5000/api`;

const Sesion = {
  token: () => localStorage.getItem('jwt_token'),
  nombre: () => localStorage.getItem('usuario_nombre') || '',
  guardar(data) {
    localStorage.setItem('jwt_token', data.token);
    localStorage.setItem('usuario_nombre', data.usuario.nombre);
  },
  cerrar() {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('usuario_nombre');
  },
  // Manda al login y recuerda a dónde volver (ej. la URL del sticker NFC).
  exigir() {
    if (!Sesion.token()) {
      sessionStorage.setItem('volver_a', window.location.href);
      window.location.href = 'auth.html';
      return false;
    }
    return true;
  },
};

class ErrorApi extends Error {
  constructor(status, cuerpo) {
    super(cuerpo.mensaje || `Error ${status}`);
    this.status = status;
    this.codigo = cuerpo.error;
  }
}

async function api(ruta, { metodo = 'GET', cuerpo } = {}) {
  const headers = {};
  if (cuerpo !== undefined) headers['Content-Type'] = 'application/json';
  if (Sesion.token()) headers['Authorization'] = `Bearer ${Sesion.token()}`;

  const respuesta = await fetch(`${API_BASE_URL}${ruta}`, {
    method: metodo,
    headers,
    body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
  });
  const datos = await respuesta.json().catch(() => ({}));

  if (respuesta.status === 401 && Sesion.token()) {
    // Token vencido o inválido: volver a iniciar sesión.
    Sesion.cerrar();
    Sesion.exigir();
  }
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, datos);
  return datos;
}

const ESTADO_CLASE = { SALUDABLE: 'saludable', EN_RIESGO: 'en-riesgo', CRITICO: 'critico', SIN_DATOS: 'sin-datos' };
const ICONO_ESPECIE = { potos: '🌿', sansevieria: '🪴', suculenta: '🌵', helecho: '🌱', lavanda: '🪻' };

function formatoValor(valor, unidad) {
  return valor === null || valor === undefined ? `—${unidad}` : `${Math.round(valor * 10) / 10}${unidad}`;
}

function escaparHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto ?? '';
  return div.innerHTML;
}
