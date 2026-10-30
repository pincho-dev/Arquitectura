const POLLING_DASHBOARD_MS = 5000;

function tarjetaPlanta(p) {
  const lectura = p.lectura_actual || {};
  const dispositivo = p.dispositivos[0];

  const espHtml = dispositivo
    ? `<span>📶 ${escaparHtml(dispositivo.codigo)} · ${dispositivo.conectado ? 'conectado' : 'desconectado'}</span>`
    : `<a href="reclamar.html" class="esp-status link-action">+ Vincular matera</a>`;

  const card = document.createElement('article');
  card.className = 'plant-card';
  card.innerHTML = `
    <div>
      <div class="card-header">
        <div class="plant-info">
          <span class="plant-icon">${ICONO_ESPECIE[p.especie] || '🌿'}</span>
          <div>
            <h3 class="plant-name">${escaparHtml(p.nombre)}</h3>
            <p class="plant-species">${escaparHtml(p.especie)}</p>
          </div>
        </div>
        <span class="badge ${ESTADO_CLASE[p.estado]}">${escaparHtml(p.estado_texto)}</span>
      </div>

      <div class="metrics-box">
        <div class="metric-item">
          <span class="metric-label">💧 HUMEDAD</span>
          <span class="metric-val">${formatoValor(lectura.humedad, '%')}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">☀️ LUZ</span>
          <span class="metric-val">${formatoValor(lectura.luz, ' lux')}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">🌡️ TEMP</span>
          <span class="metric-val">${formatoValor(lectura.temperatura, '°C')}</span>
        </div>
      </div>
    </div>

    <div class="card-footer">
      <div class="esp-status">${espHtml}</div>
      <a href="detalle.html?id=${p.id}" class="history-link">Ver historial →</a>
    </div>
  `;
  return card;
}

async function cargarDashboard() {
  const grid = document.getElementById('plants-grid');
  let plantas;
  try {
    plantas = await api('/plantas');
  } catch (err) {
    grid.innerHTML = `<p class="empty-note">No fue posible cargar tus plantas: ${escaparHtml(err.message)}</p>`;
    return;
  }

  const conectados = plantas.flatMap(p => p.dispositivos).filter(d => d.conectado).length;
  document.getElementById('plantas-counter').textContent =
    `${plantas.length} ${plantas.length === 1 ? 'planta registrada' : 'plantas registradas'}`;
  document.getElementById('status-summary').textContent =
    `📡 ${conectados} ${conectados === 1 ? 'dispositivo conectado' : 'dispositivos conectados'}`;

  grid.innerHTML = '';
  if (plantas.length === 0) {
    grid.innerHTML = `<p class="empty-note">Aún no tienes plantas. Acerca tu teléfono al sticker NFC de tu matera
      o usa <a href="reclamar.html">+ Nueva planta</a>.</p>`;
  }
  plantas.forEach(p => grid.appendChild(tarjetaPlanta(p)));
}

if (Sesion.exigir()) {
  document.getElementById('welcome-text').textContent = `Hola, ${Sesion.nombre()}`;
  document.getElementById('logout-btn').addEventListener('click', () => {
    Sesion.cerrar();
    window.location.href = 'auth.html';
  });
  cargarDashboard();
  // R6: el dashboard también se actualiza solo (consulta periódica, sin WebSockets).
  setInterval(cargarDashboard, POLLING_DASHBOARD_MS);
}
