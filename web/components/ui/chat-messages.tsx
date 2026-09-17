"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Send, RotateCcw, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export interface ChatMessagesProps {
  messages?: ChatMessage[];
  autoPlay?: boolean;
  autoPlayDelay?: number;
  typingDuration?: number;
  showReplay?: boolean;
  interactive?: boolean;
  className?: string;
}

const DEFAULT_MESSAGES: ChatMessage[] = [
  {
    id: "1",
    sender: "assistant",
    content: "Olá! Sou a IA da Secretaria da ETEC. Como posso te ajudar hoje?",
  },
  {
    id: "2",
    sender: "user",
    content: "Eu perdi um casaco azul no pátio ontem, alguém entregou?",
  },
  {
    id: "3",
    sender: "assistant",
    content: "Vou verificar no nosso catálogo... Sim! Temos um casaco azul registrado. Clique na aba Catálogo para ver a foto e solicitar a retirada.",
  },
];

function TypingIndicator({ className }: { className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={cn(
        "inline-flex items-center gap-1 rounded-2xl rounded-tl-md border border-white/10 bg-zinc-800/90 px-4 py-3 backdrop-blur-sm",
        className,
      )}
    >
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-2 w-2 rounded-full bg-white/60"
          animate={{ opacity: [0.4, 1, 0.4], y: [0, -4, 0] }}
          transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15, ease: "easeInOut" }}
        />
      ))}
    </motion.div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.sender === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.96, x: isUser ? 20 : -20 }}
      animate={{ opacity: 1, y: 0, scale: 1, x: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}
    >
      <div className={cn("flex items-end gap-2 max-w-[85%]", isUser && "flex-row-reverse")}>
        {!isUser && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-red-600 to-rose-900 shadow-md">
            <Sparkles className="size-4 text-white" />
          </div>
        )}
        <motion.div
          layout
          className={cn(
            "rounded-2xl px-4 py-2.5 text-xs leading-relaxed shadow-md",
            isUser
              ? "rounded-tr-md bg-gradient-to-r from-red-600 to-rose-800 text-white shadow-[0_8px_24px_-4px_rgba(220,38,38,0.4)]"
              : "rounded-tl-md border border-white/10 bg-zinc-800/90 text-zinc-100 backdrop-blur-sm",
          )}
        >
          {message.content}
        </motion.div>
      </div>
    </motion.div>
  );
}

export function ChatMessages({
  messages = DEFAULT_MESSAGES,
  autoPlay = true,
  autoPlayDelay = 1800,
  typingDuration = 1400,
  showReplay = true,
  interactive = true,
  className,
}: ChatMessagesProps) {
  const [visibleCount, setVisibleCount] = useState(autoPlay ? 0 : messages.length);
  const [isTyping, setIsTyping] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(messages);
  const scrollRef = useRef<HTMLDivElement>(null);
  const isAutoPlaying = useRef(false);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  }, []);

  const revealNext = useCallback(async (index: number) => {
    if (index >= chatMessages.length) { isAutoPlaying.current = false; return; }
    const message = chatMessages[index];
    if (message.sender === "assistant") {
      setIsTyping(true);
      await new Promise((r) => setTimeout(r, typingDuration));
      setIsTyping(false);
    }
    setVisibleCount(index + 1);
    scrollToBottom();
    await new Promise((r) => setTimeout(r, autoPlayDelay - (message.sender === "assistant" ? typingDuration : 0)));
    if (isAutoPlaying.current) revealNext(index + 1);
  }, [chatMessages, autoPlayDelay, typingDuration, scrollToBottom]);

  const replay = useCallback(() => {
    setVisibleCount(0); setChatMessages(messages); isAutoPlaying.current = true; setTimeout(() => revealNext(0), 100);
  }, [messages, revealNext]);

  useEffect(() => {
    setChatMessages(messages);
    if (autoPlay) {
      setVisibleCount(0); isAutoPlaying.current = true;
      const timer = setTimeout(() => revealNext(0), 500);
      return () => { clearTimeout(timer); isAutoPlaying.current = false; };
    }
  }, [messages, autoPlay, revealNext]);

  useEffect(() => { scrollToBottom(); }, [visibleCount, isTyping, scrollToBottom]);

  const handleSend = useCallback(() => {
    if (!inputValue.trim() || !interactive) return;
    const newMessage: ChatMessage = { id: `user-${Date.now()}`, sender: "user", content: inputValue.trim() };
    setChatMessages((prev) => [...prev, newMessage]);
    setInputValue("");
    setVisibleCount((prev) => prev + 1);
    setTimeout(() => {
      const reply: ChatMessage = { id: `assistant-${Date.now()}`, sender: "assistant", content: "Mensagem recebida! Um funcionário da secretaria responderá em breve." };
      setChatMessages((prev) => [...prev, reply]);
      setVisibleCount((prev) => prev + 1);
    }, typingDuration + 500);
  }, [inputValue, interactive, typingDuration]);

  return (
    <div className={cn("relative flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900 to-zinc-950 shadow-[0_24px_64px_-16px_rgba(0,0,0,0.5)]", className)}>
      <div className="flex items-center justify-between border-b border-white/5 px-4 py-3 bg-zinc-900/80">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-red-600 to-rose-900 shadow-md">
            <Sparkles className="size-4 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-white">Secretaria ETEC</h3>
            <p className="text-[10px] text-white/40">Atendimento Inteligente</p>
          </div>
        </div>
        {showReplay && (
          <button onClick={replay} className="flex items-center gap-1.5 rounded-lg bg-white/5 px-3 py-1.5 text-xs text-white/60 transition-colors hover:bg-white/10 hover:text-white"><RotateCcw className="size-3.5" /> Replay</button>
        )}
      </div>
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4 scrollbar-thin">
        {chatMessages.slice(0, visibleCount).map((message) => <MessageBubble key={message.id} message={message} />)}
        <AnimatePresence>{isTyping && <TypingIndicator />}</AnimatePresence>
      </div>
      <div className="border-t border-white/5 p-3 bg-zinc-900/60">
        <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-zinc-800/50 px-4 py-2 focus-within:border-white/20">
          <input type="text" value={inputValue} onChange={(e) => setInputValue(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleSend(); } }} placeholder="Escreva sua mensagem..." className="flex-1 bg-transparent text-sm text-white outline-none placeholder:text-white/30" />
          <button onClick={handleSend} disabled={!inputValue.trim()} className={cn("flex h-8 w-8 items-center justify-center rounded-lg transition-colors", inputValue.trim() ? "bg-red-600 text-white hover:bg-red-500" : "bg-white/5 text-white/30")}><Send className="size-4" /></button>
        </div>
      </div>
    </div>
  );
}

export default ChatMessages;
