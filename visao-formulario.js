// Só sugestões completas e explicitamente liberadas pelo serviço são aplicadas.
function aplicarSugestaoVisual(resultado, campos) {
    if (!resultado || resultado.pode_preencher !== true || resultado.metodo !== 'gemini_vision_ocr'
        || !['alta', 'media'].includes(resultado.confianca_objeto)
        || typeof resultado.nome !== 'string' || !resultado.nome.trim()
        || typeof resultado.descricao !== 'string' || !resultado.descricao.trim()) return false;
    const normalizar = valor => String(valor || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toUpperCase();
    if (campos.nome) campos.nome.value = resultado.nome;
    if (campos.descricao) campos.descricao.value = resultado.descricao;
    const categoria = normalizar(resultado.categoria);
    if (campos.categoria && categoria) {
        const opcao = Array.from(campos.categoria.options).find(opt => normalizar(opt.value) === categoria);
        if (opcao) campos.categoria.value = opcao.value;
    }
    return true;
}
