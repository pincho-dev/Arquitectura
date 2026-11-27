// Emblemas de las divisiones de la liga, dibujados en SVG (sin imágenes).
// Hexágono metálico con una planta que crece de división en división; las
// altas suman hojas a los lados (laureles) y gemas arriba.
// Uso: Emblemas.svg('hoja', 120)  ->  texto <svg> listo para innerHTML.
const Emblemas = (() => {
  const HOJA_LAUREL = 'M0 0 C5 -7 5 -17 0 -24 C-5 -17 -5 -7 0 0Z';
  const POSICIONES_LAUREL = [[20, 178, -35], [10, 156, -20], [4, 132, -8], [4, 108, 4], [8, 84, 16], [16, 62, 28]];
  const HOJA = (largo, ancho) => `M0 0 C${largo * 0.3} -${ancho} ${largo * 0.7} -${ancho} ${largo} 0 C${largo * 0.7} ${ancho} ${largo * 0.3} ${ancho} 0 0Z`;
  const GEMAS = {
    1: ['M100 -2 L111 12 L100 26 L89 12 Z'],
    3: ['M78 6 L86 16 L78 26 L70 16 Z', 'M100 -4 L111 10 L100 24 L89 10 Z', 'M122 6 L130 16 L122 26 L114 16 Z'],
  };

  const ESTILOS = {
    semilla: { colores: ['#F0B47A', '#7A4320'], borde: '#4A2812', fondo: '#24160D', laureles: 0, gemas: 0 },
    brote: { colores: ['#F4F7FA', '#7D8A98'], borde: '#3E4954', fondo: '#161D26', laureles: 0, gemas: 0 },
    hoja: { colores: ['#FFE38A', '#B07A10'], borde: '#5E400A', fondo: '#221A07', laureles: 2, gemas: 0 },
    flor: { colores: ['#8FF2C6', '#0E7A52'], borde: '#06422C', fondo: '#08201A', laureles: 4, gemas: 1, gema: '#FFE38A' },
    arbol: { colores: ['#E6F8FF', '#8FC2F7', '#3F6FD6'], borde: '#1F3E80', fondo: '#0A1430', laureles: 6, gemas: 3, gema: '#E6F8FF' },
  };

  const PLANTAS = {
    semilla: (m, e) => `
      <path d="M62 134 Q100 126 138 134" stroke="#C98A55" stroke-width="4" fill="none" stroke-linecap="round"/>
      <ellipse cx="100" cy="104" rx="19" ry="25" fill="${m}" transform="rotate(-18 100 104)"/>
      <path d="M97 84 Q106 104 98 124" stroke="${e.fondo}" stroke-width="3" fill="none" stroke-linecap="round"/>`,
    brote: (m) => `
      <path d="M62 136 Q100 128 138 136" stroke="#9AA6B3" stroke-width="4" fill="none" stroke-linecap="round"/>
      <path d="M100 132 L100 88" stroke="${m}" stroke-width="5" stroke-linecap="round"/>
      <path d="M100 104 C88 100 74 90 72 76 C88 76 98 88 100 104 Z" fill="${m}"/>
      <path d="M100 94 C112 90 126 80 128 66 C112 66 102 78 100 94 Z" fill="${m}"/>`,
    hoja: (m) => `
      <path d="M100 140 Q97 110 100 68" stroke="${m}" stroke-width="5" fill="none" stroke-linecap="round"/>
      <g fill="${m}">
        <path d="${HOJA(34, 9)}" transform="translate(99 122) rotate(-150)"/>
        <path d="${HOJA(34, 9)}" transform="translate(99 122) rotate(-30)"/>
        <path d="${HOJA(28, 8)}" transform="translate(99 98) rotate(-145)"/>
        <path d="${HOJA(28, 8)}" transform="translate(99 98) rotate(-35)"/>
        <path d="${HOJA(24, 7)}" transform="translate(100 74) rotate(-90)"/>
      </g>`,
    flor: (m) => `
      <path d="M100 146 Q98 118 100 92" stroke="${m}" stroke-width="5" fill="none" stroke-linecap="round"/>
      <g fill="${m}">
        <path d="${HOJA(34, 9)}" transform="translate(99 128) rotate(-150)"/>
        <path d="${HOJA(34, 9)}" transform="translate(99 128) rotate(-30)"/>
        ${[0, 72, 144, 216, 288].map(g => `<ellipse cx="100" cy="66" rx="9" ry="15" transform="rotate(${g} 100 82)"/>`).join('')}
      </g>
      <circle cx="100" cy="82" r="8" fill="#FFE38A"/>`,
    arbol: (m) => `
      <path d="M93 150 L97 112 L103 112 L107 150 Z" fill="${m}"/>
      <path d="M80 150 Q100 142 120 150" stroke="${m}" stroke-width="4" fill="none" stroke-linecap="round"/>
      <g fill="${m}">
        <circle cx="82" cy="100" r="20"/><circle cx="118" cy="100" r="20"/><circle cx="100" cy="78" r="25"/>
      </g>`,
  };

  const NOMBRES = { semilla: 'Semilla', brote: 'Brote', hoja: 'Hoja', flor: 'Flor', arbol: 'Árbol' };
  let contador = 0;

  function svg(clave, tamano = 120, { decorativo = false } = {}) {
    const e = ESTILOS[clave] || ESTILOS.semilla;
    // Cada emblema necesita su propio id de degradado: puede haber varios en la página.
    const id = `emblema-metal-${++contador}`;
    const m = `url(#${id})`;
    const paradas = e.colores.map((c, i) => `<stop offset="${i / (e.colores.length - 1)}" stop-color="${c}"/>`).join('');
    const laureles = POSICIONES_LAUREL.slice(0, e.laureles)
      .map(([x, y, r]) => `<path d="${HOJA_LAUREL}" transform="translate(${x} ${y}) rotate(${r})"/>`).join('');
    const gemas = (GEMAS[e.gemas] || [])
      .map(d => `<path d="${d}" fill="${e.gema}" stroke="${e.borde}" stroke-width="2.5" stroke-linejoin="round"/>`).join('');
    const accesible = decorativo ? 'aria-hidden="true"' : `role="img" aria-label="Emblema de la división ${NOMBRES[clave] || ''}"`;

    return `<svg viewBox="-10 -6 220 210" width="${tamano}" height="${Math.round(tamano * 210 / 220)}" ${accesible} class="emblema">
      <defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">${paradas}</linearGradient></defs>
      <g fill="${m}">${laureles}<g transform="translate(200 0) scale(-1 1)">${laureles}</g></g>
      <path d="M100 14 L178 58 L178 146 L100 190 L22 146 L22 58 Z" fill="${m}" stroke="${e.borde}" stroke-width="3" stroke-linejoin="round"/>
      <path d="M100 30 L164 66 L164 138 L100 174 L36 138 L36 66 Z" fill="${e.fondo}"/>
      ${gemas}
      ${PLANTAS[clave] ? PLANTAS[clave](m, e) : ''}
    </svg>`;
  }

  return { svg };
})();
