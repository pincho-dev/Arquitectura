// Lista de las ESP del usuario (GET /api/dispositivos). Polling según R6.
const POLLING_DISPOSITIVOS_MS = 5000;

function haceCuanto(fechaIso) {
  if (!fechaIso) return 'Nunca se ha conectado';
  const segundos = Math.max(0, Math.round((Date.now() - new Date(fechaIso)) / 1000));
  if (segundos < 60) return `Hace ${segundos} s`;
  const minutos = Math.round(segundos / 60);
  if (minutos < 60) return `Hace ${minutos} min`;
  const horas = Math.round(minutos / 60);
  if (horas < 24) return `Hace ${horas} h`;
  return new Date(fechaIso).toLocaleString('es-CO');
}

async function cargarDispositivos() {
  const tbody = document.getElementById('dispositivos-body');
  let dispositivos;
  try {
    dispositivos = await api('/dispositivos');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">No fue posible cargar los dispositivos: ${escaparHtml(err.message)}</td></tr>`;
    return;
  }

  const conectados = dispositivos.filter(d => d.conectado).length;
  document.getElementById('dispositivos-counter').textContent =
    `${dispositivos.length} ${dispositivos.length === 1 ? 'dispositivo' : 'dispositivos'}`;
  document.getElementById('status-summary').textContent =
    `📡 ${conectados} ${conectados === 1 ? 'conectado' : 'conectados'}`;

  if (dispositivos.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5">Aún no tienes dispositivos. Acerca tu teléfono al sticker NFC de una matera
      o usa <a href="reclamar.html">+ Agregar matera</a>.</td></tr>`;
    return;
  }

  tbody.innerHTML = dispositivos.map(d => `
    <tr>
      <td><span class="conexion ${d.conectado ? 'en-linea' : 'fuera'}">${d.conectado ? 'En vivo' : 'Desconectado'}</span></td>
      <td class="codigo">${escaparHtml(d.codigo)}</td>
      <td><a href="detalle.html?id=${d.planta.id}">${escaparHtml(d.planta.nombre)}</a></td>
      <td>${ICONO_ESPECIE[d.planta.especie] || '🌿'} ${escaparHtml(d.planta.especie)}</td>
      <td>${haceCuanto(d.ultima_conexion)}</td>
    </tr>
  `).join('');
}

if (Sesion.exigir()) {
  cargarDispositivos();
  setInterval(cargarDispositivos, POLLING_DISPOSITIVOS_MS);
}
