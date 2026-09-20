"""
Ponto de Entrada Legado e de Produção (Railway / Local)
Importa a aplicação configurada a partir dos módulos e executa o servidor.
"""
import os
from app import app
from config import PORT

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", PORT))
    print(f"🚀 [ETEC Achados e Perdidos v2.0] Servidor modular inicializado na porta {porta}")
    app.run(host='0.0.0.0', port=porta)
