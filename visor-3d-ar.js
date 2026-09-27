(function () {
  "use strict";

  let modelos = {};
  let cargaModelos = null;

  function escapar(valor) {
    return String(valor ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function cargar() {
    if (cargaModelos) return cargaModelos;
    cargaModelos = fetch("modelos-3d/modelos.json", { cache: "no-cache" })
      .then((respuesta) => (respuesta.ok ? respuesta.json() : {}))
      .then((datos) => {
        modelos = datos && typeof datos === "object" ? datos : {};
        return modelos;
      })
      .catch(() => {
        modelos = {};
        return modelos;
      });
    return cargaModelos;
  }

  function obtener(codigo) {
    return modelos[String(codigo)] || null;
  }

  function html(producto) {
    const modelo = obtener(producto.codigo);
    if (!modelo) return "";
    const codigo = escapar(producto.codigo);
    const nombre = escapar(producto.nombre);
    return `
      <section class="ficha-seccion decu-visor" data-decu-visor="${codigo}">
        <div class="decu-visor-cabecera">
          <div>
            <span class="decu-visor-eyebrow">VISTA INTERACTIVA</span>
            <h3>Conocé el cuadro desde todos los ángulos</h3>
          </div>
        </div>
        <model-viewer
          id="decu-modelo-${codigo}"
          src="${escapar(modelo.modelo)}"
          poster="${escapar(modelo.poster)}"
          alt="Modelo 3D del cuadro ${nombre}"
          camera-controls
          touch-action="pan-y"
          interaction-prompt="auto"
          auto-rotate
          auto-rotate-delay="1800"
          rotation-per-second="18deg"
          shadow-intensity="0.75"
          shadow-softness="0.85"
          exposure="1.05"
          ar
          ar-modes="webxr scene-viewer quick-look"
          ar-placement="wall"
          ar-scale="fixed"
          xr-environment>
          <button class="decu-ar-nativo" slot="ar-button" type="button">Ver en mi ambiente</button>
          <div class="decu-carga" slot="poster" style="background-image:url('${escapar(modelo.poster)}')">
            <button type="button" onclick="this.closest('model-viewer').dismissPoster()">Cargar vista 3D</button>
          </div>
        </model-viewer>
        <div class="decu-visor-acciones">
          <button class="decu-boton-3d" type="button" onclick="DecuVisor3D.enfocar('${codigo}')">↻ Girar y explorar</button>
          <button class="decu-boton-ar" type="button" onclick="DecuVisor3D.verEnAmbiente('${codigo}')">▣ Ver en mi ambiente</button>
        </div>
        <p class="decu-visor-ayuda">En celular utiliza la cámara. Desde una computadora muestra un QR para continuar en el teléfono.</p>
      </section>`;
  }

  function esMovil() {
    return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || matchMedia("(pointer:coarse)").matches;
  }

  function urlProducto(codigo) {
    const url = new URL(location.href);
    url.searchParams.set("producto", codigo);
    url.searchParams.set("ar", "1");
    url.hash = "";
    return url.href;
  }

  function asegurarModalQr() {
    let modal = document.getElementById("decu-qr-modal");
    if (modal) return modal;
    modal = document.createElement("div");
    modal.id = "decu-qr-modal";
    modal.className = "decu-qr-modal";
    modal.hidden = true;
    modal.innerHTML = `
      <div class="decu-qr-fondo" data-cerrar-qr></div>
      <section class="decu-qr-panel" role="dialog" aria-modal="true" aria-labelledby="decu-qr-titulo">
        <button class="decu-qr-cerrar" type="button" data-cerrar-qr aria-label="Cerrar">×</button>
        <span class="decu-visor-eyebrow">REALIDAD AUMENTADA</span>
        <h3 id="decu-qr-titulo">Mirá el cuadro en tu pared</h3>
        <p>Escaneá este código con la cámara de tu teléfono.</p>
        <img width="220" height="220" alt="Código QR para abrir el cuadro en el teléfono">
        <small>Después tocá “Ver en mi ambiente” y apuntá la cámara hacia una pared.</small>
      </section>`;
    modal.addEventListener("click", (evento) => {
      if (evento.target.closest("[data-cerrar-qr]")) cerrarQr();
    });
    document.body.appendChild(modal);
    return modal;
  }

  async function abrirQr(codigo) {
    const modal = asegurarModalQr();
    const imagenQr = modal.querySelector("img");
    const modelo = obtener(codigo);
    modal.hidden = false;
    document.body.classList.add("decu-qr-abierto");
    imagenQr.src = modelo?.qr || "";
    modal.querySelector(".decu-qr-cerrar").focus();
  }

  function cerrarQr() {
    const modal = document.getElementById("decu-qr-modal");
    if (modal) modal.hidden = true;
    document.body.classList.remove("decu-qr-abierto");
  }

  async function verEnAmbiente(codigo) {
    const visor = document.getElementById(`decu-modelo-${codigo}`);
    if (esMovil() && visor?.activateAR) {
      try {
        await visor.activateAR();
        return;
      } catch (_) {
        // Si el dispositivo no ofrece AR nativa, dejamos un enlace claro.
      }
    }
    await abrirQr(codigo);
  }

  function enfocar(codigo) {
    const visor = document.getElementById(`decu-modelo-${codigo}`);
    if (!visor) return;
    visor.dismissPoster?.();
    visor.scrollIntoView({ behavior: "smooth", block: "center" });
    visor.focus({ preventScroll: true });
  }

  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && !document.getElementById("decu-qr-modal")?.hidden) cerrarQr();
  });

  // Se carga en paralelo con productos.json. Cuando el usuario abre una ficha,
  // la función html() decide si ese código ya tiene un GLB generado.
  cargar();
  window.DecuVisor3D = { cargar, obtener, html, verEnAmbiente, enfocar, cerrarQr };
})();
