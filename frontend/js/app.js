const API_URL = "http://localhost:5000";

// IMPORTANTE:
// Estos endpoints son temporales.
// Se deben cambiar cuando el equipo defina
// oficialmente las rutas del backend.

const ENDPOINTS = {
    especies: "",
    diagnostico: ""
};




const especie = document.getElementById("especie");

const humedad = document.getElementById("humedad");
const luz = document.getElementById("luz");
const temperatura = document.getElementById("temperatura");

const botonDiagnostico =
    document.getElementById("boton-diagnostico");

const resultado =
    document.getElementById("resultado");

const error =
    document.getElementById("error");

const mensajeError =
    document.getElementById("mensaje-error");




const indiceVitalidad =
    document.getElementById("indice-vitalidad");

const resultadoHumedad =
    document.getElementById("resultado-humedad");

const resultadoLuz =
    document.getElementById("resultado-luz");

const resultadoTemperatura =
    document.getElementById("resultado-temperatura");

const estadoIcon =
    document.getElementById("estado-icon");

const listaRecomendaciones =
    document.getElementById("lista-recomendaciones");




document.addEventListener("DOMContentLoaded", () => {

    cargarEspecies();

    botonDiagnostico.addEventListener(
        "click",
        ejecutarDiagnostico
    );

});


// CARGAR ESPECIES

async function cargarEspecies() {

    especie.innerHTML = "";

    const opcionInicial =
        document.createElement("option");

    opcionInicial.value = "";
    opcionInicial.textContent =
        "Selecciona una especie";

    especie.appendChild(opcionInicial);


    /*
     * El endpoint todavía no está definido.
     *
     * Por eso no hacemos una petición falsa.
     *
     * Cuando el backend defina RF5, solamente
     * será necesario colocar la ruta correspondiente
     * en ENDPOINTS.especies.
     */

    if (!ENDPOINTS.especies) {

        especie.disabled = true;

        const opcion =
            document.createElement("option");

        opcion.value = "";
        opcion.textContent =
            "Servicio de especies pendiente";

        especie.appendChild(opcion);

        return;
    }


    try {

        const response = await fetch(
            `${API_URL}${ENDPOINTS.especies}`
        );


        if (!response.ok) {

            throw new Error(
                "No fue posible obtener las especies."
            );

        }


        const especies = await response.json();


        especies.forEach(nombreEspecie => {

            const option =
                document.createElement("option");

            option.value = nombreEspecie;
            option.textContent = nombreEspecie;

            especie.appendChild(option);

        });


        especie.disabled = false;

    }

    catch (err) {

        mostrarError(
            "No fue posible cargar la lista de especies."
        );

        console.error(err);

    }

}


// EJECUTAR DIAGNÓSTICO

async function ejecutarDiagnostico() {

    ocultarError();

    resultado.classList.add("hidden");




    const especieSeleccionada =
        especie.value;

    const valorHumedad =
        Number(humedad.value);

    const valorLuz =
        Number(luz.value);

    const valorTemperatura =
        Number(temperatura.value);


    if (!especieSeleccionada) {

        mostrarError(
            "Selecciona una especie antes de realizar el diagnóstico."
        );

        return;
    }


    if (
        humedad.value === "" ||
        luz.value === "" ||
        temperatura.value === ""
    ) {

        mostrarError(
            "Debes ingresar humedad, luz y temperatura."
        );

        return;
    }


    if (
        !Number.isFinite(valorHumedad) ||
        !Number.isFinite(valorLuz) ||
        !Number.isFinite(valorTemperatura)
    ) {

        mostrarError(
            "Los valores ingresados deben ser numéricos."
        );

        return;
    }


    // COMPROBACIONES FÍSICAS BÁSICAS

    if (valorHumedad < 0) {

        mostrarError(
            "La humedad no puede ser negativa."
        );

        return;
    }


    if (valorLuz < 0) {

        mostrarError(
            "La intensidad de luz no puede ser negativa."
        );

        return;
    }


    // ------------------------------------
    // ENDPOINT TODAVÍA NO DEFINIDO
    // ------------------------------------

    if (!ENDPOINTS.diagnostico) {

        mostrarError(
            "El endpoint de diagnóstico todavía no ha sido definido por el equipo."
        );

        return;
    }


    // DATOS QUE SE ENVIARÁN AL BACKEND

    const datos = {

        especie: especieSeleccionada,

        humedad: valorHumedad,

        luz: valorLuz,

        temperatura: valorTemperatura

    };


    try {

        botonDiagnostico.disabled = true;

        botonDiagnostico.querySelector("span:first-child")
            .textContent = "Analizando...";


        const response = await fetch(
            `${API_URL}${ENDPOINTS.diagnostico}`,
            {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(datos)

            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            const mensaje =
                data.mensaje ||
                data.error ||
                "El servidor rechazó la solicitud.";

            throw new Error(mensaje);
        }


        mostrarDiagnostico(data);

    }

    catch (err) {

        mostrarError(
            err.message ||
            "No fue posible conectarse con el servicio."
        );

        console.error(err);

    }

    finally {

        botonDiagnostico.disabled = false;

        botonDiagnostico.querySelector("span:first-child")
            .textContent = "Analizar planta";

    }

}


// MOSTRAR DIAGNÓSTICO

function mostrarDiagnostico(data) {

    resultado.classList.remove("hidden");


    /*
     * Estos nombres son provisionales.
     *
     * Cuando el equipo defina el JSON definitivo,
     * solamente se adapta esta función.
     *
     * La lógica del diagnóstico NO se implementa
     * aquí.
     */


    indiceVitalidad.textContent =
        data.indice_vitalidad || "--";


    resultadoHumedad.textContent =
        data.humedad || "--";


    resultadoLuz.textContent =
        data.luz || "--";


    resultadoTemperatura.textContent =
        data.temperatura || "--";


    cambiarIconoEstado(
        data.indice_vitalidad
    );


    mostrarRecomendaciones(
        data.recomendaciones
    );


    resultado.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

}




function cambiarIconoEstado(estado) {

    if (!estado) {

        estadoIcon.textContent = "🌱";

        return;
    }


    const valor =
        String(estado).toUpperCase();


    if (valor.includes("CRITICO")) {

        estadoIcon.textContent = "⚠️";

    }

    else if (valor.includes("RIESGO")) {

        estadoIcon.textContent = "🌿";

    }

    else if (valor.includes("SALUDABLE")) {

        estadoIcon.textContent = "🌱";

    }

    else {

        estadoIcon.textContent = "🌱";

    }

}




function mostrarRecomendaciones(
    recomendaciones
) {

    listaRecomendaciones.innerHTML = "";


    if (!recomendaciones) {

        listaRecomendaciones.innerHTML =
            `<p>No hay recomendaciones disponibles.</p>`;

        return;
    }


    // Si el backend devuelve un objeto
    if (
        typeof recomendaciones === "object" &&
        !Array.isArray(recomendaciones)
    ) {

        Object.entries(recomendaciones)
            .forEach(([parametro, mensaje]) => {

                agregarRecomendacion(
                    `${parametro}: ${mensaje}`
                );

            });

        return;
    }


    // Si el backend devuelve una lista
    if (Array.isArray(recomendaciones)) {

        recomendaciones.forEach(
            recomendacion => {

                agregarRecomendacion(
                    recomendacion
                );

            }
        );

        return;
    }


    agregarRecomendacion(
        recomendaciones
    );

}




function agregarRecomendacion(texto) {

    const elemento =
        document.createElement("div");

    elemento.className =
        "recommendation-item";

    elemento.textContent =
        `💡 ${texto}`;

    listaRecomendaciones.appendChild(
        elemento
    );

}




function mostrarError(mensaje) {

    error.classList.remove("hidden");

    mensajeError.textContent = mensaje;

    error.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });

}



function ocultarError() {

    error.classList.add("hidden");

}
