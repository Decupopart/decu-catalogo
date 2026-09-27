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

  function galeria(producto) {
    const modelo = obtener(producto.codigo);
    if (!modelo) return "";
    const codigo = escapar(producto.codigo);
    const nombre = escapar(producto.nombre);
    return `
      <button class="decu-activar-360" type="button" aria-pressed="false"
              aria-label="Abrir vista 360 grados de ${nombre}"
              onclick="DecuVisor3D.activar360('${codigo}')">
        <span>360°</span>
      </button>
      <div class="decu-galeria-3d" data-decu-visor="${codigo}" aria-hidden="true">
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
          <div class="decu-carga" slot="poster" style="background-image:url('${escapar(modelo.poster)}')"></div>
        </model-viewer>
        <button class="decu-cerrar-360" type="button" aria-label="Cerrar vista 360 grados"
                onclick="DecuVisor3D.cerrar360('${codigo}')">×</button>
        <span class="decu-ayuda-giro">Arrastrá para girar</span>
      </div>`;
  }

  function accion(producto) {
    const modelo = obtener(producto.codigo);
    if (!modelo) return "";
    const codigo = escapar(producto.codigo);
    return `
      <div class="decu-accion-pared">
        <button class="decu-boton-ar" type="button" onclick="DecuVisor3D.verEnAmbiente('${codigo}')">
          <span aria-hidden="true">▣</span> Ver en mi pared
        </button>
        <p>En celular abre la cámara. Desde una computadora muestra un QR.</p>
      </div>`;
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
        <small>Después tocá “Ver en mi pared” y apuntá la cámara hacia una pared.</small>
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
        visor.dismissPoster?.();
        await visor.activateAR();
        return;
      } catch (_) {
        // Si el dispositivo no ofrece AR nativa, dejamos un enlace claro.
      }
    }
    await abrirQr(codigo);
  }

  function activar360(codigo) {
    const visor = document.getElementById(`decu-modelo-${codigo}`);
    if (!visor) return;
    const marco = visor.closest("[data-ficha-imagen-principal]");
    const panel = visor.closest("[data-decu-visor]");
    if (!marco || !panel) return;
    if (!marco.dataset.claseAntes3d) marco.dataset.claseAntes3d = marco.className;
    marco.className = "ficha-imagen-recorte completa decu-3d-activo";
    marco.setAttribute("data-ficha-imagen-principal", "");
    panel.setAttribute("aria-hidden", "false");
    marco.querySelector(".decu-activar-360")?.setAttribute("aria-pressed", "true");
    visor.dismissPoster?.();
    visor.focus({ preventScroll: true });
  }

  function cerrar360(codigo) {
    const visor = document.getElementById(`decu-modelo-${codigo}`);
    if (!visor) return;
    const marco = visor.closest("[data-ficha-imagen-principal]");
    const panel = visor.closest("[data-decu-visor]");
    if (!marco || !panel) return;
    marco.className = marco.dataset.claseAntes3d || "ficha-imagen-recorte completa";
    delete marco.dataset.claseAntes3d;
    marco.setAttribute("data-ficha-imagen-principal", "");
    panel.setAttribute("aria-hidden", "true");
    marco.querySelector(".decu-activar-360")?.setAttribute("aria-pressed", "false");
  }

  document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Escape") return;
    if (!document.getElementById("decu-qr-modal")?.hidden) {
      cerrarQr();
      return;
    }
    const visorActivo = document.querySelector(".decu-3d-activo model-viewer");
    if (visorActivo) cerrar360(visorActivo.id.replace("decu-modelo-", ""));
  });

  // Se carga en paralelo con productos.json. Cuando el usuario abre una ficha,
  // las funciones de galería deciden si ese código ya tiene un GLB generado.
  cargar();
  window.DecuVisor3D = {
    cargar,
    obtener,
    galeria,
    accion,
    activar360,
    cerrar360,
    verEnAmbiente,
    cerrarQr,
  };
})();
