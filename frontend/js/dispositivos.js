// Lista de las ESP del usuario (GET /api/dispositivos), en vivo por WebSocket.

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
    tbody.innerHTML = `<tr><td colspan="6">No fue posible cargar los dispositivos: ${escaparHtml(err.message)}</td></tr>`;
    return;
  }

  const conectados = dispositivos.filter(d => d.conectado).length;
  document.getElementById('dispositivos-counter').textContent =
    `${dispositivos.length} ${dispositivos.length === 1 ? 'dispositivo' : 'dispositivos'}`;
  document.getElementById('status-summary').textContent =
    `📡 ${conectados} ${conectados === 1 ? 'conectado' : 'conectados'}`;

  if (dispositivos.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6">Aún no tienes dispositivos. Escanea el QR de la etiqueta de una matera
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
      <td class="acciones">
        <button type="button" data-orden="parpadear" data-codigo="${escaparHtml(d.codigo)}" ${d.conectado ? '' : 'disabled'}
          title="El LED de la matera parpadea para encontrarla">💡 Parpadear</button>
        <button type="button" data-orden="reportar" data-codigo="${escaparHtml(d.codigo)}" ${d.conectado ? '' : 'disabled'}
          title="La matera manda una lectura ya mismo">📤 Leer ahora</button>
      </td>
    </tr>
  `).join('');
}

// Órdenes en vivo: viajan al ESP32 por su WebSocket (POST /api/dispositivos/<codigo>/ordenes).
document.getElementById('dispositivos-body').addEventListener('click', async (e) => {
  const boton = e.target.closest('button[data-orden]');
  if (!boton) return;
  const texto = boton.textContent;
  boton.disabled = true;
  try {
    await api(`/dispositivos/${encodeURIComponent(boton.dataset.codigo)}/ordenes`,
      { metodo: 'POST', cuerpo: { orden: boton.dataset.orden } });
    boton.textContent = 'Enviada…';
  } catch (err) {
    boton.textContent = err.codigo === 'DISPOSITIVO_DESCONECTADO' ? 'Desconectada' : 'Error';
    boton.title = err.message;
  }
  setTimeout(() => { boton.textContent = texto; boton.disabled = false; }, 2500);
});

if (Sesion.exigir()) {
  cargarDispositivos();
  const recargar = TiempoReal.agrupar(cargarDispositivos);
  TiempoReal.escuchar({
    alAviso: (e) => {
      if (e.tipo === 'orden_ok') {
        const boton = document.querySelector(`button[data-codigo="${CSS.escape(e.codigo)}"]:disabled`);
        if (boton) boton.textContent = '✓ Cumplida';
        return;
      }
      if (e.tipo === 'conexion' || e.tipo === 'lectura') recargar();
    },
    respaldo: cargarDispositivos,
  });
}
