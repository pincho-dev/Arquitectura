// Flujo manual (sin sticker NFC): se genera el token y se pega en el firmware.
const PLANTA_ID = new URLSearchParams(window.location.search).get('planta_id');
const copyBtn = document.getElementById('copy-btn');
const tokenInput = document.getElementById('device-token');

copyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(tokenInput.value);
  } catch {
    tokenInput.select();
    document.execCommand('copy');
  }
  copyBtn.textContent = '¡Copiado!';
  setTimeout(() => { copyBtn.textContent = 'Copiar'; }, 2000);
});

async function vincular() {
  const planta = await api(`/plantas/${PLANTA_ID}/estado`);
  document.getElementById('planta-nombre').textContent = planta.nombre.toUpperCase();
  document.getElementById('volver-link').href = `detalle.html?id=${PLANTA_ID}`;

  const codigo = `ESP32-${Math.random().toString(16).slice(2, 6).toUpperCase()}`;
  const dispositivo = await api(`/plantas/${PLANTA_ID}/dispositivos`, { metodo: 'POST', cuerpo: { codigo } });
  tokenInput.value = dispositivo.token;
  document.getElementById('firmware-preview').textContent =
    `#define DEVICE_CODIGO "${dispositivo.codigo}"\n#define DEVICE_TOKEN  "${dispositivo.token}"`;
  document.getElementById('waiting-subtitle').textContent =
    `POST /api/dispositivos/${dispositivo.codigo}/lecturas aún no reporta`;

  // Consulta periódica hasta que el dispositivo reporte su primera lectura.
  const intervalo = setInterval(async () => {
    const estado = await api(`/plantas/${PLANTA_ID}/estado`).catch(() => null);
    const nuevo = estado && estado.dispositivos.find(d => d.codigo === dispositivo.codigo);
    if (nuevo && nuevo.conectado) {
      clearInterval(intervalo);
      document.getElementById('waiting-title').textContent = `¡${dispositivo.codigo} conectado!`;
      setTimeout(() => { window.location.href = `detalle.html?id=${PLANTA_ID}`; }, 1200);
    }
  }, 4000);
}

if (Sesion.exigir()) {
  if (!PLANTA_ID) {
    window.location.href = 'reclamar.html';
  } else {
    vincular().catch(err => {
      document.getElementById('waiting-title').textContent = `No fue posible vincular: ${err.message}`;
    });
  }
}
