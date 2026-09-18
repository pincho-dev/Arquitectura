/*
 * Cliente web del sistema de diagnóstico.
 *
 * Este archivo se encarga de:
 * - manejar el formulario;
 * - comunicarse con la API;
 * - mostrar los datos recibidos.
 *
 * Las reglas para determinar BAJO, OPTIMO, ALTO y el
 * estado global de la planta pertenecen al backend.
 */


/*
 * Dirección de la API. Debe coincidir con FLASK_RUN_PORT
 * y con CORS_ORIGIN configurados en el .env del backend.
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
 * La lista de especies viene de RF5 (GET /especies).
 */
document.addEventListener("DOMContentLoaded", () => {
    prepararFormulario();
});


async function prepararFormulario() {

    selectorEspecie.innerHTML = "";
    selectorEspecie.disabled = true;
    estadoEspecies.textContent = "Cargando especies...";

    try {

        const respuesta = await fetch(`${API_URL}/especies`);

        if (!respuesta.ok) {
            throw new Error("La API respondió con un error al listar especies.");
        }

        const especies = await respuesta.json();

        const opcionInicial = document.createElement("option");
        opcionInicial.value = "";
        opcionInicial.textContent = "Seleccione una especie";
        selectorEspecie.appendChild(opcionInicial);

        especies.forEach((especie) => {
            const opcion = document.createElement("option");
            opcion.value = especie.nombre;
            opcion.textContent = capitalizar(especie.nombre);
            selectorEspecie.appendChild(opcion);
        });

        selectorEspecie.disabled = false;
        estadoEspecies.textContent = "";

    } catch (error) {

        selectorEspecie.innerHTML = "";

        const opcionError = document.createElement("option");
        opcionError.value = "";
        opcionError.textContent = "No se pudo cargar la lista de especies";
        selectorEspecie.appendChild(opcionError);

        estadoEspecies.textContent =
            "No fue posible comunicarse con la API para obtener las especies.";

    }

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
 * Realiza la petición de diagnóstico contra POST /diagnostico.
 *
 * El cuerpo de error que devuelve el backend en 4xx tiene
 * siempre la forma { error, mensaje, detalle } (ver RF6 en
 * backend/presentation/app.py).
 */
async function realizarDiagnostico(datos) {

    botonDiagnostico.disabled = true;
    botonDiagnostico.textContent = "Consultando...";

    try {

        const respuesta = await fetch(`${API_URL}/diagnostico`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                especie: datos.especie,
                humedad: Number(datos.humedad),
                luz: Number(datos.luz),
                temperatura: Number(datos.temperatura)
            })
        });

        const cuerpo = await respuesta.json();

        if (!respuesta.ok) {
            mostrarErrorApi(cuerpo.mensaje, cuerpo.error);
            return;
        }

        mostrarDiagnostico(cuerpo);

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
 * Esta función no calcula estados: solo toma lo que devuelve
 * POST /diagnostico y lo presenta.
 *
 * Contrato real (backend/presentation/app.py):
 * { especie, estado, recomendaciones, parametros: [{ nombre, valor, unidad, estado }] }
 */
function mostrarDiagnostico(diagnostico) {

    resultado.classList.remove("oculto");
    errorApi.classList.add("oculto");


    /*
     * Estado global de la planta (SALUDABLE / EN_RIESGO / CRITICO).
     * La clase adicional solo controla el color del badge (ver styles.css).
     */
    const elementoEstadoGlobal = document.getElementById("estado-global");

    elementoEstadoGlobal.textContent = diagnostico.estado ?? "-";
    elementoEstadoGlobal.className = "vitalidad";

    if (diagnostico.estado) {
        elementoEstadoGlobal.classList.add(`estado-${diagnostico.estado.toLowerCase()}`);
    }


    /*
     * Estados individuales: el backend los entrega como una
     * lista de parámetros, cada uno con su propio estado.
     */
    const idPorNombre = {
        humedad: "estado-humedad",
        luz: "estado-luz",
        temperatura: "estado-temperatura"
    };

    (diagnostico.parametros ?? []).forEach((parametro) => {
        const idElemento = idPorNombre[parametro.nombre.toLowerCase()];

        if (idElemento) {
            mostrarEstado(idElemento, parametro.estado);
        }
    });


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
     * El backend actual (EvaluadorDiagnostico) devuelve un
     * único texto fijo por estado global, no uno por parámetro
     * (simplificación documentada en la bitácora de IA).
     */
    if (typeof recomendaciones === "string") {

        const elemento = document.createElement("div");

        elemento.className = "recomendacion";
        elemento.textContent = recomendaciones;

        contenedor.appendChild(elemento);

        return;
    }


    /*
     * Soporta también un objeto de recomendaciones por
     * parámetro, por si el backend evoluciona hacia eso.
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
 * Pone en mayúscula la primera letra (para mostrar el
 * nombre de una especie en el selector).
 */
function capitalizar(texto) {

    return texto.charAt(0).toUpperCase() + texto.slice(1);

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
