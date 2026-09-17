"use client";

import { useState } from "react";
import { UserCircle2, ShieldCheck, XCircle } from "lucide-react";

const API_URL = "https://etec-achados.up.railway.app";

export default function LoginPage() {
  const [telaAtiva, setTelaAtiva] = useState<"login" | "cadastro" | "recuperar">("login");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [codigo, setCodigo] = useState("");
  const [nome, setNome] = useState("");
  const [rm, setRm] = useState("");
  const [loading, setLoading] = useState(false);
  const [codigoEnviado, setCodigoEnviado] = useState(false);
  const [toast, setToast] = useState<{ msg: string; tipo: "erro" | "sucesso" } | null>(null);

  const mostrarToast = (msg: string, tipo: "erro" | "sucesso") => {
    setToast({ msg, tipo });
    setTimeout(() => setToast(null), 4000);
  };

  const fazerLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/login-aluno`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, senha }),
      });
      const data = await res.json();
      if (data.success) {
        localStorage.setItem("aluno_token", data.token);
        localStorage.setItem("aluno_dados", JSON.stringify(data.aluno));
        mostrarToast("Login efetuado com sucesso!", "sucesso");
      } else {
        mostrarToast(data.message || "Erro ao fazer login.", "erro");
      }
    } catch (error) {
      mostrarToast("Erro de conexão com o servidor.", "erro");
    }
    setLoading(false);
  };

  const enviarCodigo = async () => {
    if (!email.endsWith("@aluno.cps.sp.gov.br")) {
      return mostrarToast("Use um e-mail @aluno.cps.sp.gov.br", "erro");
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/enviar-codigo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (data.success) {
        setCodigoEnviado(true);
        mostrarToast("Código enviado para o seu e-mail!", "sucesso");
      } else {
        mostrarToast(data.message, "erro");
      }
    } catch (error) {
      mostrarToast("Erro na rede.", "erro");
    }
    setLoading(false);
  };

  const confirmarCadastro = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/cadastrar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, codigo, nome, rm, senha }),
      });
      const data = await res.json();
      if (data.success) {
        localStorage.setItem("aluno_token", data.token);
        localStorage.setItem("aluno_dados", JSON.stringify(data.aluno));
        mostrarToast("Conta criada com sucesso!", "sucesso");
      } else {
        mostrarToast(data.message, "erro");
      }
    } catch (error) {
      mostrarToast("Erro ao finalizar cadastro.", "erro");
    }
    setLoading(false);
  };

  const confirmarRedefinicao = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/auth/redefinir`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, codigo, senha }),
      });
      const data = await res.json();
      if (data.success) {
        mostrarToast("Senha alterada com sucesso! Faça login.", "sucesso");
        setTelaAtiva("login");
        setCodigoEnviado(false);
        setSenha("");
      } else {
        mostrarToast(data.message, "erro");
      }
    } catch (error) {
      mostrarToast("Erro ao redefinir senha.", "erro");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#0d1117] flex items-center justify-center p-4">
      {toast && (
        <div className="fixed top-5 right-5 z-50">
          <div className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl border ${toast.tipo === 'sucesso' ? 'bg-emerald-950/50 border-emerald-900 text-emerald-400' : 'bg-red-950/50 border-red-900 text-red-400'}`}>
            {toast.tipo === 'sucesso' ? <ShieldCheck className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
            <p className="text-sm font-bold">{toast.msg}</p>
          </div>
        </div>
      )}

      <div className="w-full max-w-sm bg-[#161b22] border border-[#30363d] rounded-2xl p-8 shadow-2xl">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-red-600 to-rose-900 flex items-center justify-center text-white mx-auto shadow-[0_8px_24px_-4px_rgba(220,38,38,0.5)] mb-4">
            <UserCircle2 className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-black text-[#c9d1d9]">Acesso do Aluno</h2>
          <p className="text-xs text-[#8b949e] mt-2">Utilize seu e-mail institucional</p>
        </div>

        {telaAtiva === "login" && (
          <form onSubmit={fazerLogin} className="space-y-4">
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="E-mail @aluno.cps.sp.gov.br" className="w-full bg-[#0d1117] border border-[#30363d] text-[#c9d1d9] text-sm rounded-xl px-4 py-3.5 focus:outline-none focus:border-red-500 transition-colors" />
            <input type="password" required value={senha} onChange={(e) => setSenha(e.target.value)} placeholder="Sua Senha" className="w-full bg-[#0d1117] border border-[#30363d] text-[#c9d1d9] text-sm rounded-xl px-4 py-3.5 focus:outline-none focus:border-red-500 transition-colors" />
            <button type="submit" disabled={loading} className="w-full bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 text-white font-bold py-3.5 rounded-xl text-sm uppercase shadow-lg transition-all disabled:opacity-50">
              {loading ? "Entrando..." : "Entrar no Sistema"}
            </button>
            <div className="flex justify-between text-xs font-bold pt-4">
              <button type="button" onClick={() => { setTelaAtiva("cadastro"); setCodigoEnviado(false); }} className="text-red-500 hover:text-red-400 transition-colors">Criar Conta</button>
              <button type="button" onClick={() => { setTelaAtiva("recuperar"); setCodigoEnviado(false); }} className="text-[#8b949e] hover:text-[#c9d1d9] transition-colors">Esqueceu a senha?</button>
            </div>
          </form>
        )}

        {telaAtiva === "cadastro" && (
          <form onSubmit={confirmarCadastro} className="space-y-4">
            {!codigoEnviado ? (
              <>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="E-mail @aluno.cps.sp.gov.br" className="w-full bg-[#0d1117] border border-[#30363d] text-[#c9d1d9] text-sm rounded-xl px-4 py-3.5 focus:outline-none focus:border-red-500" />
                <button type="button" onClick={enviarCodigo} disabled={loading || !email} className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3.5 rounded-xl text-sm uppercase shadow-lg transition-all disabled:opacity-50">
                  {loading ? "Enviando..." : "Enviar Código"}
                </button>
              </>
            ) : (
              <div className="space-y-3">
                <p className="text-[10px] text-amber-500 font-bold text-center uppercase tracking-wider">Verifique seu e-mail</p>
                <input type="text" required value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="Código de 6 dígitos" className="w-full bg-[#0d1117] border border-amber-500/30 text-amber-400 text-sm rounded-xl px-4 py-3.5 focus:outline-none focus:border-amber-500 text-center tracking-widest font-black" />
                <div className="grid grid-cols-3 gap-2">
                  <input type="text" required value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Nome Completo" className="col-span-2 w-full bg-[#0d1117] border border-[#30363d] text-[#c9d1d9] text-sm rounded-xl px-4 py-3.5 focus:outline-none focus:border-red-500" />
                  <input type="number" required value={rm} onChange={(e) => setRm(e.target.value)} placeholder="RM" className="col-span-1 w-full bg-[#0d1117] border border-[#30363d] text-[#c9d1d9] text-sm rounded-xl px-4 py-3.5 focus:outline-none focus:border-red-500" />
                </div>
                <input type="password" required value={senha} onChange={(e) => setSenha(e.target.value)} placeholder="Crie uma Senha Forte" className="w-full bg-[#0d1117] border border-[#30363d] text-[#c9d1d9] text-sm rounded-xl px-4 py-3.5 focus:outline-none focus:border-red-500" />
                <button type="submit" disabled={loading} className="w-full bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 text-white font-bold py-3.5 rounded-xl text-sm uppercase shadow-lg transition-all disabled:opacity-50">
                  {loading ? "Processando..." : "Finalizar Cadastro"}
                </button>
              </div>
            )}
            <button type="button" onClick={() => setTelaAtiva("login")} className="w-full text-xs font-bold text-[#8b949e] hover:text-[#c9d1d9] mt-2 transition-colors">Voltar para Login</button>
          </form>
        )}

        {telaAtiva === "recuperar" && (
          <form onSubmit={confirmarRedefinicao} className="space-y-4">
             {!codigoEnviado ? (
              <>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="E-mail Institucional" className="w-full bg-[#0d1117] border border-[#30363d] text-[#c9d1d9] text-sm rounded-xl px-4 py-3.5 focus:outline-none focus:border-amber-500" />
                <button type="button" onClick={enviarCodigo} disabled={loading || !email} className="w-full bg-amber-600 hover:bg-amber-500 text-white font-bold py-3.5 rounded-xl text-sm uppercase shadow-lg transition-all disabled:opacity-50">
                  {loading ? "Enviando..." : "Solicitar Redefinição"}
                </button>
              </>
            ) : (
              <div className="space-y-3">
                <input type="text" required value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="Código recebido no e-mail" className="w-full bg-[#0d1117] border border-amber-500/30 text-amber-400 text-sm rounded-xl px-4 py-3.5 focus:outline-none focus:border-amber-500 text-center tracking-widest font-black" />
                <input type="password" required value={senha} onChange={(e) => setSenha(e.target.value)} placeholder="Digite a Nova Senha" className="w-full bg-[#0d1117] border border-[#30363d] text-[#c9d1d9] text-sm rounded-xl px-4 py-3.5 focus:outline-none focus:border-red-500" />
                <button type="submit" disabled={loading} className="w-full bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 text-white font-bold py-3.5 rounded-xl text-sm uppercase shadow-lg transition-all disabled:opacity-50">
                  {loading ? "Salvando..." : "Salvar Nova Senha"}
                </button>
              </div>
            )}
            <button type="button" onClick={() => setTelaAtiva("login")} className="w-full text-xs font-bold text-[#8b949e] hover:text-[#c9d1d9] mt-2 transition-colors">Voltar para Login</button>
          </form>
        )}
      </div>
    </div>
  );
}
