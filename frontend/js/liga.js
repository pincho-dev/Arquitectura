// Página de la liga: mi división, ranking (global o entre amigos), mis
// plantas en la liga, amigos y la tabla de divisiones.
const ORDEN_DIVISIONES = ['semilla', 'brote', 'hoja', 'flor', 'arbol'];
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
  'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

const estado = { mes: null, mesActual: null, alcance: 'global', yo: null, requisitos: null };

function mesLegible(mes) {
  const [anio, numero] = mes.split('-').map(Number);
  return `${MESES[numero - 1]} ${anio}`;
}

function mesDesplazado(mes, delta) {
  const [anio, numero] = mes.split('-').map(Number);
  const fecha = new Date(anio, numero - 1 + delta, 1);
  return `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, '0')}`;
}

function puntosTexto(puntos) {
  return puntos === null || puntos === undefined ? '—' : `${Math.round(puntos * 10) / 10}`;
}

function consultaMes() {
  return estado.mes ? `mes=${estado.mes}` : '';
}

// ---------------------------------------------------------------- mi división

function renderHero(yo) {
  const hero = document.getElementById('hero');
  const division = yo.division;
  const siguiente = yo.siguiente_division;
  const puntos = yo.clasificado ? yo.puntos : yo.puntos_provisionales;
  const horasMes = yo.requisitos.horas_minimas_mes;

  let progreso = 1;
  if (siguiente && puntos !== null) {
    progreso = Math.min(Math.max((puntos - division.minimo) / (siguiente.minimo - division.minimo), 0), 1);
  } else if (siguiente) {
    progreso = 0;
  }

  let estadoTexto;
  if (yo.plantas.length === 0) {
    estadoTexto = 'Reclama una matera para entrar a la liga.';
  } else if (yo.clasificado) {
    estadoTexto = `<strong>${puntosTexto(puntos)} pts</strong> de promedio en el mes`;
  } else {
    const mejorHoras = Math.max(...yo.plantas.map(p => p.horas_conectada));
    estadoTexto = `Aún no clasificas: tu planta más conectada lleva <strong>${mejorHoras} de ${horasMes} h</strong>`
      + (puntos !== null ? ` · vas con ${puntosTexto(puntos)} pts` : '');
  }

  const faltan = siguiente
    ? (yo.puntos_para_subir !== null
      ? `Te faltan <strong>${puntosTexto(yo.puntos_para_subir)} pts</strong> para ${escaparHtml(siguiente.nombre)}`
      : `Llega a ${siguiente.minimo} pts para subir a ${escaparHtml(siguiente.nombre)}`)
    : 'Estás en la división más alta. ¡Que no se te seque!';

  const anterior = yo.division_mes_anterior
    ? `El mes anterior terminaste en ${escaparHtml(yo.division_mes_anterior.nombre)}.`
    : 'El mes anterior no clasificaste.';
  const arranque = !yo.clasificado && yo.plantas.length > 0
    ? ' Mientras no clasifiques, arrancas una división por debajo.'
    : '';

  hero.dataset.division = division.clave;
  hero.innerHTML = `
    <div class="hero-emblema">${Emblemas.svg(division.clave, 200)}</div>
    <div class="hero-info">
      <div class="hero-mes">
        <button type="button" class="mes-boton" id="mes-anterior" aria-label="Mes anterior">‹</button>
        <span>${escaparHtml(mesLegible(yo.mes))}</span>
        <button type="button" class="mes-boton" id="mes-siguiente" aria-label="Mes siguiente"
          ${yo.mes === estado.mesActual ? 'disabled' : ''}>›</button>
      </div>
      <p class="hero-metal">${escaparHtml(division.metal)}</p>
      <h1 class="hero-division">${escaparHtml(division.nombre)}</h1>
      <p class="hero-puntos">${estadoTexto}</p>
      <div class="barra" role="progressbar" aria-label="Progreso hacia la siguiente división"
        aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(progreso * 100)}">
        <span style="width: ${progreso * 100}%"></span>
      </div>
      <p class="hero-faltan">${faltan}</p>
      <p class="hero-anterior">${anterior}${arranque}</p>
      <button type="button" class="boton-fantasma" id="ver-emblema">Ver mi emblema</button>
    </div>
  `;

  document.getElementById('mes-anterior').addEventListener('click', () => cambiarMes(-1));
  document.getElementById('mes-siguiente').addEventListener('click', () => cambiarMes(1));
  document.getElementById('ver-emblema').addEventListener('click', () => mostrarEmblema(yo, false));
}

function renderMisPlantas(yo) {
  const contenedor = document.getElementById('mis-plantas');
  if (yo.plantas.length === 0) {
    contenedor.innerHTML = `<p class="nota">Aún no tienes plantas. <a href="reclamar.html">Reclama tu matera</a> y empieza a sumar puntos.</p>`;
    return;
  }
  const horasMes = yo.requisitos.horas_minimas_mes;
  contenedor.innerHTML = yo.plantas.map(p => {
    const avance = Math.min(p.horas_conectada / horasMes, 1) * 100;
    const chip = p.clasifica
      ? '<span class="chip chip-ok">Clasifica</span>'
      : `<span class="chip chip-pendiente">Le faltan ${Math.max(Math.ceil(horasMes - p.horas_conectada), 0)} h</span>`;
    return `
      <article class="planta-liga">
        <div class="planta-liga-cabecera">
          <h3>${escaparHtml(p.nombre)}</h3>
          ${chip}
        </div>
        <p class="planta-liga-puntos"><strong>${puntosTexto(p.puntos)}</strong> pts</p>
        <div class="barra barra-clara" role="progressbar" aria-label="Horas conectada este mes"
          aria-valuemin="0" aria-valuemax="${horasMes}" aria-valuenow="${p.horas_conectada}">
          <span style="width: ${avance}%"></span>
        </div>
        <p class="planta-liga-detalle">
          ${p.horas_conectada} h conectada · ${p.dias_validos} ${p.dias_validos === 1 ? 'día' : 'días'} con puntos ·
          ${p.episodios} ${p.episodios === 1 ? 'alerta' : 'alertas'}
        </p>
      </article>`;
  }).join('');
}

// ------------------------------------------------------------------- ranking

async function cargarRanking() {
  const lista = document.getElementById('ranking');
  const nota = document.getElementById('ranking-nota');
  let ranking;
  try {
    ranking = await api(`/liga/ranking?alcance=${estado.alcance}&${consultaMes()}`);
  } catch (err) {
    lista.innerHTML = '';
    nota.textContent = `No fue posible cargar el ranking: ${err.message}`;
    return;
  }

  lista.innerHTML = ranking.filas.map(f => `
    <li class="fila ${f.soy_yo ? 'fila-yo' : ''}">
      <span class="fila-pos">${f.posicion}</span>
      <span class="fila-emblema">${Emblemas.svg(f.division.clave, 44, { decorativo: true })}</span>
      <span class="fila-nombre">
        ${escaparHtml(f.usuario.nombre)}${f.soy_yo ? ' <small>(tú)</small>' : ''}
        <small class="fila-division">${escaparHtml(f.division.nombre)} · ${f.plantas} ${f.plantas === 1 ? 'planta' : 'plantas'}</small>
      </span>
      <span class="fila-puntos">${puntosTexto(f.puntos)}<small> pts</small></span>
    </li>`).join('');

  const horas = estado.requisitos ? estado.requisitos.horas_minimas_mes : 24;
  if (ranking.filas.length === 0) {
    nota.textContent = estado.alcance === 'amigos'
      ? 'Ni tú ni tus amigos clasifican todavía. Agrega amigos más abajo para competir con ellos.'
      : 'Nadie clasifica todavía este mes.';
  } else if (ranking.mi_posicion === null) {
    nota.textContent = `Todavía no apareces: una de tus plantas necesita ${horas} h conectada en el mes.`;
  } else {
    nota.textContent = `Vas de ${ranking.mi_posicion}.º. Solo aparecen quienes clasifican.`;
  }
}

function elegirAlcance(alcance) {
  estado.alcance = alcance;
  document.querySelectorAll('.tab').forEach(tab => {
    const activo = tab.dataset.alcance === alcance;
    tab.classList.toggle('activo', activo);
    tab.setAttribute('aria-pressed', String(activo));
  });
  cargarRanking();
}

// -------------------------------------------------------------------- amigos

async function cargarAmigos() {
  const contenedor = document.getElementById('amigos');
  let amistades;
  try {
    amistades = await api('/amigos');
  } catch (err) {
    contenedor.innerHTML = `<p class="nota">No fue posible cargar tus amigos: ${escaparHtml(err.message)}</p>`;
    return;
  }

  const grupos = [
    ['recibida', 'Solicitudes para ti', a => `
      <button type="button" class="boton-primario boton-chico" data-accion="aceptar" data-id="${a.id}">Aceptar</button>
      <button type="button" class="boton-fantasma boton-chico" data-accion="eliminar" data-id="${a.id}">Rechazar</button>`],
    ['amigos', 'Tus amigos', a => `
      <button type="button" class="boton-fantasma boton-chico" data-accion="eliminar" data-id="${a.id}"
        aria-label="Quitar a ${escaparHtml(a.usuario.nombre)} de tus amigos">Quitar</button>`],
    ['enviada', 'Esperando respuesta', a => `
      <button type="button" class="boton-fantasma boton-chico" data-accion="eliminar" data-id="${a.id}">Cancelar</button>`],
  ];

  const html = grupos.map(([clave, titulo, botones]) => {
    const deEsteGrupo = amistades.filter(a => a.estado === clave);
    if (deEsteGrupo.length === 0) return '';
    return `
      <div class="amigos-grupo">
        <h3>${titulo}</h3>
        <ul>
          ${deEsteGrupo.map(a => `
            <li class="amigo">
              <span class="amigo-avatar" aria-hidden="true">${escaparHtml(a.usuario.nombre.charAt(0).toUpperCase())}</span>
              <span class="amigo-nombre">${escaparHtml(a.usuario.nombre)}</span>
              <span class="amigo-acciones">${botones(a)}</span>
            </li>`).join('')}
        </ul>
      </div>`;
  }).join('');

  contenedor.innerHTML = html || '<p class="nota">Aún no tienes amigos en la liga. Invita a alguien con su correo.</p>';
}

async function accionAmigo(evento) {
  const boton = evento.target.closest('button[data-accion]');
  if (!boton) return;
  boton.disabled = true;
  const mensaje = document.getElementById('amigo-mensaje');
  try {
    if (boton.dataset.accion === 'aceptar') {
      await api(`/amigos/${boton.dataset.id}/aceptar`, { metodo: 'POST' });
      mensaje.textContent = '¡Ahora son amigos!';
    } else {
      await api(`/amigos/${boton.dataset.id}`, { metodo: 'DELETE' });
      mensaje.textContent = '';
    }
  } catch (err) {
    mensaje.textContent = err.message;
  }
  await cargarAmigos();
  if (estado.alcance === 'amigos') cargarRanking();
}

async function enviarSolicitud(evento) {
  evento.preventDefault();
  const entrada = document.getElementById('correo-amigo');
  const mensaje = document.getElementById('amigo-mensaje');
  const boton = evento.target.querySelector('button[type="submit"]');
  boton.disabled = true;
  try {
    const amistad = await api('/amigos', { metodo: 'POST', cuerpo: { correo: entrada.value } });
    mensaje.textContent = amistad.estado === 'amigos'
      ? `${amistad.usuario.nombre} ya te había invitado: ¡ahora son amigos!`
      : `Solicitud enviada a ${amistad.usuario.nombre}.`;
    entrada.value = '';
    await cargarAmigos();
    if (estado.alcance === 'amigos') cargarRanking();
  } catch (err) {
    mensaje.textContent = err.message;
  } finally {
    boton.disabled = false;
  }
}

// ---------------------------------------------------------------- divisiones

async function cargarDivisiones() {
  const datos = await api('/liga/divisiones');
  estado.requisitos = datos.requisitos;
  document.getElementById('divisiones').innerHTML = datos.divisiones.map(d => `
    <div class="division" data-division="${d.clave}">
      ${Emblemas.svg(d.clave, 96)}
      <strong>${escaparHtml(d.nombre)}</strong>
      <span class="division-metal">${escaparHtml(d.metal)}</span>
      <span class="division-rango">${d.minimo}–${d.maximo} pts</span>
    </div>`).join('');
  document.getElementById('reglas').innerHTML = `
    Cada día ganas hasta 100 puntos: 70 por el tiempo que tu planta estuvo saludable (en riesgo vale la mitad)
    y 30 por qué tan rápido la recuperas cuando algo sale mal. Tu puntaje es el promedio de tus plantas.
    Para clasificar, una planta tiene que estar conectada al menos ${datos.requisitos.horas_minimas_mes} h en el mes
    (y un día cuenta si estuvo ${datos.requisitos.horas_minimas_dia} h). Desconectar la matera no suma ni resta.`;
}

// --------------------------------------------------- emblema y "subiste de división"

function mostrarEmblema(yo, esAscenso) {
  const dialogo = document.getElementById('ascenso');
  dialogo.dataset.division = yo.division.clave;
  document.getElementById('ascenso-mes').textContent = esAscenso ? `Cierre de ${mesLegible(yo.mes)}` : mesLegible(yo.mes);
  document.getElementById('ascenso-titulo').textContent = esAscenso ? '¡Subiste de división!' : 'Tu división';
  document.getElementById('ascenso-emblema').innerHTML = Emblemas.svg(yo.division.clave, 220);
  document.getElementById('ascenso-cambio').innerHTML = esAscenso
    ? `${escaparHtml(yo.division_mes_anterior.nombre)} <span aria-hidden="true">→</span><span class="visualmente-oculto">a</span> <strong>${escaparHtml(yo.division.nombre)} · ${escaparHtml(yo.division.metal)}</strong>`
    : `<strong>${escaparHtml(yo.division.nombre)} · ${escaparHtml(yo.division.metal)}</strong>`;
  const puntos = yo.clasificado ? yo.puntos : yo.puntos_provisionales;
  document.getElementById('ascenso-texto').textContent = yo.siguiente_division && yo.puntos_para_subir !== null
    ? `Llevas ${puntosTexto(puntos)} pts. Te faltan ${puntosTexto(yo.puntos_para_subir)} para ${yo.siguiente_division.nombre}.`
    : (yo.siguiente_division ? `Clasifica este mes para empezar a subir.` : 'Estás en lo más alto de la liga.');
  dialogo.showModal();
}

function subioDeDivision(yo) {
  return yo.clasificado && yo.division_mes_anterior
    && ORDEN_DIVISIONES.indexOf(yo.division.clave) > ORDEN_DIVISIONES.indexOf(yo.division_mes_anterior.clave);
}

function quizasCelebrar(yo) {
  if (yo.mes !== estado.mesActual || !subioDeDivision(yo)) return;
  const clave = `liga_ascenso_visto_${yo.mes}`;
  if (localStorage.getItem(clave) === yo.division.clave) return;
  localStorage.setItem(clave, yo.division.clave);
  mostrarEmblema(yo, true);
}

// ------------------------------------------------------------------- general

async function cargarYo() {
  try {
    const yo = await api(`/liga/yo?${consultaMes()}`);
    if (!estado.mesActual) estado.mesActual = yo.mes;
    estado.yo = yo;
    renderHero(yo);
    renderMisPlantas(yo);
    quizasCelebrar(yo);
  } catch (err) {
    document.getElementById('hero').innerHTML =
      `<p class="liga-cargando">No fue posible cargar tu división: ${escaparHtml(err.message)}</p>`;
  }
}

function cambiarMes(delta) {
  const base = estado.yo ? estado.yo.mes : estado.mesActual;
  const nuevo = mesDesplazado(base, delta);
  if (estado.mesActual && nuevo > estado.mesActual) return;
  estado.mes = nuevo === estado.mesActual ? null : nuevo;
  document.getElementById('titulo-ranking').textContent =
    estado.mes ? `Ranking de ${mesLegible(nuevo)}` : 'Ranking del mes';
  cargarYo();
  cargarRanking();
}

if (Sesion.exigir()) {
  document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => elegirAlcance(tab.dataset.alcance)));
  document.getElementById('form-amigo').addEventListener('submit', enviarSolicitud);
  document.getElementById('amigos').addEventListener('click', accionAmigo);
  cargarDivisiones().catch(() => {}).finally(() => {
    cargarYo();
    cargarRanking();
  });
  cargarAmigos();
}
