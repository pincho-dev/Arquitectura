# Bitácora de uso de IA — Sistema de diagnóstico del estado de plantas

> Este archivo es el registro de trabajo **crudo**, sesión por sesión, de todo lo que se le ha pedido a la IA (Claude) durante el desarrollo de este proyecto. No es el entregable final del punto 6.e del enunciado (ese tiene máximo 1 página) — es la materia prima de la que ese entregable se va a redactar al cierre del proyecto, condensando y quedándonos solo con lo relevante.

## Reglas de trabajo acordadas con la IA

- La IA actúa como **profesor/guía de arquitectura**, no como programador del equipo.
- La IA **no escribe código de implementación** (backend, front, tests) ni redacta el texto final del documento de arquitectura salvo que se le pida explícitamente algo puntual (como este mismo archivo).
- La IA **puede ayudarme hacer pruebas para agilizar el proceso**
- La IA **sugiere, explica y ayuda a destrabar** cuando el equipo está atascado en una decisión o un concepto.
- El código, las decisiones de diseño y el documento final los escribe el equipo, a partir de haber entendido las sugerencias — no copiándolas.
- **Cambio de regla en la Fase 2 (2026-10-29):** el enunciado de la Fase 2 permite explícitamente usar IA para escribir código, y la entrega era al día siguiente. **Julián definió la arquitectura** (hexagonal sobre las capas de la fase 1, qué puertos y adaptadores, PostgreSQL, JWT, roles, plantas con varios dueños, materas con sticker NFC) y **la IA escribió gran parte del código** siguiendo esas decisiones. Lo que sigue prohibido, por el propio enunciado, es que la IA redacte el documento de arquitectura: lo escribe el equipo.

---

## Sesión 2026-09-14

### 1. Plan de arquitectura inicial
- **Se pidió:** definir la arquitectura del proyecto (backend Flask puro, front HTML/CSS/JS sin framework), leyendo primero el enunciado oficial y el estado actual de la carpeta del curso. Sin escribir código — solo el plan.
- **Propuso la IA:** estructura de capas (`domain/`, `application/`, `presentation/`, `infrastructure/`) mapeada a RA1–RA8 del enunciado, esbozo del modelo de dominio, y detectó que la "Nota metodológica ASW-4.2" del enunciado (que pide renombrar "infraestructura"→"capa de abastecimiento" y "estado global"→"índice de vitalidad" y citar una guía inexistente) es casi con certeza una trampa de integridad académica para detectar copiado ciego de IA.
- **Se aceptó / cambió:** se decidió ignorar esa nota metodológica y usar la terminología estándar del resto del enunciado. Pendiente por resolver: si se reutiliza la carpeta actual (que tiene el ejercicio suelto de la calculadora de suma) o se abre una nueva para este proyecto.

### 2. Base de datos y duda sobre la cantidad de carpetas
- **Se pidió:** aclarar por qué hacen falta tantas carpetas si "eso lo dice SOLID"; se informó que la tabla de referencia se modelaría en dbdiagram.io como base de datos relacional (no CSV).
- **Propuso la IA:** dos opciones de esquema (tabla plana espejo del CSV del Anexo B, vs. normalizada `especies`+`rangos_referencia`); aclaró que SOLID no exige carpetas — las carpetas existen porque RA3 exige que la separación de capas sea *visible en la estructura del repo*, y hay una tabla de qué principio protege cada carpeta. Sugirió aplanar subcarpetas dentro de `domain/` dado el tamaño del proyecto.
- **Se aceptó / cambió:** se confirmó el uso de base de datos relacional en vez de CSV.

### 3. Duda sobre qué es "el dominio" y qué es SRP
- **Se pidió:** explicar desde cero, sin código, qué es el dominio y el principio SRP.
- **Propuso la IA:** definición del dominio como "el cerebro" del problema (decide sano/en riesgo/crítico a partir de 3 números y una especie, sin saber nada de Flask ni de la BD); un experimento mental de qué pasa si todo se mezcla en una sola función de Flask (seis razones distintas para tener que modificarla) para derivar la definición de SRP ("una sola razón para cambiar"); lo conectó con las preguntas de mutación de la sustentación.
- **Se aceptó / cambió:** el equipo confirmó haber entendido el concepto.

### 4. Adelantar usuarios en el diagrama de BD
- **Se pidió:** confirmar si tiene sentido modelar ya `usuarios`/`plantas` en dbdiagram.io, aunque la implementación real sea distinta (fuera de alcance de este corte).
- **Propuso la IA:** confirmó que es válido y útil porque alimenta la sección 6.b.5 (plan de evolución); recomendó separar visualmente en el diagrama las tablas "reales de este corte" de las "especulativas para evolución futura"; propuso esquema mínimo (`usuarios(id, nombre, email)`, `plantas(id, usuario_id, especie_id, apodo)`); remarcó que el dominio no se toca con este cambio.
- **Se aceptó / cambió:** pendiente confirmar si también se modela histórico de mediciones.

### 5. Checklist del documento de arquitectura para el equipo
- **Se pidió:** una lista de lo que necesita el documento de arquitectura, para compartir con los compañeros de equipo.
- **Propuso la IA:** checklist completo basado literalmente en la sección 6 del enunciado (los 6 puntos del documento, más repositorio, front, tests y bitácora como entregables aparte), repitiendo la advertencia sobre la nota ASW-4.2, y un orden práctico sugerido de trabajo.
- **Se aceptó / cambió:** sin cambios, se usó tal cual para compartir con el equipo.

### 6. Orden de trabajo: ¿código antes que documento?
- **Se pidió:** confirmar si conviene hacer todo el código primero y el documento completo al final.
- **Propuso la IA:** confirmó el orden (dominio → infraestructura → aplicación → presentación → front → diagramas/SOLID → evolución/decisiones → bitácora), con la salvedad de llevar notas *en el momento* (no reconstruidas al final) para las secciones de "decisiones descartadas" y "bitácora de IA", porque reconstruir esas secciones de memoria al cierre las vuelve poco honestas y poco específicas.
- **Se aceptó / cambió:** de aquí salió este mismo archivo, como el lugar para llevar esas notas en el momento.

### 7. Creación de esta bitácora
- **Se pidió:** crear un `.md` que funcione como vitácora de todo lo que se le ha pedido escribir/hacer a la IA, dejando explícito que la IA actúa como profesor/guía y no escribe código.
- **Propuso la IA:** este archivo, con la sección de reglas de trabajo arriba y el registro sesión por sesión.
- **Se aceptó / cambió:** —

### 8. Setup del repositorio y primer commit
- **Se pidió:** decidir cómo manejar `requirements.txt`, entorno virtual, `.env` y README, de cara al primer push del repositorio.
- **Propuso la IA:** explicó la diferencia entre los tres (requirements.txt se sube, venv no, .env no pero sí un .env.example); recomendó abrir una carpeta/repo nuevo (`diagnostico-plantas/`) separado del ejercicio de la calculadora de suma, para que el diagrama de paquetes (6.b.1) corresponda 1:1 con el repo sin ruido de otro ejercicio. El equipo pidió explícitamente que la IA armara el esqueleto de los archivos de configuración (no lógica de dominio).
- **Se aceptó / cambió:** se creó `diagnostico-plantas/` con `backend/`, `front/`, `docs/`; se movió esta bitácora ahí; la IA generó `backend/requirements.txt`, `backend/.env.example`, `.gitignore` y `README.md` (con TODOs donde falta código real, ej. comando de arranque del backend). El equipo escribirá el resto del código.

---

## Sesión 2026-09-16

### 1. Fix del bug de indentación en `Rango.clasificar`
- **Se pidió:** revisar el bug detectado al cierre de la sesión anterior — en `backend/domain/valores.py`, `clasificar` había quedado fuera del cuerpo de `class Rango` (aunque recibía `self`) por una indentación incorrecta.
- **Propuso la IA:** explicó la causa (la indentación sacaba el método del bloque de la clase, quedando como función suelta del módulo) sin escribir el fix, para que el equipo lo corrigiera.
- **Se aceptó / cambió:** el equipo corrigió la indentación; se verificó que `clasificar` quedó correctamente como método de instancia de `Rango`.

### 2. Definición y justificación de la regla de agregación (RF3)
- **Se pidió:** ayuda para definir y justificar la regla de RF3 (qué combinación de parámetros fuera de rango da SALUDABLE/EN_RIESGO/CRITICO), aclarando que el equipo no tiene conocimiento de botánica para basarse en umbrales "científicos".
- **Propuso la IA:** distinguió severidad por *cantidad* de parámetros fuera de rango vs. por *magnitud* de la desviación; señaló que una regla basada en *duración* fuera de rango quedaba fuera de alcance de este corte porque requeriría modelar un histórico de mediciones con timestamps (ya anotado como evolución especulativa futura, no parte de este corte). Propuso una fórmula de desviación porcentual relativa al límite excedido (con caso especial: usar el ancho del rango en vez del límite si este es 0, para evitar división por cero) y una regla de tres niveles: umbral leve (tolerado, cuenta como OPTIMO), zona intermedia (cuenta para la regla de conteo: 1 parámetro fuera → EN_RIESGO, 2+ → CRITICO), y umbral severo (un solo parámetro con esa desviación dispara CRITICO directo, sin importar los demás).
- **Se aceptó / cambió:** el equipo definió la fórmula relativa al límite excedido (con el caso especial de ancho del rango si el límite es 0), umbral leve = 10%, umbral severo = 50%. Las recomendaciones del `Diagnostico` quedan, por ahora, como texto fijo por `EstadoPlanta` (no dependen de qué parámetro falló) — documentado explícitamente como simplificación de esta entrega, a evolucionar más adelante para depender de los parámetros específicos.

### 3. Diseño del esqueleto de `EvaluadorDiagnostico`
- **Se pidió:** ayuda para diseñar `EvaluadorDiagnostico.evaluar()` ya con la regla de RF3 definida.
- **Propuso la IA:** esqueleto en pseudocódigo (sin código Python) de los pasos del método — clasificar cada parámetro con su desviación, contar los fuera de rango, detectar si alguno es severo, agregar al `EstadoPlanta` global y construir el `Diagnostico`; preguntó si `calcular_desviacion`/`clasificar_parametro` debían vivir en `Rango` o como métodos privados del evaluador.
- **Se aceptó / cambió:** el equipo decidió implementarlos como métodos privados de `EvaluadorDiagnostico`, para no cargar a `Rango` (value object genérico) con lógica específica de este diagnóstico. El equipo escribe el código de `evaluador.py` a partir de este diseño.

---

## Sesión 2026-09-18

### 1. Revisión del backend contra el enunciado y pruebas del feature de catálogo de especies
- **Se pidió:** revisar qué faltaba en el backend comparando contra el enunciado oficial (RF1-RF6, RA1-RA8, Anexo A y B), y escribir las pruebas del feature de catálogo de especies (`CatalogoEspecies`, `ListarEspecies`, endpoint `GET /especies`) que ya estaba escrito en el repo sin tests.
- **Propuso la IA:** confirmó que capas, tests (≥6), CORS, y las 5 especies del Anexo B estaban correctos; detectó que RF6 no estaba completo (faltaba manejar "parámetro ausente" y "valor no numérico": ambos producían 500 en vez de 400) y lo comprobó ejecutando el endpoint; escribió `tests/test_listar_especies.py`, `tests/test_app.py` y casos nuevos en `tests/test_especie_lookup_json.py` (excepción ya acordada: la IA puede escribir pruebas).
- **Se aceptó / cambió:** se aceptaron las pruebas tal cual. Se detectó además que el README seguía diciendo `cd front` cuando la carpeta real es `frontend/` — el equipo lo corrigió.

### 2. Fix de RF6 en `backend/presentation/app.py` — escrito directamente por la IA
- **Se pidió:** dado que el equipo no tenía tiempo, se pidió **explícitamente que la IA escribiera el código** del fix (excepción puntual a la regla de "la IA no escribe implementación"), en vez de solo guiar.
- **Propuso la IA:** una función `_extraer_medicion` en la capa de presentación que valida y convierte el JSON crudo a valores tipados **antes** de llamar al caso de uso (esto es la comprobación práctica de RA6: el dominio nunca ve un dict crudo); una excepción propia `ErrorDeValidacion` (vive en `presentation/`, no en el dominio); y un cuerpo de error uniforme `{error, mensaje, detalle}` para los 4 casos de RF6 (especie no encontrada, parámetro ausente, valor no numérico, valor fuera del rango físico).
- **Se aceptó / cambió:** se aceptó tal cual, dada la urgencia. **Pendiente para el equipo:** entender esta función a fondo antes de la sustentación — es la pieza más probable de recibir una pregunta de mutación tipo "¿qué pasa si el front envía un campo vacío?".

### 3. Conexión front-back — escrita directamente por la IA
- **Se pidió:** conectar `frontend/js/app.js` con los endpoints reales (`GET /especies`, `POST /diagnostico`) y probar la app completa corriendo ambos servidores.
- **Propuso la IA:** reemplazó los `fetch` pendientes (`TODO`) por las llamadas reales; ajustó `mostrarDiagnostico`/`mostrarRecomendaciones` al contrato real del backend (el front había sido escrito contra un contrato inventado: `diagnostico.humedad` plano, `diagnostico.indice_vitalidad`, en vez de `diagnostico.parametros[]` y `diagnostico.estado`); detectó y corrigió que el campo/id `indice-vitalidad` coincidía literalmente con la terminología de la nota trampa ASW-4.2 que el equipo ya había decidido ignorar en la sesión 2026-09-14 — se renombró a `estado-global`; también corrigió fences de markdown (` ```html ` / ` ``` `) que habían quedado pegados en `index.html` y rompían la página. Verificó todo con un navegador headless (Playwright + Chromium del sistema): carga de especies, diagnóstico exitoso y el caso de error de RF6 (temperatura fuera de rango) mostrados correctamente en pantalla.
- **Se aceptó / cambió:** se aceptó tal cual, dada la urgencia. **Nota de honestidad importante:** ni el fix de RF6 ni el cableado del front fueron escritos por el equipo — fueron pedidos explícitamente a la IA por falta de tiempo. Si en la sustentación preguntan por estas líneas, hay que poder explicar el *por qué* (ver punto 2), no solo que "la IA lo hizo".

### 4. Rediseño visual del front (CSS) — escrito directamente por la IA
- **Se pidió:** un front "menos sonso", minimalista, con pequeñas animaciones al aparecer el resultado.
- **Propuso la IA:** rediseño de `frontend/css/styles.css` (paleta reducida con variables CSS, tipografía del sistema, más espacio en blanco) y una clase de color dinámica en `estado-global` según SALUDABLE/EN_RIESGO/CRITICO (cambio menor en `app.js`); animaciones de aparición (`@keyframes aparecer`/`aparecerEscala`) en el resultado, las tarjetas de parámetros y el error, respetando `prefers-reduced-motion`. No se tocó el HTML estructural ni la lógica de negocio.
- **Se aceptó / cambió:** se aceptó tal cual. Esto es diseño visual, no afecta RA1-RA8 ni la lógica evaluada, pero igual lo escribió la IA — mismo criterio de honestidad que los puntos 2 y 3.

### 5. Panel de estado de la API — escrito directamente por la IA
- **Se pidió:** una página que muestre visiblemente que se le están haciendo solicitudes a la API.
- **Propuso la IA:** advirtió primero que servir esa página desde Flask como HTML violaría **RA1** (descalificación parcial: cero en "Cumplimiento de restricciones", 25% de la nota, sin importar el resto). En vez de eso: un endpoint nuevo `GET /estado` en `presentation/app.py` (JSON con `activo`, `especies_cargadas` y las últimas 20 solicitudes vía un `@app.after_request`, guardadas en memoria — no es persistencia de mediciones, es solo para este panel y se pierde al reiniciar el servidor), y una **segunda página estática independiente** `frontend/estado.html` + `frontend/js/estado.js` que hace polling cada 2s a ese endpoint y muestra la lista en vivo. Se probó con dos pestañas abiertas a la vez (una haciendo diagnósticos, otra viendo el panel) y se confirmó que las solicitudes (`POST /diagnostico`, el `OPTIONS` del preflight de CORS, `GET /especies`) aparecen en tiempo real.
- **Se aceptó / cambió:** se aceptó tal cual. **Para la sustentación:** esta es una pieza extra que no pide el enunciado — si preguntan, la respuesta es "es solo un panel de monitoreo para nosotros, consume `/estado` igual que el front consume `/especies` y `/diagnostico`; no toca dominio ni aplicación, y no cambia nada de lo evaluado".

### 6. Push a `back_Julian` y merge a `main` — conflicto con el rediseño del equipo de front
- **Se pidió:** subir todo lo de esta sesión y hacer merge a `main`.
- **Propuso la IA:** al ir a hacer el merge, detectó que `origin/main` ya tenía 3 commits nuevos del equipo de front (`Update index.html/styles.css/app.js`) que reemplazaban el `<form>` por un layout tipo "dashboard" sin forms — el cambio que el profesor pidió. Ese rediseño **otra vez** traía el campo/id `indice_vitalidad` / "ÍNDICE DE VITALIDAD" (la terminología de la trampa ASW-4.2), y dejaba `ENDPOINTS.especies`/`ENDPOINTS.diagnostico` vacíos (sin conectar realmente a la API). La IA resolvió el conflicto de merge quedándose con el rediseño del equipo de front (respeta el pedido del profesor), y encima: renombró `indice-vitalidad` → `estado-global` / "ESTADO DE LA PLANTA", cableó los dos endpoints reales, adaptó el mapeo de `mostrarDiagnostico` al contrato real del backend (`data.parametros[]` / `data.estado`, ya que el fetch de `/especies` devuelve objetos `{nombre, rangos}` y no strings), agregó las animaciones de aparición y el color por estado sobre las clases nuevas, y adaptó `estado.html`/`estado.css` (que dependían de clases de mi CSS anterior) a la paleta nueva. Se verificó de nuevo con Playwright antes de comitear el merge.
- **Se aceptó / cambió:** se aceptó tal cual. **Nota para el equipo de front:** revisen de dónde está saliendo el término "índice de vitalidad" en lo que generan — ya es la segunda vez que aparece esa terminología exacta de la nota trampa del enunciado en código que ustedes escribieron; vale la pena que como equipo hablen de esto abiertamente en la bitácora en vez de que lo siga arreglando la IA en cada merge.

### 7. JSON en vez de CSV: se había perdido el formato de tabla de referencia del enunciado
- **Se pidió:** revisar si el uso de `especies.json` cumplía la sección 2 del enunciado ("Tabla de referencia por especie: CSV o base de datos"), y de dónde salieron los valores de las 5 especies.
- **Propuso la IA:** confirmó que el enunciado solo nombra CSV o base de datos, nunca JSON — no es una de las dos restricciones que descalifican (RA1/RA4), pero es una desviación de la letra del enunciado. Sobre la fuente: los valores de las 5 especies ya eran, letra por letra, los del Anexo B del enunciado (no vienen de investigación botánica propia) — hay que citarlo así en el documento, honestamente. Reescribió `infrastructure/especie_lookup_json.py` → `especie_lookup_csv.py` (usa el módulo `csv` de la librería estándar en vez de `json`) y `infrastructure/data/especies.json` → `especies.csv` con las columnas exactas del Anexo B (`especie,humedad_min,humedad_max,luz_min,luz_max,temp_min,temp_max`). El único cambio fuera de `infrastructure/` fue una línea en `presentation/app.py` (la instanciación de la clase) — cero cambios en `domain/`/`application/`, que es exactamente lo que RA5 promete.
- **Se aceptó / cambió:** se aceptó tal cual. Los 31 tests siguen pasando (se migró `test_especie_lookup_json.py` → `test_especie_lookup_csv.py` con fixtures CSV en vez de JSON). **Para la sustentación:** si preguntan "¿por qué CSV y no base de datos?", la respuesta es que el enunciado deja esa decisión para cuando el equipo cierre el esquema en dbdiagram.io (pendiente abierto de la sesión 2026-09-14), y que migrar a base de datos después implica una clase nueva en `infrastructure/` y cero cambios en el dominio — lo mismo que se acaba de demostrar migrando de JSON a CSV.

---

## Sesión 2026-09-30

### 1. Ampliación de alcance: gestión de usuarios y autenticación (indicación verbal del profesor)
- **Se pidió:** hablar de gestión de usuarios/autenticación para el backend, aclarando que el profesor indicó en clase (no reflejado aún en el enunciado escrito) que el equipo debería tener al menos la gestión de usuarios implementada — ampliando lo que la sección 2 del enunciado marca como "No entra" en este corte. También se pidió explicar autenticación con tokens, funciones hash y qué es un "secreto", y qué son los WebSockets: temas de una clase a la que Julián no pudo asistir.
- **Propuso la IA:** señaló explícitamente la contradicción con la sección 2 del enunciado (*"Autenticación y gestión de usuarios"* está en la columna *"No entra"*) antes de avanzar, para dejarlo documentado de cara a la sustentación. Aclarado que es indicación verbal del profesor, explicó sin código: el flujo de autenticación con JWT (login → verificación de contraseña → token firmado → cliente lo reenvía → servidor verifica firma), la diferencia entre hash lento+salteado para contraseñas (bcrypt/argon2) vs. HMAC rápido para firmar tokens, qué es el `SECRET_KEY` y por qué vive solo en `.env` del servidor, y qué son los WebSockets (conexión persistente bidireccional vs. petición-respuesta de HTTP), con dos usos concretos para este proyecto: reemplazar el polling de 2s del panel `/estado` por push en tiempo real, y a futuro empujar mediciones del ESP32/MQTT al front sin polling. Remarcó que la autenticación es un *concern* transversal (`presentation/`+`infrastructure/`), no lógica del dominio de diagnóstico — el dominio (`Rango`, `EvaluadorDiagnostico`, `Diagnostico`) no debe enterarse de que existen usuarios.
- **Se aceptó / cambió:** se confirma que la gestión de usuarios se va a implementar de verdad en este corte, por pedido explícito (verbal) del profesor, pese a la letra del enunciado. **Pendiente para el equipo:** tener lista la justificación de por qué se implementó algo listado como "No entra", para la sustentación.

### 2. Diseño de la base de datos para usuarios, roles, autenticación y plantas compartidas
- **Se pidió:** diseñar juntos el esquema de base de datos para el backend de usuarios.
- **Propuso la IA:** antes de proponer tablas, preguntó dos decisiones que cambian el esquema (motor de BD, y si el flujo de tokens es solo access token o access+refresh); dio ventajas/desventajas de SQLite vs. Postgres vs. MySQL para este proyecto específico (fricción de setup para el equipo/profesor, concurrencia, qué tan "producción" se ve, facilidad de migrar de motor después dado el precedente de la migración JSON→CSV). Con Postgres y access+refresh token elegidos, propuso: `usuarios` (id, nombre, email único, password_hash, creado_en, activo) y `refresh_tokens` (con `token_hash` — no el token crudo — e índice único, y campo `revocado` para poder invalidar sesiones), usando `timestamptz`/`bigserial` como detalles "de producción" en Postgres. Al pedir gestión de roles y confirmar que las plantas pueden tener varios dueños a la vez, rediseñó a dos relaciones muchos-a-muchos: `roles`+`usuario_roles` (permite agregar roles nuevos sin tocar esquema ni código) y `plantas`+`usuario_planta` (se le quitó `usuario_id` a `plantas`; ambas tablas intermedias con PK compuesta). Preguntó si los co-dueños de una planta tienen los mismos permisos o si hace falta un rol dentro de la relación `usuario_planta`.
- **Se aceptó / cambió:** `nombre` obligatorio en `usuarios`; roles con tabla + asignación (no columna fija); plantas con dueños múltiples vía tabla intermedia; todos los co-dueños de una planta tienen los mismos permisos (no se agrega columna de rol en `usuario_planta`). Motor de base de datos: **PostgreSQL**, justificado explícitamente por buscar algo "lo más parecido a producción posible". Diseño de tablas cerrado en esta sesión — queda pendiente implementarlo (ver pendientes abiertos).

---

## Sesión 2026-10-29 — Fase 2 (arquitectura hexagonal)

> Reparto de esta sesión: **Julián definió la arquitectura y las decisiones de diseño; la IA escribió gran parte del código** (backend, migraciones, simulador, conexión del front y tests) y explicó cada pieza. Todo el código se probó contra PostgreSQL real y en el navegador.

### 1. Lectura del enunciado de la Fase 2 y revisión de trampas
- **Se pidió:** revisar el nuevo enunciado (`Enunciado_Matera_Fase2_Hexagonal.pdf`) y los mockups, buscando trampas como la nota ASW-4.2 de la fase 1.
- **Propuso la IA:** analizó el PDF por dentro (colores, tamaños de letra, texto oculto, anotaciones, metadatos): no encontró trampas. Señaló diferencias entre el enunciado y el diseño del equipo (plantas con varios dueños vs. "cada planta pertenece a un usuario").
- **Se aceptó / cambió:** el profesor aclaró que el enunciado es una **guía, no un paso a paso** (lo generó con IA). Se mantienen las decisiones propias del equipo cuando están justificadas (ej. varios dueños por planta).

### 2. Merge con el nuevo front del equipo
- **Se pidió:** traer los últimos cambios del front (`origin/main`).
- **Propuso la IA:** merge fast-forward sin conflictos; detectó que las pantallas nuevas no cargaban su JS/CSS (rutas sin `js/` ni `css/`), que el login devolvía un token simulado y que había un token de dispositivo escrito a mano.
- **Se aceptó / cambió:** se corrigió más adelante, al conectar el front (punto 7).

### 3. Base de datos PostgreSQL
- **Se pidió (Julián):** montar la BD en PostgreSQL con el diseño del 2026-09-30, y luego mejorar su estructura porque "era muy mala".
- **Propuso la IA:** Postgres en Docker (`docker-compose.yml`) para que todo el equipo lo levante igual; migraciones con Alembic. Como mejoras: tabla de referencia normalizada (`parametros`, `especies`, `rangos_referencia`), CHECK de estado/origen/rangos físicos en `lecturas`, correo en minúsculas, índices en todas las llaves foráneas, `IDENTITY`, revocación con fecha y protección contra lecturas duplicadas del ESP32.
- **Se aceptó / cambió:** Julián aceptó el diseño; se mantuvieron sus decisiones de roles en tabla aparte y plantas con varios dueños. La tabla de referencia queda en CSV **y** en BD, elegible por configuración (`TABLA_REFERENCIA`, R4).

### 4. Autenticación con JWT
- **Se pidió (Julián):** revisar si el front tenía algún secreto para autenticar y hacer la autenticación de usuarios.
- **Propuso la IA:** el front no debe tener ningún secreto (el `JWT_SECRET` vive solo en el `.env` del servidor). Implementó registro/login detrás de puertos del dominio (`RepositorioUsuarios`, `HasherContrasenas`, `EmisorTokens`) con bcrypt y PyJWT como adaptadores, y el decorador `@requiere_usuario` que verifica el token y entrega solo el `usuario_id` al caso de uso.
- **Se aceptó / cambió:** aceptado. Se dejó fuera el refresh token por tiempo (access token de 60 min).

### 5. Plantas, regla de propiedad, historial y vinculación
- **Se pidió (Julián):** completar el backend, explicándolo después.
- **Propuso la IA:** regla "un usuario solo ve sus plantas" en el dominio (`Planta.verificar_acceso`, 403 si es ajena), historial de lecturas (R5), puertos de entrada para todos los casos de uso y un único caso de uso `RegistrarLectura` para el formulario y para el dispositivo. Tokens de dispositivo **opacos** (hash en BD, revocables) en vez de JWT, porque un ESP32 no puede renovar tokens.
- **Se aceptó / cambió:** aceptado.

### 6. Prueba de cambio: adaptador de dispositivos y simulador del ESP32
- **Propuso la IA:** separar los commits para que el que agrega `POST /api/dispositivos/{codigo}/lecturas` y `simulador_esp32.py` **no toque `domain/` ni `application/`** (commit `a91628b`, verificado). El simulador manda lecturas normales, fuera de rango e inválidas.
- **Se aceptó / cambió:** aceptado; es el commit que debe enlazar el documento.

### 7. Materas con sticker NFC (idea de Julián) y conexión del front
- **Se pidió (Julián):** que cada matera tenga un dueño usando **stickers NFC**: al acercar el teléfono, la planta se agrega sola a la cuenta. Como todavía no hay stickers, simularlo con el simulador de los ESP.
- **Propuso la IA:** el patrón de "clave de reclamo": la matera sale de fábrica sin dueño (`flask fabricar-matera`), con su token en el firmware y una URL `reclamar.html?codigo=…&clave=…` en el sticker; mientras nadie la reclame, el dominio rechaza sus lecturas (`MateraSinDueno`); el reclamo es atómico (un solo dueño). El simulador con `--tocar-nfc` abre esa URL como lo haría el teléfono. Conectó todo el front a la API real.
- **Se aceptó / cambió:** Julián pidió que la planta se agregue directamente, sin pasos extra: la especie sale del kit de fábrica y el nombre por defecto es "Matera <código>". Probado en el navegador: registro → vuelta al sticker → planta agregada → lecturas en vivo → planta ajena bloqueada.

### 8. Compartir plantas entre usuarios y endpoint para ver los ESP
- **Se pidió (Julián):** comprobar que un usuario pueda compartir una planta (decisión de diseño del 2026-09-30: plantas con varios dueños) y probarlo en el navegador con los ESP simulados; también si había un endpoint para ver los ESP.
- **Propuso la IA:** señaló que la BD y el dominio ya soportaban varios dueños, pero **no existía forma de compartir** (no estaba implementado). Agregó el caso de uso `CompartirPlanta` (solo un dueño puede compartir; el invitado debe estar registrado; compartir dos veces no duplica), `POST /api/plantas/{id}/duenos`, la sección "Compartir" en el detalle de la planta y `GET /api/dispositivos`.
- **Se aceptó / cambió:** aceptado. Probado en el navegador con una matera simulada transmitiendo: Ana comparte con Brian → Brian la ve en vivo y puede registrar lecturas; un tercero sigue recibiendo 403; correo no registrado da error claro.

---

## Pendientes abiertos (para no perderlos)
- [x] ~~Decidir si se reutiliza `arquitectura_de_software/` o se abre una carpeta/repo nuevo~~ → resuelto: repo nuevo en `diagnostico-plantas/`.
- [x] ~~Definir y justificar la regla de agregación de RF3 (qué combinación de BAJO/ALTO da CRITICO vs EN_RIESGO)~~ → resuelto en sesión 2026-09-16: desviación % relativa al límite, umbral leve 10%, umbral severo 50%.
- [x] ~~Implementar `EvaluadorDiagnostico.evaluar()` en código~~ → resuelto: implementado por el equipo, con tests verdes.
- [x] ~~RF6 (parámetro ausente / no numérico) devolvía 500 en vez de 400~~ → resuelto sesión 2026-09-18, ver punto 2 arriba.
- [x] ~~Decidir motor concreto de BD (Postgres/MySQL/otro)~~ → resuelto sesión 2026-09-30: **PostgreSQL**, decidido para el backend de usuarios/auth por buscar semejanza con producción.
- [x] ~~Decidir si `especies` se queda en CSV o migra a Postgres~~ → resuelto 2026-10-29: ambas, elegibles por `TABLA_REFERENCIA` (R4); esquema normalizado.
- [ ] Decidir si se modela histórico de mediciones en el diagrama especulativo de evolución.
- [x] ~~El equipo de front iba a reemplazar el `<form>` por otro patrón de UI~~ → resuelto: ya llegó a `main` y se fusionó (sesión 2026-09-18, punto 6). Pendiente real: que el equipo de front revise por qué les sigue saliendo "índice de vitalidad" en el código que generan.
- [ ] Justificar en el documento (6.b.6) la decisión de rutas propias (`/diagnostico`, `/especies`) en vez de las del Anexo A (`/api/v1/...`), y la forma del cuerpo de error elegida.
- [x] ~~Implementar el esquema de la sesión 2026-09-30 vía migraciones~~ → resuelto 2026-10-29 con Alembic.
- [x] ~~Elegir librería de JWT~~ → PyJWT, access token de 60 min (`JWT_MINUTOS_VALIDEZ`). Refresh token: pendiente, fuera de esta entrega.
- [x] ~~Driver, migraciones, `DATABASE_URL` y secreto~~ → `psycopg`, Alembic, `JWT_SECRET` en `.env`.
- [ ] Preparar para la sustentación la justificación de implementar gestión de usuarios/autenticación pese a estar listada como "No entra" en la sección 2 del enunciado (fue pedido verbal del profesor, sesión 2026-09-30).
- [ ] Escribir el documento de arquitectura de la Fase 2 (lo escribe el equipo): diagrama hexagonal con nombres reales, tabla de puertos/adaptadores, dónde se emite y se verifica el JWT, 3 principios SOLID, enlace al commit `a91628b` y análisis MQTT.
- [ ] Probar el flujo NFC desde un teléfono real en la red local (`--host 0.0.0.0`, `FRONT_URL` y `CORS_ORIGIN` con la IP del PC) y grabar la URL en un sticker real.
- [ ] Conectar el ESP32 físico del equipo (falta saber qué sensores tiene para escribir el firmware).
