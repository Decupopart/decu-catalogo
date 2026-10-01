/* Las obras no migradas conservan la galería anterior. */
window.DecuImagenes = (() => {
  let manifiesto = { productos: {} };
  const escapar = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  function url(ruta) { return manifiesto.baseUrl ? `${manifiesto.baseUrl}/${ruta}` : ruta; }
  function galeria(p) {
    const vistas = manifiesto.productos?.[p.codigo];
    if (!Array.isArray(vistas) || vistas.length !== 4) return null;
    if (!vistas.every(v => v.variantes?.[160]?.ruta && v.variantes?.[640]?.ruta && v.variantes?.[1254]?.ruta)) return null;
    return vistas.map(v => ({
      imagen: url(v.variantes[1254].ruta), miniatura: url(v.variantes[160].ruta),
      tarjeta: url(v.variantes[640].ruta), etiqueta: v.etiqueta,
      alt: `${v.etiqueta} — ${p.nombre}`, modo: "completa",
      srcset: [v.variantes[640], v.variantes[1254]].map(x => `${url(x.ruta)} ${x.ancho}w`).join(", ")
    }));
  }
  return {
    async cargar() {
      try {
        const respuesta = await fetch("galerias.json", {cache:"no-cache"});
        if (respuesta.ok) {
          const datos = await respuesta.json();
          if (datos.version === 1 && datos.productos && (!datos.baseUrl || /^https:\/\//.test(datos.baseUrl))) manifiesto = datos;
        }
      } catch (error) { console.warn("Se conserva la galería anterior", error); }
    },
    galeria,
    principal: p => galeria(p)?.[0],
    atributos: (item, sizes = "(max-width: 600px) 90vw, 520px") => item?.srcset ? `srcset="${escapar(item.srcset)}" sizes="${escapar(sizes)}"` : ""
  };
})();
