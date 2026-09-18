/*
 * Panel de estado de la API.
 *
 * Cliente estático independiente: hace polling a GET /estado
 * cada 2 segundos y muestra lo que devuelve. No calcula nada,
 * solo presenta lo que entrega el backend.
 */

const API_URL = "http://localhost:5000";
const INTERVALO_MS = 2000;

const puntoActividad = document.getElementById("punto-actividad");
const tituloServicio = document.getElementById("titulo-servicio");
const detalleServicio = document.getElementById("detalle-servicio");
const listaSolicitudes = document.getElementById("lista-solicitudes");


async function actualizarEstado() {

    try {

        const respuesta = await fetch(`${API_URL}/estado`);

        if (!respuesta.ok) {
            throw new Error("La API respondió con un error.");
        }

        const estado = await respuesta.json();

        mostrarServicioActivo(estado);
        mostrarSolicitudes(estado.solicitudes_recientes ?? []);

    } catch (error) {

        mostrarServicioCaido();

    }

}


function mostrarServicioActivo(estado) {

    puntoActividad.classList.remove("punto-inactiva");
    puntoActividad.classList.add("punto-activa");

    tituloServicio.textContent = "API activa";

    const hora = new Date(estado.hora_servidor).toLocaleTimeString();

    detalleServicio.textContent =
        `${estado.especies_cargadas} especies cargadas · actualizado ${hora}`;

}


function mostrarServicioCaido() {

    puntoActividad.classList.remove("punto-activa");
    puntoActividad.classList.add("punto-inactiva");

    tituloServicio.textContent = "API no disponible";
    detalleServicio.textContent =
        "No fue posible comunicarse con el backend en " + API_URL;

}


function mostrarSolicitudes(solicitudes) {

    if (solicitudes.length === 0) {
        listaSolicitudes.innerHTML =
            '<p class="texto-ayuda">Todavía no hay solicitudes registradas.</p>';
        return;
    }

    listaSolicitudes.innerHTML = "";

    solicitudes.forEach((solicitud) => {

        const fila = document.createElement("div");
        fila.className = "solicitud";

        const metodo = document.createElement("span");
        metodo.className = `metodo metodo-${solicitud.metodo.toLowerCase()}`;
        metodo.textContent = solicitud.metodo;

        const ruta = document.createElement("span");
        ruta.className = "ruta";
        ruta.textContent = solicitud.ruta;

        const codigo = document.createElement("span");
        codigo.className = `codigo ${solicitud.estado >= 400 ? "codigo-error" : "codigo-ok"}`;
        codigo.textContent = solicitud.estado;

        const hora = document.createElement("span");
        hora.className = "hora";
        hora.textContent = new Date(solicitud.hora).toLocaleTimeString();

        fila.append(metodo, ruta, codigo, hora);
        listaSolicitudes.appendChild(fila);

    });

}


actualizarEstado();
setInterval(actualizarEstado, INTERVALO_MS);
