// Galería: subir fotos de mis plantas y ver las de todos. Las imágenes piden
// el JWT, así que no van directo en <img src>: se descargan con fetch y se
// muestran como blob (URL.createObjectURL).
const POR_PAGINA = 12;
const estado = { ultimoId: null, planta: '', cargando: false, urls: new Map() };

function fechaLegible(iso) {
  return new Date(iso).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' });
}

async function subirFormulario(ruta, datos) {
  const respuesta = await fetch(`${API_BASE_URL}${ruta}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${Sesion.token()}` },
    body: datos, // FormData: el navegador pone el multipart/form-data
  });
  const cuerpo = await respuesta.json().catch(() => ({}));
  if (respuesta.status === 401) { Sesion.cerrar(); Sesion.exigir(); }
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, cuerpo);
  return cuerpo;
}

async function cargarImagen(img, ruta) {
  try {
    const respuesta = await fetch(`${API_BASE_URL.replace(/\/api$/, '')}${ruta}`, {
      headers: { Authorization: `Bearer ${Sesion.token()}` },
    });
    if (!respuesta.ok) throw new Error();
    const url = URL.createObjectURL(await respuesta.blob());
    estado.urls.set(img, url);
    img.src = url;
  } catch {
    img.closest('.foto-marco').classList.add('foto-error');
  }
}

// Solo se descarga cada imagen cuando está por aparecer en pantalla.
const observador = new IntersectionObserver((entradas) => {
  entradas.forEach(e => {
    if (!e.isIntersecting) return;
    observador.unobserve(e.target);
    cargarImagen(e.target, e.target.dataset.ruta);
  });
}, { rootMargin: '400px' });

function tarjetaFoto(f) {
  const tarjeta = document.createElement('article');
  tarjeta.className = 'foto';
  const l = f.lectura;
  const lecturaHtml = l
    ? `<div class="foto-lectura">
         <span class="badge ${ESTADO_CLASE[l.estado]}">${escaparHtml(l.estado_texto)}</span>
         <span>💧 ${formatoValor(l.humedad, '%')}</span>
         <span>☀️ ${formatoValor(l.luz, ' lux')}</span>
         <span>🌡️ ${formatoValor(l.temperatura, '°C')}</span>
       </div>`
    : '<p class="foto-sin-lectura">Sin lecturas de la matera cuando se subió.</p>';

  tarjeta.innerHTML = `
    <button type="button" class="foto-marco" style="aspect-ratio: ${f.ancho} / ${f.alto}"
      aria-label="Ver en grande la foto de ${escaparHtml(f.planta.nombre)}">
      <img alt="${escaparHtml(f.descripcion || `Foto de ${f.planta.nombre}`)}" data-ruta="${f.imagen_url}">
    </button>
    <div class="foto-cuerpo">
      <div class="foto-cabecera">
        <div>
          <h3 class="foto-planta">${ICONO_ESPECIE[f.planta.especie] || '🌿'} ${escaparHtml(f.planta.nombre)}</h3>
          <p class="foto-autor">${escaparHtml(f.planta.especie)} · de ${escaparHtml(f.autor.nombre)} · ${fechaLegible(f.creada_en)}</p>
        </div>
        ${f.puede_borrar ? '<button type="button" class="boton-borrar">Borrar</button>' : ''}
      </div>
      ${f.descripcion ? `<p class="foto-descripcion">${escaparHtml(f.descripcion)}</p>` : ''}
      ${lecturaHtml}
    </div>`;

  const img = tarjeta.querySelector('img');
  observador.observe(img);
  tarjeta.querySelector('.foto-marco').addEventListener('click', () => abrirVisor(img));
  const borrar = tarjeta.querySelector('.boton-borrar');
  if (borrar) borrar.addEventListener('click', () => borrarFoto(f, tarjeta, borrar));
  return tarjeta;
}

async function cargarFotos({ reiniciar = false } = {}) {
  if (estado.cargando) return;
  estado.cargando = true;
  const contenedor = document.getElementById('fotos');
  const masBoton = document.getElementById('cargar-mas');
  const fin = document.getElementById('fin');
  if (reiniciar) {
    estado.urls.forEach(url => URL.revokeObjectURL(url));
    estado.urls.clear();
    estado.ultimoId = null;
    contenedor.innerHTML = '';
  }
  const parametros = new URLSearchParams({ limite: POR_PAGINA });
  if (estado.ultimoId) parametros.set('antes_de', estado.ultimoId);
  if (estado.planta) parametros.set('planta', estado.planta);

  try {
    const fotos = await api(`/fotos?${parametros}`);
    fotos.forEach(f => contenedor.appendChild(tarjetaFoto(f)));
    if (fotos.length) estado.ultimoId = fotos[fotos.length - 1].id;
    masBoton.hidden = fotos.length < POR_PAGINA;
    fin.textContent = contenedor.children.length === 0
      ? 'Todavía no hay fotos. ¡Sube la primera!'
      : (fotos.length < POR_PAGINA ? 'Ya viste todas las fotos.' : '');
  } catch (err) {
    fin.textContent = `No fue posible cargar la galería: ${err.message}`;
  } finally {
    estado.cargando = false;
  }
}

async function borrarFoto(f, tarjeta, boton) {
  // Dos toques para borrar: evita borrar sin querer desde el celular.
  if (!boton.dataset.confirmar) {
    boton.dataset.confirmar = '1';
    boton.textContent = '¿Seguro? Toca otra vez';
    setTimeout(() => { delete boton.dataset.confirmar; boton.textContent = 'Borrar'; }, 4000);
    return;
  }
  boton.disabled = true;
  try {
    await api(`/fotos/${f.id}`, { metodo: 'DELETE' });
    const img = tarjeta.querySelector('img');
    if (estado.urls.has(img)) URL.revokeObjectURL(estado.urls.get(img));
    tarjeta.remove();
  } catch (err) {
    boton.disabled = false;
    boton.textContent = err.message;
  }
}

function abrirVisor(img) {
  if (!img.src) return;
  const grande = document.getElementById('visor-imagen');
  grande.src = img.src;
  grande.alt = img.alt;
  document.getElementById('visor').showModal();
}

// ------------------------------------------------------------- subir foto

async function cargarMisPlantas() {
  const selector = document.getElementById('planta');
  const filtro = document.getElementById('filtro');
  try {
    const plantas = await api('/plantas');
    if (plantas.length === 0) {
      selector.innerHTML = '<option value="">No tienes plantas todavía</option>';
      document.getElementById('boton-subir').disabled = true;
      document.getElementById('mensaje').innerHTML = 'Primero <a href="reclamar.html">reclama tu matera</a> para subir fotos.';
      return;
    }
    selector.innerHTML = plantas.map(p => `<option value="${p.id}">${escaparHtml(p.nombre)}</option>`).join('');
    filtro.insertAdjacentHTML('beforeend',
      plantas.map(p => `<option value="${p.id}">Solo ${escaparHtml(p.nombre)}</option>`).join(''));
    // Desde el detalle de una planta se llega con ?planta=ID ya elegida.
    const pedida = new URLSearchParams(location.search).get('planta');
    if (pedida && plantas.some(p => String(p.id) === pedida)) selector.value = pedida;
  } catch (err) {
    document.getElementById('mensaje').textContent = `No fue posible cargar tus plantas: ${err.message}`;
  }
}

function mostrarPrevia() {
  const archivo = document.getElementById('archivo').files[0];
  const caja = document.getElementById('vista-previa');
  const previa = document.getElementById('previa');
  if (previa.src) URL.revokeObjectURL(previa.src);
  if (!archivo) { caja.hidden = true; previa.removeAttribute('src'); return; }
  previa.src = URL.createObjectURL(archivo);
  caja.hidden = false;
}

async function publicar(evento) {
  evento.preventDefault();
  const mensaje = document.getElementById('mensaje');
  const archivo = document.getElementById('archivo').files[0];
  const planta = document.getElementById('planta').value;
  if (!planta) { mensaje.textContent = 'Elige una planta.'; return; }
  if (!archivo) { mensaje.textContent = 'Elige una foto.'; return; }
  if (archivo.size > 10 * 1024 * 1024) { mensaje.textContent = 'La foto pesa más de 10 MB.'; return; }

  const datos = new FormData();
  datos.append('foto', archivo);
  datos.append('descripcion', document.getElementById('descripcion').value);
  const boton = document.getElementById('boton-subir');
  boton.disabled = true;
  boton.textContent = 'Subiendo…';
  mensaje.textContent = '';
  try {
    await subirFormulario(`/plantas/${planta}/fotos`, datos);
    evento.target.reset();
    mostrarPrevia();
    document.getElementById('contador').textContent = '0/280';
    mensaje.textContent = '¡Foto publicada!';
    await cargarFotos({ reiniciar: true });
  } catch (err) {
    mensaje.textContent = err.message;
  } finally {
    boton.disabled = false;
    boton.textContent = 'Publicar foto';
  }
}

if (Sesion.exigir()) {
  document.getElementById('archivo').addEventListener('change', mostrarPrevia);
  document.getElementById('descripcion').addEventListener('input', (e) => {
    document.getElementById('contador').textContent = `${e.target.value.length}/280`;
  });
  document.getElementById('form-foto').addEventListener('submit', publicar);
  document.getElementById('cargar-mas').addEventListener('click', () => cargarFotos());
  document.getElementById('filtro').addEventListener('change', (e) => {
    estado.planta = e.target.value;
    cargarFotos({ reiniciar: true });
  });
  cargarMisPlantas();
  cargarFotos();
}
