/*
 * Avisos en vivo del backend por WebSocket (/ws/app).
 *
 *   TiempoReal.escuchar({
 *     alAviso: (evento) => { ... },   // {tipo: 'estado'|'conexion'|'lectura'|'orden_ok', planta_id, codigo, ...}
 *     respaldo: () => { ... },        // recarga por HTTP; se llama mientras no haya WebSocket
 *   });
 *
 * Al abrir, el JWT va en el primer mensaje: el navegador no deja poner la
 * cabecera Authorization en un WebSocket, y en la URL quedaría en los logs.
 *
 * Si el WebSocket se cae, reintenta solo (1 s, 2 s, 4 s… hasta 30 s) y
 * mientras tanto vuelve a la consulta periódica de R6 cada 5 s: la página
 * nunca se queda congelada.
 */
const TiempoReal = (() => {
  const URL_WS = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:5000/ws/app`;
  const INTERVALO_RESPALDO_MS = 5000;
  const ESPERA_MAXIMA_MS = 30000;
  const CIERRE_NO_AUTENTICADO = 4401;

  function indicador() {
    let pill = document.getElementById('modo-tiempo-real');
    if (!pill) {
      pill = document.createElement('div');
      pill.id = 'modo-tiempo-real';
      pill.setAttribute('role', 'status');
      pill.style.cssText = 'position:fixed;bottom:1rem;right:1rem;padding:.35rem .8rem;border-radius:999px;'
        + 'font-size:.78rem;font-weight:600;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.15);z-index:50;';
      document.body.appendChild(pill);
    }
    return pill;
  }

  function mostrarModo(modo) {
    const pill = indicador();
    const modos = {
      'en-vivo': ['● En vivo', '#16a34a'],
      respaldo: ['↻ Sin conexión en vivo: actualizando cada 5 s', '#b45309'],
      conectando: ['… Conectando', '#64748b'],
    };
    [pill.textContent, pill.style.color] = modos[modo];
  }

  function escuchar({ alAviso = () => {}, respaldo = () => {} } = {}) {
    let espera = 1000;
    let temporizador = null;

    const iniciarRespaldo = () => {
      if (temporizador) return;
      respaldo();
      temporizador = setInterval(respaldo, INTERVALO_RESPALDO_MS);
    };
    const detenerRespaldo = () => {
      clearInterval(temporizador);
      temporizador = null;
    };

    function conectar() {
      mostrarModo(temporizador ? 'respaldo' : 'conectando');
      const ws = new WebSocket(URL_WS);

      ws.addEventListener('open', () => ws.send(JSON.stringify({ tipo: 'auth', token: Sesion.token() })));

      ws.addEventListener('message', (e) => {
        let evento;
        try { evento = JSON.parse(e.data); } catch { return; }
        if (evento.tipo === 'estado') {
          espera = 1000;
          detenerRespaldo();
          mostrarModo('en-vivo');
        }
        if (evento.tipo !== 'error') alAviso(evento);
      });

      ws.addEventListener('close', (e) => {
        if (e.code === CIERRE_NO_AUTENTICADO) {   // JWT vencido: volver a iniciar sesión
          Sesion.cerrar();
          Sesion.exigir();
          return;
        }
        iniciarRespaldo();
        mostrarModo('respaldo');
        setTimeout(conectar, espera);
        espera = Math.min(espera * 2, ESPERA_MAXIMA_MS);
      });
    }

    conectar();
  }

  // Varios avisos seguidos (ej. lectura + conexión) producen una sola recarga.
  function agrupar(fn, ms = 250) {
    let pendiente = null;
    return () => {
      clearTimeout(pendiente);
      pendiente = setTimeout(fn, ms);
    };
  }

  return { escuchar, agrupar };
})();
