const API_BASE_URL = 'http://localhost:5000/api';

// Capa de servicio simulada para Flask
async function obtenerMisPlantas() {
  const token = localStorage.getItem('jwt_token');

  /* CUANDO CONECTES FLASK:
  const response = await fetch(`${API_BASE_URL}/plantas`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await response.json();
  */

  // Datos simulados estructurados según el esquema de la base de datos / ESP32
  return new Promise((resolve) => {
    resolve([
      {
        id: 1,
        nombre: "Monstera 1",
        especie: "Monstera deliciosa",
        icono: "🌿",
        estado: "Saludable",
        humedad: 62,
        luz: 410,
        temperatura: 23,
        dispositivo_id: "ESP32-01",
        conectado: true
      },
      {
        id: 2,
        nombre: "Suculenta ventana",
        especie: "Echeveria elegans",
        icono: "🌵",
        estado: "En riesgo",
        humedad: 18,
        luz: 780,
        temperatura: 27,
        dispositivo_id: "ESP32-02",
        conectado: true
      },
      {
        id: 3,
        nombre: "Helecho cocina",
        especie: "Nephrolepis exaltata",
        icono: "🌱",
        estado: "Crítico",
        humedad: 9,
        luz: 120,
        temperatura: 29,
        dispositivo_id: "ESP32-03",
        conectado: true
      },
      {
        id: 4,
        nombre: "Albahaca balcón",
        especie: "Ocimum basilicum",
        icono: "🌿",
        estado: "Sin datos",
        humedad: null,
        luz: null,
        temperatura: null,
        dispositivo_id: null,
        conectado: false
      }
    ]);
  });
}

function getBadgeClass(estado) {
  switch (estado.toLowerCase()) {
    case 'saludable': return 'saludable';
    case 'en riesgo': return 'en-riesgo';
    case 'crítico': return 'critico';
    default: return 'sin-datos';
  }
}

async function cargarDashboard() {
  const grid = document.getElementById('plants-grid');
  const plantas = await obtenerMisPlantas();

  grid.innerHTML = '';
  plantas.forEach(p => {
    const card = document.createElement('article');
    card.className = 'plant-card';

    const humStr = p.humedad !== null ? `${p.humedad}%` : '-%';
    const luxStr = p.luz !== null ? `${p.luz} lux` : '- lux';
    const tempStr = p.temperatura !== null ? `${p.temperatura}°C` : '-°C';

    const espHtml = p.conectado
      ? `<span>📶 ${p.dispositivo_id} conectado</span>`
      : `<a href="vincular.html?planta_id=${p.id}" class="esp-status link-action">+ Vincular dispositivo</a>`;

    card.innerHTML = `
      <div>
        <div class="card-header">
          <div class="plant-info">
            <span class="plant-icon">${p.icono}</span>
            <div>
              <h3 class="plant-name">${p.nombre}</h3>
              <p class="plant-species">${p.especie}</p>
            </div>
          </div>
          <span class="badge ${getBadgeClass(p.estado)}">${p.estado}</span>
        </div>

        <div class="metrics-box">
          <div class="metric-item">
            <span class="metric-label">💧 HUMEDAD</span>
            <span class="metric-val">${humStr}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">☀️ LUZ</span>
            <span class="metric-val">${luxStr}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">🌡️ TEMP</span>
            <span class="metric-val">${tempStr}</span>
          </div>
        </div>
      </div>

      <div class="card-footer">
        <div class="esp-status">${espHtml}</div>
        <a href="detalle.html?id=${p.id}" class="history-link">Ver historial →</a>
      </div>
    `;
    grid.appendChild(card);
  });
}

document.getElementById('logout-btn')?.addEventListener('click', () => {
  localStorage.removeItem('jwt_token');
  window.location.href = 'auth.html';
});

cargarDashboard();