/*
 * Reclamo de una matera con el QR de su etiqueta.
 *
 * El QR guarda una URL: reclamar.html?codigo=MAT-1A2B&clave=xxxx
 * Al escanearlo con la cámara, el teléfono abre esa URL en el navegador
 * (no hace falta app). Esta página toma código y clave, y si hay sesión
 * reclama la matera de inmediato; si no, pasa por el login y vuelve aquí.
 */
const vistaReclamo = document.getElementById('vista-reclamo');
const vistaInstrucciones = document.getElementById('vista-instrucciones');
const mensaje = document.getElementById('reclamo-mensaje');
const errorBox = document.getElementById('reclamo-error');

function mostrarError(texto) {
  errorBox.textContent = texto;
  errorBox.hidden = false;
}

async function reclamar(codigo, clave) {
  vistaInstrucciones.hidden = true;
  vistaReclamo.hidden = false;
  errorBox.hidden = true;
  document.getElementById('titulo').textContent = `Matera ${codigo.toUpperCase()}`;
  mensaje.textContent = 'Agregando la matera a tu cuenta…';

  try {
    const planta = await api('/plantas/reclamar', { metodo: 'POST', cuerpo: { codigo, clave } });
    document.getElementById('spinner').hidden = true;
    document.getElementById('icono').textContent = ICONO_ESPECIE[planta.especie] || '🌿';
    mensaje.innerHTML = `¡Listo! <strong>${escaparHtml(planta.nombre)}</strong> (${escaparHtml(planta.especie)}) ya es tuya.`;
    setTimeout(() => { window.location.href = `detalle.html?id=${planta.id}`; }, 1500);
  } catch (err) {
    vistaReclamo.hidden = true;
    if (err.codigo === 'MATERA_YA_RECLAMADA') {
      mostrarError('Esta matera ya pertenece a una cuenta. Si es tuya, la encuentras en "Mis plantas".');
    } else if (err.codigo === 'CLAVE_RECLAMO_INVALIDA') {
      mostrarError('El código y la clave no corresponden a ninguna matera. Revísalos en la etiqueta.');
    } else {
      mostrarError(err.message || 'No fue posible agregar la matera.');
    }
    vistaInstrucciones.hidden = false;
  }
}

const params = new URLSearchParams(window.location.search);
const codigo = params.get('codigo');
const clave = params.get('clave');

// Sin sesión, Sesion.exigir() guarda esta URL (con código y clave) y manda al
// login; después del login se vuelve aquí y el reclamo sigue solo.
if (Sesion.exigir()) {
  if (codigo && clave) {
    reclamar(codigo, clave);
  } else {
    vistaInstrucciones.hidden = false;
  }

  document.getElementById('manual-form').addEventListener('submit', (e) => {
    e.preventDefault();
    reclamar(document.getElementById('codigo').value.trim(), document.getElementById('clave').value.trim());
  });
}
