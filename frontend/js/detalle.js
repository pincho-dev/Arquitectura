const API_BASE_URL = 'http://localhost:5000/api';

// Obtener ID de la planta desde el query string: detalle.html?id=1
const params = new URLSearchParams(window.location.search);
const PLANTA_ID = params.get('id') || 1;

// Mock de servicio preparado para Flask
async function obtenerEstadoEHistorialPlanta(id) {
  const token = localStorage.getItem('jwt_token');

  /* CUANDO CONECTES FLASK:
  const response = await fetch(`${API_BASE_URL}/plantas/${id}/estado`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await response.json();
  */

  // Estructura lista para recibir lecturas persistidas desde la ESP32
  return new Promise((resolve) => {
    resolve({
      id: id,
      nombre: "Monstera 1",
      especie: "Monstera deliciosa",
      dispositivo_id: "ESP32-01",
      estado: "En riesgo",
      diagnostico: "Humedad por debajo del rango recomendado para la especie desde hace 40 minutos.",
      lectura_actual: {
        humedad: 34,
        luz: 410,
        temperatura: 23
      },
      historial: [
        { hora: "18:42", humedad: 34, luz: 410, temp: 23, origen: "ESP32-01" },
        { hora: "18:37", humedad: 36, luz: 405, temp: 23, origen: "ESP32-01" },
        { hora: "18:32", humedad: 39, luz: 398, temp: 22, origen: "ESP32-01" },
        { hora: "18:20", humedad: 45, luz: 390, temp: 22, origen: "Formulario" },
        { hora: "18:12", humedad: 48, luz: 380, temp: 22, origen: "ESP32-01" },
        { hora: "18:02", humedad: 52, luz: 375, temp: 21, origen: "ESP32-01" }
      ]
    });
  });
}

function renderizarDetalle(data) {
  document.getElementById('plant-title').textContent = data.nombre;
  document.getElementById('plant-species').textContent = data.especie;
  document.getElementById('status-desc').textContent = data.diagnostico;

  // Actualizar métricas destacadas
  document.getElementById('current-humidity').textContent = `${data.lectura_actual.humedad}%`;
  document.getElementById('current-light').textContent = `${data.lectura_actual.luz} lux`;
  document.getElementById('current-temp').textContent = `${data.lectura_actual.temperatura}°C`;

  // Actualizar tabla
  const tbody = document.getElementById('readings-table-body');
  tbody.innerHTML = '';
  data.historial.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.hora}</td>
      <td>${r.humedad}%</td>
      <td>${r.luz} lux</td>
      <td>${r.temp}°C</td>
      <td>${r.origen}</td>
    `;
    tbody.appendChild(tr);
  });
}

// Carga inicial
obtenerEstadoEHistorialPlanta(PLANTA_ID).then(renderizarDetalle);

// Polling periódico (cada 5 segundos) según requerimiento R6 (sin WebSockets)
const POLLING_INTERVAL_MS = 5000;
setInterval(async () => {
  try {
    const dataActualizada = await obtenerEstadoEHistorialPlanta(PLANTA_ID);
    renderizarDetalle(dataActualizada);
  } catch (error) {
    console.warn("Fallo de sondeo periódico:", error);
  }
}, POLLING_INTERVAL_MS);