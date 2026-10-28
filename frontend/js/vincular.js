const API_BASE_URL = 'http://localhost:5000/api';

const copyBtn = document.getElementById('copy-btn');
const tokenInput = document.getElementById('device-token');

// 1. Lógica de copiado al portapapeles
copyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(tokenInput.value);
    const originalText = copyBtn.textContent;
    copyBtn.textContent = '¡Copiado!';
    copyBtn.style.backgroundColor = '#2c4935';
    copyBtn.style.color = '#ffffff';

    setTimeout(() => {
      copyBtn.textContent = originalText;
      copyBtn.style.backgroundColor = '#edf2eb';
      copyBtn.style.color = '#2c4935';
    }, 2000);
  } catch {
    tokenInput.select();
    document.execCommand('copy');
  }
});

// 2. Consulta periódica para detectar si la ESP32 ya transmitió datos
async function verificarEstadoHandshake(tokenDispositivo) {
  /* CUANDO CONECTES FLASK:
  const res = await fetch(`${API_BASE_URL}/dispositivos/verificar-conexion?device_token=${tokenDispositivo}`);
  const data = await res.json();
  return data.reportando; // booleano
  */

  // Simulación: siempre false hasta que la ESP32 física envíe su primer POST
  return false;
}

const checkInterval = setInterval(async () => {
  try {
    const conectado = await verificarEstadoHandshake(tokenInput.value);
    if (conectado) {
      clearInterval(checkInterval);
      alert('¡Dispositivo ESP32 vinculado y transmitiendo con éxito!');
      window.location.href = 'detalle.html';
    }
  } catch (err) {
    console.log("Esperando paquete HTTP POST de la ESP32...", err);
  }
}, 4000);