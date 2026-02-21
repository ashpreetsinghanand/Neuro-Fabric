import { useEffect, useRef, useState } from 'react';

const USER_AVATAR = "https://lh3.googleusercontent.com/aida-public/AB6AXuDt1FOc6XayHpPma7I3dgPZkGjT8NsmZ-GyYPuR4dRtW7oa-i9i1yux6ONhfZ-HqZpifHdDKLDnt-95w2bj9kspJjW00VUNqiU_ajpXajJWTjTCleHLMp_TDr33D0TjWg4z1E-USglXOWPnDruOlI0qndICNM5Lk9gx9DxegSj-QZB9kOCGa5wgm8nOifOVQEC0jXKUgq7tv6tYWFrKqATSgluxE-TlxNW24RLCjPS4DUQeqgR8psU_L3D5B_N_kIlNaR03wG8Qm_o";
const USER_AVATAR_LARGE = "https://lh3.googleusercontent.com/aida-public/AB6AXuDzfAfU4tTgSq9RZxUogxt_dSIiezbE4knA0ufsMScTYyqsxX6O_fJ7Mb2Yd2BWFh1QKtD5NkuG9tRV8iK6UwWon9SMxUZ4BOt_swP77lSDsmC6jETOY5YGDjmBHxMYKr7ndMUwj290kXy4sPVqp3QppYZjTXEw9oMctRLACPFu7A9NaJAmgFpI-smz21sPUskjTKzeDBVOz4oMljGYmbPWasa3scue6BeBWIjV60sFxg4VEqZ9Yh_WnDZM1r-4bFUnkl3Sxkc2Ivg";

const DEFAULT_CHATS = [
  {
    id: '1',
    title: 'Project Planning',
    messages: [
      { id: 'm1', role: 'assistant', text: "Hello Alex! I'm ready to help you coordinate your project plan. What phase are we looking at today?" },
      { id: 'm2', role: 'user', text: "I need to create a timeline for a 3-month software development cycle. Can you help me break it down into manageable sprints?" },
      {
        id: 'm3',
        role: 'assistant',
        text: "A 3-month (approx. 12-week) cycle works best when broken into 6 two-week sprints. Here is a high-level breakdown for a professional development lifecycle:",
        sprintList: [
          { num: '01', title: 'Sprint 1-2: Foundation & Core Architecture', desc: 'Environment setup, database schema design, and core authentication modules.' },
          { num: '02', title: 'Sprint 3-4: Feature Development (Phase A)', desc: 'Implementing the primary user interface and essential business logic components.' },
          { num: '03', title: 'Sprint 5-6: Integration & QA', desc: 'API integrations, final feature polish, and rigorous regression testing.' },
        ],
        textAfter: "Would you like to drill down into the specific deliverables for the Foundation Phase?",
      },
    ],
  },
  { id: '2', title: 'Python Debugging', messages: [] },
  { id: '3', title: 'Marketing Copy v2', messages: [] },
  { id: '4', title: 'Travel Ideas: Iceland', messages: [] },
];

let nextChatId = 5;
let nextMessageId = 100;

function App() {
  const [chats, setChats] = useState(DEFAULT_CHATS);
  const [activeChatId, setActiveChatId] = useState('1');
  const [messageInput, setMessageInput] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const activeChat = chats.find((c) => c.id === activeChatId) || chats[0];

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(() => scrollToBottom(), [activeChat?.messages]);

  const handleNewChat = () => {
    const newChat = { id: String(nextChatId++), title: 'New Chat', messages: [] };
    setChats((prev) => [newChat, ...prev]);
    setActiveChatId(newChat.id);
  };

  const handleSend = () => {
    const trimmed = messageInput.trim();
    if (!trimmed) return;
    setMessageInput('');
    const userMsg = { id: `msg-${nextMessageId++}`, role: 'user', text: trimmed };
    const assistantMsg = {
      id: `msg-${nextMessageId++}`,
      role: 'assistant',
      text: "Thanks for your message. This is a demo; connect a backend to get real AI responses.",
    };
    setChats((prev) =>
      prev.map((c) =>
        c.id === activeChatId
          ? {
            ...c,
            title: c.messages.length === 0 ? trimmed.slice(0, 40) + (trimmed.length > 40 ? '…' : '') : c.title,
            messages: [...c.messages, userMsg, assistantMsg],
          }
          : c
      )
    );
    setTimeout(() => scrollToBottom(), 50);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = (text, sprintList, textAfter) => {
    let full = text || '';
    if (sprintList?.length) {
      full += '\n' + sprintList.map((s) => `${s.num} ${s.title}\n${s.desc}`).join('\n\n');
    }
    if (textAfter) full += '\n\n' + textAfter;
    navigator.clipboard?.writeText(full);
  };

  return (
    <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 font-display">
      <div className="flex h-screen w-full overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-64 bg-slate-50 dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 flex flex-col shrink-0 transition-all">
          <div className="p-4 flex flex-col gap-4 h-full">
            <button
              type="button"
              onClick={handleNewChat}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors w-full text-left group"
            >
              <span className="material-symbols-outlined text-slate-600 dark:text-slate-400 group-hover:text-primary transition-colors" style={{ fontSize: '20px' }}>add</span>
              <span className="text-sm font-medium">New Chat</span>
            </button>
            <div className="flex-1 overflow-y-auto custom-scrollbar -mx-2 px-2 flex flex-col gap-1">
              <p className="text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-3 mb-2 mt-4">Recent History</p>
              {chats.map((chat) => (
                <button
                  type="button"
                  key={chat.id}
                  onClick={() => setActiveChatId(chat.id)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg w-full text-left cursor-pointer group transition-colors ${chat.id === activeChatId
                      ? 'bg-slate-200/50 dark:bg-slate-900 text-slate-900 dark:text-slate-100'
                      : 'hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-600 dark:text-slate-400'
                    }`}
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: '18px', fontVariationSettings: chat.id === activeChatId ? "'FILL' 1" : undefined }}
                  >
                    chat_bubble
                  </span>
                  <span className="text-sm truncate flex-1">{chat.title}</span>
                  <span className="material-symbols-outlined text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" style={{ fontSize: '16px' }}>more_horiz</span>
                </button>
              ))}
            </div>
            <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-col gap-1">
              <button type="button" className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-900 cursor-pointer transition-colors group w-full text-left">
                <span className="material-symbols-outlined text-slate-600 dark:text-slate-400 group-hover:text-primary" style={{ fontSize: '20px' }}>settings</span>
                <span className="text-sm">Settings</span>
              </button>
              <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-900 cursor-pointer transition-colors group">
                <div className="size-6 rounded-full bg-slate-300 dark:bg-slate-800 flex items-center justify-center overflow-hidden">
                  <img className="w-full h-full object-cover" alt="User avatar profile" src={USER_AVATAR_LARGE} />
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-medium">Alex Chen</span>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wide">Pro Plan</span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col bg-white dark:bg-background-dark relative">
          <header className="h-14 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6 bg-white/80 dark:bg-background-dark/80 backdrop-blur-md sticky top-0 z-10">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold tracking-tight">{activeChat.title}</span>
              <span className="px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-[10px] text-slate-500 font-bold uppercase tracking-wide">Model 4.0</span>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition-colors">
                <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>ios_share</span>
              </button>
              <button type="button" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition-colors">
                <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>more_vert</span>
              </button>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto custom-scrollbar">
            <div className="max-w-3xl mx-auto py-10 px-6 flex flex-col gap-10">
              {activeChat.messages.length === 0 && (
                <div className="flex gap-6 group">
                  <div className="size-8 rounded-lg bg-primary/10 dark:bg-primary/20 flex items-center justify-center shrink-0 mt-1">
                    <span className="material-symbols-outlined text-primary" style={{ fontSize: '18px', fontVariationSettings: "'FILL' 1" }}>smart_toy</span>
                  </div>
                  <div className="flex flex-col gap-2 flex-1">
                    <p className="text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">Assistant</p>
                    <p className="text-slate-800 dark:text-slate-200 leading-relaxed">Start a conversation by typing a message below.</p>
                  </div>
                </div>
              )}
              {activeChat.messages.map((msg) =>
                msg.role === 'assistant' ? (
                  <div key={msg.id} className="flex gap-6 group">
                    <div className="size-8 rounded-lg bg-primary/10 dark:bg-primary/20 flex items-center justify-center shrink-0 mt-1">
                      <span className="material-symbols-outlined text-primary" style={{ fontSize: '18px', fontVariationSettings: "'FILL' 1" }}>smart_toy</span>
                    </div>
                    <div className="flex flex-col gap-2 flex-1">
                      <p className="text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">Assistant</p>
                      <div className="text-slate-800 dark:text-slate-200 leading-relaxed space-y-4">
                        {msg.text && <p>{msg.text}</p>}
                        {msg.sprintList && msg.sprintList.length > 0 && (
                          <div className="bg-slate-50 dark:bg-slate-900/40 p-5 rounded-xl border border-slate-200 dark:border-slate-800 space-y-3">
                            {msg.sprintList.map((item) => (
                              <div key={item.num} className="flex gap-4">
                                <span className="text-primary font-bold">{item.num}</span>
                                <div>
                                  <p className="font-semibold text-sm">{item.title}</p>
                                  <p className="text-sm text-slate-500 dark:text-slate-400">{item.desc}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                        {msg.textAfter && <p>{msg.textAfter}</p>}
                      </div>
                      <div className="flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          type="button"
                          onClick={() => handleCopy(msg.text, msg.sprintList, msg.textAfter)}
                          className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-primary transition-colors"
                        >
                          <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>content_copy</span>
                        </button>
                        <button type="button" className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-green-500 transition-colors">
                          <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>thumb_up</span>
                        </button>
                        <button type="button" className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-red-500 transition-colors">
                          <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>thumb_down</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div key={msg.id} className="flex gap-6 justify-end">
                    <div className="flex flex-col gap-2 items-end max-w-[85%]">
                      <p className="text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mr-2">You</p>
                      <div className="bg-slate-100 dark:bg-slate-900 px-5 py-3.5 rounded-2xl rounded-tr-none text-slate-800 dark:text-slate-200 leading-relaxed border border-slate-200 dark:border-slate-800/50">
                        {msg.text}
                      </div>
                    </div>
                    <div className="size-8 rounded-full bg-slate-200 dark:bg-slate-800 flex items-center justify-center shrink-0 mt-1 overflow-hidden border border-slate-300 dark:border-slate-700">
                      <img className="w-full h-full object-cover" alt="User profile avatar" src={USER_AVATAR} />
                    </div>
                  </div>
                )
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          <div className="p-6 bg-gradient-to-t from-white via-white/95 to-transparent dark:from-background-dark dark:via-background-dark/95 dark:to-transparent">
            <div className="max-w-3xl mx-auto relative">
              <div className="relative flex items-center border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl shadow-xl shadow-slate-200/50 dark:shadow-none focus-within:border-primary/50 transition-all p-1">
                <button type="button" className="p-2 text-slate-400 hover:text-primary transition-colors">
                  <span className="material-symbols-outlined" style={{ fontSize: '24px' }}>attach_file</span>
                </button>
                <textarea
                  ref={textareaRef}
                  className="flex-1 bg-transparent border-none focus:ring-0 text-sm py-3 px-2 resize-none dark:text-slate-200 placeholder:text-slate-400 dark:placeholder:text-slate-600 custom-scrollbar"
                  placeholder="Message AI Assistant..."
                  rows={1}
                  style={{ minHeight: '44px', maxHeight: '200px' }}
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                />
                <div className="flex items-center gap-1 pr-1">
                  <button
                    type="button"
                    onClick={handleSend}
                    className="p-2 size-10 rounded-lg bg-primary text-white hover:bg-primary/90 transition-colors flex items-center justify-center"
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: '20px', fontVariationSettings: "'FILL' 1" }}>send</span>
                  </button>
                </div>
              </div>
              <p className="text-[10px] text-center mt-3 text-slate-400 uppercase tracking-widest font-medium">
                AI Assistant may provide inaccurate info. Verify important details.
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
