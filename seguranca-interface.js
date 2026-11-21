// Codificação por contexto: texto HTML, argumentos JavaScript e URLs de imagens.
function textoHTML(valor) {
    return String(valor ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[char]);
}

function argumentoHTML(valor) {
    return textoHTML(JSON.stringify(valor) ?? 'null');
}

function urlImagemSegura(valor) {
    if (typeof valor !== 'string') return '';
    const url = valor.trim();
    if (!url) return '';
    if (/^data:image\/(?:png|jpe?g|webp|gif);base64,[A-Za-z0-9+/=\s]+$/i.test(url)) return url;
    try {
        const parsed = new URL(url, window.location.href);
        return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : '';
    } catch {
        return '';
    }
}

function imagemHTML(valor) {
    return textoHTML(urlImagemSegura(valor));
}

function abrirImagemSegura(valor) {
    const url = urlImagemSegura(valor);
    if (url) window.open(url, '_blank', 'noopener,noreferrer');
}

function definirTextoFormatado(destino, valor) {
    // Diálogos usam somente formatação básica, nunca atributos ou elementos ativos.
    const template = document.createElement('template');
    template.innerHTML = String(valor ?? '');
    const permitidos = new Set(['B', 'STRONG', 'EM', 'I', 'BR', 'P', 'UL', 'OL', 'LI', 'CODE', 'SPAN']);
    const fragmento = document.createDocumentFragment();
    function copiar(origem, alvo) {
        for (const node of origem.childNodes) {
            if (node.nodeType === 3) {
                alvo.appendChild(document.createTextNode(node.textContent));
            } else if (node.nodeType === 1 && permitidos.has(node.tagName)) {
                const elemento = document.createElement(node.tagName.toLowerCase());
                copiar(node, elemento);
                alvo.appendChild(elemento);
            } else if (node.nodeType === 1 && !['SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'TEMPLATE'].includes(node.tagName)) {
                alvo.appendChild(document.createTextNode(node.textContent));
            }
        }
    }
    copiar(template.content, fragmento);
    destino.replaceChildren(fragmento);
}
