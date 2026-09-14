# Bitácora de uso de IA — Sistema de diagnóstico del estado de plantas

> Este archivo es el registro de trabajo **crudo**, sesión por sesión, de todo lo que se le ha pedido a la IA (Claude) durante el desarrollo de este proyecto. No es el entregable final del punto 6.e del enunciado (ese tiene máximo 1 página) — es la materia prima de la que ese entregable se va a redactar al cierre del proyecto, condensando y quedándonos solo con lo relevante.

## Reglas de trabajo acordadas con la IA

- La IA actúa como **profesor/guía de arquitectura**, no como programador del equipo.
- La IA **no escribe código de implementación** (backend, front, tests) ni redacta el texto final del documento de arquitectura salvo que se le pida explícitamente algo puntual (como este mismo archivo).
- La IA **sugiere, explica y ayuda a destrabar** cuando el equipo está atascado en una decisión o un concepto.
- El código, las decisiones de diseño y el documento final los escribe el equipo, a partir de haber entendido las sugerencias — no copiándolas.

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

## Pendientes abiertos (para no perderlos)
- [x] ~~Decidir si se reutiliza `arquitectura_de_software/` o se abre una carpeta/repo nuevo~~ → resuelto: repo nuevo en `diagnostico-plantas/`.
- [ ] Definir y justificar la regla de agregación de RF3 (qué combinación de BAJO/ALTO da CRITICO vs EN_RIESGO).
- [ ] Decidir esquema de BD final en dbdiagram.io (tabla plana vs normalizada) para `especies`/`rangos_referencia`, y motor concreto (Postgres/MySQL/otro) para completar `requirements.txt` y `DATABASE_URL`.
- [ ] Decidir si se modela histórico de mediciones en el diagrama especulativo de evolución.
- [ ] Diseñar el modelo de dominio (`EvaluadorDiagnostico` y sus objetos) — código lo escribe el equipo.
