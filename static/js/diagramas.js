import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';

mermaid.initialize({ startOnLoad: true });

function decodeHtmlEntities(str) {
    const txt = document.createElement("textarea");
    txt.innerHTML = str;
    return txt.value;
}

window.descargardiagrama = async function(formato = "svg") {
    const contenedor = document.getElementById("mermaid-code");
    if (!contenedor) {
        alert("No se encontró el código Mermaid.");
        return;
    }

    const codigoMermaid = decodeHtmlEntities(contenedor.textContent.trim());
    const { svg } = await mermaid.render("descarga-diagrama", codigoMermaid);
    
    const { proyecto, titulo, fecha } = window.DIAGRAMA_INFO;
    const nombreArchivo = `${proyecto}_${titulo}_${fecha}.${formato}`;

    if (formato === "svg") {
        const blob = new Blob([svg], { type: "image/svg+xml" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = nombreArchivo;
        a.click();
        URL.revokeObjectURL(url);
    }

    if (formato === "jpg") {
        try {
            const svgElement = document.querySelector(".mermaid svg");
            if (!svgElement) {
                alert("❌ No se encontró el SVG renderizado.");
                return;
            }

            let svgString = new XMLSerializer().serializeToString(svgElement);

            if (!svgString.includes("xmlns=\"http://www.w3.org/2000/svg\"")) {
                svgString = svgString.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"');
            }

            const svgBase64 = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgString)));

            const img = new Image();
            img.crossOrigin = "anonymous";
            img.onload = function () {
                const canvas = document.createElement("canvas");
                canvas.width = img.width * 9; 
                canvas.height = img.height * 9;
                const ctx = canvas.getContext("2d");

                // Fondo blanco para JPG
                ctx.fillStyle = "#ffffff";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

                // Exportar como JPG
                canvas.toBlob((blob) => {
                    const a = document.createElement("a");
                    a.href = URL.createObjectURL(blob);
                    a.download = nombreArchivo;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(a.href);
                }, "image/jpeg", 0.95);
            };

            img.onerror = function () {
                alert("❌ Error al cargar el SVG como imagen.");
            };

            img.src = svgBase64;

        } catch (error) {
            alert("❌ Error inesperado al exportar a JPG.");
            console.error(error);
        }
    }
};