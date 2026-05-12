import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../SupabaseClient';
import Sidebar from '../components/Sidebar';
import '../styles/chat.css';

function Chat() {
  const navigate = useNavigate();
  const scrollRef = useRef(null);
  
  const [user, setUser] = useState(null);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { role: 'bot', content: 'What can I help you?' }
  ]);
  const [history, setHistory] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // 1. Load User & History di awal
  useEffect(() => {
    const loadData = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        navigate('/');
      } else {
        setUser(user);
        
        const { data: chatData, error } = await supabase
          .from('chat_history')
          .select('*')
          .eq('user_id', user.id)
          .order('created_at', { ascending: false });

        if (!error && chatData) setHistory(chatData);
      }
    };
    loadData();
  }, [navigate]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 2. Fungsi untuk load isi chat saat history di-klik
  const loadChatSession = async (chatId) => {
    setCurrentChatId(chatId);
    
    // Ambil semua pesan dari tabel chat_messages berdasarkan chat_id
    const { data, error } = await supabase
      .from('chat_messages')
      .select('role, content')
      .eq('chat_id', chatId)
      .order('created_at', { ascending: true });

    if (error) {
      console.error("Gagal memuat pesan:", error);
    } else if (data && data.length > 0) {
      setMessages(data); // Tampilkan isi pesan ke layar
    } else {
      setMessages([{ role: 'bot', content: 'What can I help you?' }]);
    }
  };

  const handleNewChat = () => {
    setMessages([{ role: 'bot', content: 'What can I help you?' }]);
    setCurrentChatId(null);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    const currentInput = input; 
    setInput('');

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: currentInput }),
      });

      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      const botResponse = data.answer;

      setMessages(prev => [...prev, { role: 'bot', content: botResponse }]);

      let activeChatId = currentChatId;

      // Buat Sesi History baru jika belum ada
      if (!activeChatId) {
        const { data: newChat } = await supabase
          .from('chat_history')
          .insert([
            { 
              user_id: user.id, 
              title: currentInput.substring(0, 30) + (currentInput.length > 30 ? "..." : ""), 
              last_message: botResponse.substring(0, 50) + (botResponse.length > 50 ? "..." : "")
            }
          ])
          .select()
          .single();

        if (newChat) {
          activeChatId = newChat.id;
          setCurrentChatId(activeChatId);
          setHistory(prev => [newChat, ...prev]);
        }
      } else {
        // Update pesan terakhir di sidebar
        await supabase
          .from('chat_history')
          .update({ last_message: botResponse.substring(0, 50) + (botResponse.length > 50 ? "..." : "") })
          .eq('id', activeChatId);
      }

      // SIMPAN DETAIL PESAN KE TABEL chat_messages
      if (activeChatId) {
        await supabase.from('chat_messages').insert([
          { chat_id: activeChatId, role: 'user', content: currentInput },
          { chat_id: activeChatId, role: 'bot', content: botResponse }
        ]);
      }

    } catch (error) {
      console.error("Error calling API:", error);
      setMessages(prev => [...prev, { role: 'bot', content: "Connection error." }]);
    }
  };

  const handleLogout = async () => {
    if (window.confirm("Are you sure you want to log out?")) {
      await supabase.auth.signOut();
      navigate('/');
    }
  };

  return (
    <div className="chat-container">
      <Sidebar
        user={user}
        history={history}
        currentChatId={currentChatId}
        onSelectChat={loadChatSession}
        onNewChat={handleNewChat}
        activePage="chat"
        onCollapsedChange={setIsSidebarCollapsed}
      />

      {/* MAIN CHAT AREA */}
      <main className={`chat-main ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <header className="chat-header">
          <h2>{history.length > 0 && currentChatId ? history.find(h => h.id === currentChatId)?.title : 'New Chat'}</h2>
          <button onClick={handleLogout} className="logout-btn">
            <i className="logout-icon"></i> Logout
          </button>
        </header>

        <section className="messages-area">
          {messages.map((msg, index) => (
            <div key={index} className={`message-row ${msg.role}`}>
              {msg.role === 'bot' && <div className="bot-icon"></div>}
              <div className="message-bubble">
                {msg.content.split('\n').map((line, i) => <p key={i}>{line}</p>)}
              </div>
            </div>
          ))}
          <div ref={scrollRef} />
        </section>

        <footer className="chat-input-area">
          <form onSubmit={handleSendMessage} className="input-wrapper">
            <input 
              type="text" 
              placeholder="Type Your Message Here..." 
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button type="submit" className="send-btn">
              <svg viewBox="0 0 24 24" className="send-icon"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" /></svg>
            </button>
          </form>
        </footer>
      </main>
    </div>
  );
}

export default Chat;
