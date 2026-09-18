/*
 * Cliente web del sistema de diagnóstico.
 *
 * Este archivo se encarga de:
 * - manejar el formulario;
 * - comunicarse con la API;
 * - mostrar los datos recibidos.
 *
 * Las reglas para determinar BAJO, OPTIMO, ALTO e
 * índice de vitalidad pertenecen al backend.
 */


/*
 * Dirección temporal de la API.
 *
 * Cuando el equipo defina la dirección y los endpoints
 * definitivos, solamente se debe actualizar esta sección.
 */
const API_URL = "http://localhost:5000";


/*
 * Elementos principales de la página.
 */
const formulario = document.getElementById("diagnostico-form");
const selectorEspecie = document.getElementById("especie");
const estadoEspecies = document.getElementById("estado-especies");

const resultado = document.getElementById("resultado");
const errorApi = document.getElementById("error-api");

const mensajeFormulario = document.getElementById("mensaje-formulario");
const mensajeError = document.getElementById("mensaje-error");
const codigoError = document.getElementById("codigo-error");

const botonDiagnostico = document.getElementById("boton-diagnostico");


/*
 * Carga inicial.
 *
 * La lista de especies debe venir de RF5.
 * Todavía no se llama a un endpoint porque el contrato
 * de la API aún no ha sido definido por el equipo.
 */
document.addEventListener("DOMContentLoaded", () => {
    prepararFormulario();
});


function prepararFormulario() {

    selectorEspecie.innerHTML = "";

    const opcionInicial = document.createElement("option");

    opcionInicial.value = "";
    opcionInicial.textContent = "Endpoint de especies pendiente";

    selectorEspecie.appendChild(opcionInicial);

    selectorEspecie.disabled = true;

    estadoEspecies.textContent =
        "El endpoint de RF5 todavía no ha sido definido.";

}


/*
 * Evento principal del formulario.
 */
formulario.addEventListener("submit", async (evento) => {

    evento.preventDefault();

    ocultarMensajes();

    const datos = obtenerDatosFormulario();

    if (!validarFormulario(datos)) {
        return;
    }

    await realizarDiagnostico(datos);
});


/*
 * Obtiene únicamente los datos introducidos por el usuario.
 */
function obtenerDatosFormulario() {

    return {
        especie: selectorEspecie.value,
        humedad: document.getElementById("humedad").value,
        luz: document.getElementById("luz").value,
        temperatura: document.getElementById("temperatura").value
    };

}


/*
 * Validaciones propias de la interfaz.
 *
 * No se validan aquí los rangos de referencia de la especie.
 * Esa decisión corresponde al backend.
 */
function validarFormulario(datos) {

    if (!datos.especie) {
        mostrarMensajeFormulario(
            "Seleccione una especie antes de continuar."
        );

        return false;
    }


    if (
        datos.humedad === "" ||
        datos.luz === "" ||
        datos.temperatura === ""
    ) {

        mostrarMensajeFormulario(
            "Complete los tres parámetros de la medición."
        );

        return false;
    }


    if (
        !esNumero(datos.humedad) ||
        !esNumero(datos.luz) ||
        !esNumero(datos.temperatura)
    ) {

        mostrarMensajeFormulario(
            "Los valores de la medición deben ser numéricos."
        );

        return false;
    }


    return true;
}


/*
 * Comprueba si un valor puede convertirse en número.
 */
function esNumero(valor) {

    return valor.trim() !== "" && Number.isFinite(Number(valor));

}


/*
 * Realiza la petición de diagnóstico.
 *
 * IMPORTANTE:
 * El endpoint y la estructura del JSON son temporales.
 * Esta función será ajustada cuando el backend defina
 * oficialmente su contrato.
 */
async function realizarDiagnostico(datos) {

    botonDiagnostico.disabled = true;
    botonDiagnostico.textContent = "Consultando...";


    try {

        /*
         * TODO:
         *
         * Cuando el backend defina el endpoint, esta petición
         * se completará con la ruta y el JSON acordados.
         *
         * Ejemplo de estructura:
         *
         * fetch(`${API_URL}/ruta-definitiva`, {
         *     method: "POST",
         *     headers: {
         *         "Content-Type": "application/json"
         *     },
         *     body: JSON.stringify(datos)
         * });
         */


        mostrarErrorApi(
            "El endpoint de diagnóstico todavía no ha sido definido.",
            "API pendiente"
        );

    } catch (error) {

        mostrarErrorApi(
            "No fue posible comunicarse con el servicio de diagnóstico.",
            "ERROR_RED"
        );

    } finally {

        botonDiagnostico.disabled = false;
        botonDiagnostico.textContent = "Consultar diagnóstico";

    }

}


/*
 * Muestra el diagnóstico recibido desde la API.
 *
 * Esta función no calcula estados.
 * Solamente toma los valores entregados por el backend
 * y los presenta en pantalla.
 *
 * La estructura exacta del objeto se ajustará al contrato
 * definitivo de la API.
 */
function mostrarDiagnostico(diagnostico) {

    resultado.classList.remove("oculto");
    errorApi.classList.add("oculto");


    /*
     * Índice de vitalidad.
     */
    document.getElementById("indice-vitalidad").textContent =
        diagnostico.indice_vitalidad ?? "-";


    /*
     * Estados individuales.
     */
    mostrarEstado(
        "estado-humedad",
        diagnostico.humedad
    );

    mostrarEstado(
        "estado-luz",
        diagnostico.luz
    );

    mostrarEstado(
        "estado-temperatura",
        diagnostico.temperatura
    );


    /*
     * Recomendaciones.
     */
    mostrarRecomendaciones(
        diagnostico.recomendaciones
    );

}


/*
 * Presenta un estado recibido desde la API.
 */
function mostrarEstado(idElemento, estado) {

    const elemento = document.getElementById(idElemento);

    elemento.textContent = estado ?? "-";

    elemento.classList.remove(
        "estado-bajo",
        "estado-optimo",
        "estado-alto"
    );


    if (!estado) {
        return;
    }


    const estadoNormalizado =
        String(estado).toUpperCase();


    if (estadoNormalizado === "BAJO") {

        elemento.classList.add("estado-bajo");

    } else if (estadoNormalizado === "OPTIMO") {

        elemento.classList.add("estado-optimo");

    } else if (estadoNormalizado === "ALTO") {

        elemento.classList.add("estado-alto");

    }

}


/*
 * Presenta las recomendaciones entregadas por la API.
 */
function mostrarRecomendaciones(recomendaciones) {

    const contenedor =
        document.getElementById("lista-recomendaciones");

    contenedor.innerHTML = "";


    if (!recomendaciones) {

        const mensaje = document.createElement("div");

        mensaje.className = "recomendacion";
        mensaje.textContent =
            "No se recibieron recomendaciones.";

        contenedor.appendChild(mensaje);

        return;
    }


    /*
     * Permite trabajar inicialmente con un objeto de
     * recomendaciones por parámetro.
     *
     * La estructura definitiva se ajustará al contrato
     * del backend.
     */
    if (
        typeof recomendaciones === "object" &&
        !Array.isArray(recomendaciones)
    ) {

        Object.entries(recomendaciones).forEach(
            ([parametro, texto]) => {

                const elemento =
                    document.createElement("div");

                elemento.className = "recomendacion";

                elemento.textContent =
                    `${formatearParametro(parametro)}: ${texto}`;

                contenedor.appendChild(elemento);

            }
        );

        return;
    }


    /*
     * También permite una lista de textos.
     */
    if (Array.isArray(recomendaciones)) {

        recomendaciones.forEach((texto) => {

            const elemento =
                document.createElement("div");

            elemento.className = "recomendacion";
            elemento.textContent = texto;

            contenedor.appendChild(elemento);

        });

    }

}


/*
 * Convierte los nombres técnicos de los parámetros
 * en nombres más legibles para la interfaz.
 */
function formatearParametro(parametro) {

    const nombres = {
        humedad: "Humedad",
        luz: "Luz",
        temperatura: "Temperatura"
    };

    return nombres[parametro] ?? parametro;

}


/*
 * Muestra un mensaje relacionado con el formulario.
 */
function mostrarMensajeFormulario(mensaje) {

    mensajeFormulario.textContent = mensaje;

    mensajeFormulario.classList.remove("oculto");
    mensajeFormulario.classList.add("error");

}


/*
 * Muestra un error procedente de la comunicación
 * con la API.
 */
function mostrarErrorApi(mensaje, codigo = "") {

    resultado.classList.add("oculto");

    errorApi.classList.remove("oculto");

    mensajeError.textContent = mensaje;

    codigoError.textContent =
        codigo ? `Código: ${codigo}` : "";

}


/*
 * Limpia los mensajes anteriores.
 */
function ocultarMensajes() {

    mensajeFormulario.classList.add("oculto");
    errorApi.classList.add("oculto");

}
