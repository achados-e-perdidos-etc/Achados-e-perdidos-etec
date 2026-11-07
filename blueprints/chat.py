"""Rotas modulares: usam o mesmo isolamento de conversas do servidor unificado."""
from flask import Blueprint
from database import get_db_connection
from utils.security import token_required, secretaria_required
from services import chat_service, chat_retencao
chat_bp = Blueprint('chat', __name__)
chat_bp.before_app_request(chat_retencao.iniciar)

@chat_bp.route('/api/chat/enviar', methods=['POST','OPTIONS'])
@token_required
def enviar_chat(): return chat_service.enviar(get_db_connection)

@chat_bp.route('/api/chat/mensagens/<string:rm>', methods=['GET','OPTIONS'])
@token_required
def buscar_mensagens(rm): return chat_service.mensagens(get_db_connection, rm)

@chat_bp.route('/api/chat/legado/<string:rm>', methods=['GET','OPTIONS'])
@secretaria_required
def buscar_legado(rm): return chat_service.mensagens(get_db_connection, rm, legado=True)

@chat_bp.route('/api/chat/conversas', methods=['GET','OPTIONS'])
@secretaria_required
def listar_conversas(): return chat_service.conversas(get_db_connection)
