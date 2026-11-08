# Recursos locais da interface

Arquivos distribuídos localmente para permitir abertura offline e fixar versões:

- Tailwind CSS 3.4.17: `tailwind.css`, gerado com o conteúdo do portal. Licença MIT em `tailwind-license.txt`.
- Font Awesome Free 6.5.1: CSS e fontes WOFF2 obtidos do cdnjs. Licenças em `fontawesome-license.txt`; avisos também preservados no CSS.
- Plus Jakarta Sans e Inter: subconjunto Latin, pesos variáveis 400–800, obtido pela API oficial Google Fonts. Licenças SIL OFL em `jakarta-ofl.txt` e `inter-ofl.txt`.
- Chart.js 4.4.8: distribuição UMD do jsDelivr, licença MIT em `chart-license.txt`.
- QRCode.js 1.0.0: cdnjs, licença MIT em `qrcode-license.txt`.
- html5-qrcode 2.3.8: unpkg, licença Apache 2.0 em `html5-qrcode-license.txt`.

As bibliotecas são cópias de distribuição; os avisos de licença foram preservados. A fonte da UI não contém dados de usuário.

Para regenerar o CSS após acrescentar classes Tailwind, na raiz do projeto:

```sh
printf '@tailwind base;\n@tailwind components;\n@tailwind utilities;\n' > /tmp/etec-tailwind.css
npm exec --yes --package=tailwindcss@3.4.17 -- tailwindcss -i /tmp/etec-tailwind.css -c tailwind.config.cjs -o vendor/tailwind.css --minify
```

O servidor de produção não precisa de Node/npm. Ao alterar recursos da interface, atualize a versão do cache em `sw.js` e verifique seu precache antes de publicar.
