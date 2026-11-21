"""Fotos privadas e registro do aceite para novos cadastros."""
VERSAO_TERMOS='2026-11-15'
SECOES_TERMOS=[
 ('Finalidade do portal','Este portal auxilia a comunidade escolar a cadastrar, procurar e devolver objetos. Use sua própria conta e seu e-mail institucional. O acesso ao painel da secretaria depende de autorização da instituição.'),
 ('Informações corretas','Informe seu nome e sua matrícula com cuidado. Não use a identidade de outra pessoa. A confirmação do e-mail e uma foto de perfil não comprovam, por si sós, a matrícula ou a propriedade de um objeto.'),
 ('Objetos e retirada','Cadastre apenas informações verdadeiras e imagens adequadas dos objetos. Não publique documentos, rostos de terceiros, dados pessoais desnecessários ou conteúdo ofensivo. A equipe pode solicitar correções e moderar cadastros. A retirada depende de conferência presencial, código quando aplicável e registro de recebimento pela equipe autorizada.'),
 ('Foto de perfil opcional','Você pode adicionar e remover sua foto no perfil. Use uma foto apenas sua, de frente, com cabeça e ombros enquadrados e o rosto inteiro visível. Evite máscara, óculos escuros, filtros, montagens ou objetos cobrindo o rosto. A foto serve como apoio visual à secretaria e não fica no catálogo público. A pré-verificação local procura rosto e olhos visíveis; ela pode falhar e não garante autenticidade, identidade ou ausência de qualquer obstrução.'),
 ('Dados e acesso','O serviço utiliza nome, e-mail institucional, matrícula, senha protegida por hash, cadastros, mensagens, registros de ações e entregas. A foto de perfil e seu registro de aceite são associados à sua conta. Apenas você e a equipe autorizada podem consultar sua foto. Professores autorizados a atuar como moderação fazem parte dessa equipe. As informações públicas dos objetos não devem expor os dados privados de quem os cadastrou ou solicitou.'),
 ('Armazenamento e serviços','A foto de perfil é reduzida e armazenada no banco do serviço, sem envio ao provedor de análise visual. Fotos de objetos podem utilizar Cloudinary; mensagens por e-mail, análise de objetos e notificações dependem dos provedores configurados pela instituição. As mensagens do chat têm retenção de 30 dias. Outros registros são mantidos conforme a necessidade de operação e auditoria; consulte a secretaria sobre acesso, correção ou remoção dos seus dados.'),
 ('Cuidados com a conta','Proteja sua senha, saia ao terminar em computadores compartilhados e use Lembrar de mim apenas em dispositivo de confiança. Não compartilhe códigos de acesso ou retirada. Avise a secretaria se identificar uso indevido ou um cadastro incorreto.'),
 ('Aceite e contato','Ao marcar o aceite e concluir o cadastro, você concorda com estas regras e declara estar ciente do uso dos dados descrito aqui. A versão dos termos e a data do aceite são registradas pelo servidor. Dúvidas sobre o portal e solicitações relacionadas aos dados devem ser encaminhadas à secretaria da instituição responsável por disponibilizá-lo.')
]
SCHEMA_PERFIS='''
CREATE TABLE IF NOT EXISTS perfis_fotos (
 email VARCHAR(150) PRIMARY KEY REFERENCES alunos(email) ON DELETE CASCADE,
 id UUID UNIQUE NOT NULL, foto BYTEA NOT NULL CHECK(octet_length(foto)<=65536),
 atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS termos_aceites (
 email VARCHAR(150) PRIMARY KEY REFERENCES alunos(email) ON DELETE CASCADE,
 versao VARCHAR(30) NOT NULL, aceito_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
'''


def validar_aceite(dados):
    if not isinstance(dados,dict) or dados.get('aceite_termos') is not True:
        return 'Leia e aceite os Termos de Uso para criar sua conta.'
    if dados.get('versao_termos')!=VERSAO_TERMOS:
        return 'Os termos foram atualizados. Abra os termos novamente e confirme o aceite.'


def registrar_aceite(cursor,email):
    cursor.execute('INSERT INTO termos_aceites(email,versao) VALUES(%s,%s)',(email,VERSAO_TERMOS))
