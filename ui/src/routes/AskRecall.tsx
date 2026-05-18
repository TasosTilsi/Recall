import { useState } from 'react';
import { chat } from '@/api/client';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send, User, Bot, BookOpen } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
}

export default function AskRecall() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const result = await chat(input);
      const assistantMsg: Message = {
        role: 'assistant',
        content: result.response,
        sources: result.sources
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Could not reach the chat engine.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: '#0b1326' }}>
      <div className="p-4 border-b border-slate-800 bg-[#131b2e]">
        <h1 className="text-lg font-bold text-white flex items-center gap-2">
          <Bot size={20} className="text-blue-400" />
          Ask Recall
        </h1>
        <p className="text-xs text-slate-400">Query your multi-repo knowledge graph with AI.</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-50">
                <Bot size={48} className="mb-4 text-blue-400" />
                <p className="text-white font-medium">How can I help you discover your code?</p>
                <p className="text-xs text-slate-400 mt-1 max-w-xs">Ask about decisions, workflows, or patterns across your projects.</p>
            </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-4 ${msg.role === 'assistant' ? 'bg-slate-800/20 p-4 rounded-lg' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-blue-600' : 'bg-slate-700'}`}>
              {msg.role === 'user' ? <User size={16} className="text-white" /> : <Bot size={16} className="text-blue-400" />}
            </div>
            <div className="flex-1 space-y-2">
              <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-4 pt-4 border-t border-slate-800">
                  <p className="text-[10px] font-bold text-slate-500 uppercase mb-2 flex items-center gap-1">
                    <BookOpen size={10} />
                    Knowledge Sources
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.map((s: any, idx: number) => (
                      <span key={idx} className="text-[10px] bg-slate-800 text-blue-400 px-2 py-1 rounded border border-slate-700">
                        {s.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
            <div className="flex gap-4 bg-slate-800/20 p-4 rounded-lg animate-pulse">
                <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
                    <Bot size={16} className="text-blue-400" />
                </div>
                <div className="flex-1 space-y-2">
                    <div className="h-4 bg-slate-700 rounded w-3/4"></div>
                    <div className="h-4 bg-slate-700 rounded w-1/2"></div>
                </div>
            </div>
        )}
      </div>

      <div className="p-4 border-t border-slate-800 bg-[#131b2e]">
        <div className="flex gap-2">
          <Input
            placeholder="Search decisions, patterns, workflows..."
            className="bg-[#0b1326] border-slate-700 text-white"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <Button size="icon" onClick={handleSend} disabled={loading}>
            <Send size={18} />
          </Button>
        </div>
      </div>
    </div>
  );
}
