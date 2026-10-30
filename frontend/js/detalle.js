// Obtener ID de la planta desde el query string: detalle.html?id=1
const params = new URLSearchParams(window.location.search);
const PLANTA_ID = params.get('id');

// Polling periódico (cada 5 segundos) según requerimiento R6 (sin WebSockets)
const POLLING_INTERVAL_MS = 5000;

function hora(fechaIso) {
  return new Date(fechaIso).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function renderizarDetalle(data) {
  document.title = `Matera Inteligente - ${data.nombre}`;
  document.getElementById('plant-title').textContent = data.nombre;
  document.getElementById('plant-species').textContent = data.especie;

  const badge = document.getElementById('status-badge');
  badge.className = `badge ${ESTADO_CLASE[data.estado]}`;
  badge.textContent = data.estado_texto;

  const fueraDeRango = data.parametros.filter(p => p.estado !== 'OPTIMO')
    .map(p => `${p.nombre} ${p.estado === 'BAJO' ? 'por debajo' : 'por encima'} del rango (${p.rango_optimo[0]}–${p.rango_optimo[1]})`);
  document.getElementById('status-desc').textContent = data.lectura_actual
    ? [fueraDeRango.join(' · '), data.recomendaciones].filter(Boolean).join('. ')
    : 'Todavía no hay lecturas de esta planta.';

  const lectura = data.lectura_actual || {};
  document.getElementById('current-humidity').textContent = formatoValor(lectura.humedad, '%');
  document.getElementById('current-light').textContent = formatoValor(lectura.luz, ' lux');
  document.getElementById('current-temp').textContent = formatoValor(lectura.temperatura, '°C');

  const pill = document.getElementById('live-pill');
  const dispositivo = data.dispositivos[0];
  pill.hidden = !dispositivo;
  if (dispositivo) {
    pill.textContent = `📡 ${dispositivo.codigo} · ${dispositivo.conectado ? 'en vivo' : 'desconectado'}`;
  }

  const otros = data.cantidad_duenos - 1;
  document.getElementById('share-owners').textContent = otros === 0
    ? 'Solo tú puedes ver esta planta.'
    : `Compartida con ${otros} ${otros === 1 ? 'persona más' : 'personas más'}.`;

  const tbody = document.getElementById('readings-table-body');
  tbody.innerHTML = '';
  data.historial.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${hora(r.medida_en)}</td>
      <td>${formatoValor(r.humedad, '%')}</td>
      <td>${formatoValor(r.luz, ' lux')}</td>
      <td>${formatoValor(r.temperatura, '°C')}</td>
      <td>${r.origen === 'dispositivo' ? escaparHtml(r.dispositivo) : 'Formulario'}</td>
    `;
    tbody.appendChild(tr);
  });
}

function mostrarError(mensaje) {
  document.querySelector('.share-section').hidden = true;
  document.getElementById('plant-title').textContent = 'No disponible';
  document.getElementById('status-desc').textContent = mensaje;
}

async function actualizar() {
  try {
    renderizarDetalle(await api(`/plantas/${PLANTA_ID}/estado`));
    return true;
  } catch (err) {
    // 403: la planta es de otro usuario (regla de propiedad del dominio).
    mostrarError(err.status === 403 ? '🔒 Esta planta pertenece a otro usuario.' : err.message);
    return err.status !== 403 && err.status !== 404;
  }
}

async function compartir(e) {
  e.preventDefault();
  const input = document.getElementById('share-email');
  const msg = document.getElementById('share-msg');
  try {
    await api(`/plantas/${PLANTA_ID}/duenos`, { metodo: 'POST', cuerpo: { correo: input.value.trim() } });
    msg.className = 'share-msg ok';
    msg.textContent = `Listo: ${input.value.trim()} ya puede ver esta planta y sus lecturas.`;
    input.value = '';
    actualizar();
  } catch (err) {
    msg.className = 'share-msg error';
    msg.textContent = err.message;
  }
  msg.hidden = false;
}

if (Sesion.exigir()) {
  document.getElementById('share-form').addEventListener('submit', compartir);
  document.getElementById('vincular-link').href = `vincular.html?planta_id=${PLANTA_ID}`;
  actualizar().then(seguir => {
    if (!seguir) return;
    const intervalo = setInterval(async () => {
      if (!(await actualizar())) clearInterval(intervalo);
    }, POLLING_INTERVAL_MS);
  });
}
