/* Aspas preservam separadores/quebras; apóstrofo impede fórmula de planilha. */
const CSVSeguro = {
    valor(valor) {
        const texto = valor == null ? '' : String(valor);
        const inicio = texto.normalize('NFKC').replace(/^[\s\uFEFF\u200B]+/, '');
        return /^[=+\-@]/.test(inicio) || /^[\t\r\n]/.test(texto) ? "'" + texto : texto;
    },
    celula(valor) { return '"' + this.valor(valor).replace(/"/g, '""') + '"'; },
    linha(valores) { return valores.map(v => this.celula(v)).join(';') + '\r\n'; }
};
if (typeof module !== 'undefined') module.exports = CSVSeguro;
