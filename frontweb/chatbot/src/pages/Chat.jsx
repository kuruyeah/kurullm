import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../SupabaseClient';
import Sidebar from '../components/Sidebar';
import '../styles/chat.css';

const StarRating = ({ onRate, initialRating = 0 }) => {
  const [rating, setRating] = useState(initialRating);
  const [hover, setHover] = useState(0);
  const [submitted, setSubmitted] = useState(initialRating > 0);

  const handleSubmit = () => {
    if (rating > 0 && !submitted) {
      onRate(rating);
      setSubmitted(true);
    }
  };

  return (
    <div className="star-rating-wrapper">
      <div className="star-rating">
        {[...Array(5)].map((star, index) => {
          index += 1;
          return (
            <button
              type="button"
              key={index}
              className={index <= (hover || rating) ? "star on" : "star off"}
              onClick={() => {
                if (!submitted) setRating(index);
              }}
              onMouseEnter={() => { if (!submitted) setHover(index); }}
              onMouseLeave={() => { if (!submitted) setHover(rating); }}
              disabled={submitted}
              style={{ cursor: submitted ? 'default' : 'pointer' }}
            >
              <span className="star-char">★</span>
            </button>
          );
        })}
      </div>
      {!submitted && rating > 0 && (
        <button className="submit-rating-btn" onClick={handleSubmit}>Submit</button>
      )}
      {submitted && <span className="submitted-text">Thank you!</span>}
    </div>
  );
};

function Chat() {
  const navigate = useNavigate();
  const scrollRef = useRef(null);
  
  const [user, setUser] = useState(null);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { role: 'bot', content: 'What can I help you?', isGreeting: true }
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
      .select('id, role, content, rating')
      .eq('chat_id', chatId)
      .order('created_at', { ascending: true });

    if (error) {
      console.error("Gagal memuat pesan:", error);
    } else if (data && data.length > 0) {
      setMessages(data); // Tampilkan isi pesan ke layar
    } else {
      setMessages([{ role: 'bot', content: 'What can I help you?', isGreeting: true }]);
    }
  };

  const handleNewChat = () => {
    setMessages([{ role: 'bot', content: 'What can I help you?', isGreeting: true }]);
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
      const startTime = performance.now();
      
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: currentInput }),
      });

      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      const endTime = performance.now();
      
      const botResponse = data.answer;
      const responseTimeMs = Math.round(endTime - startTime);
      
      // Basic fallback detection (you can improve this based on your bot's exact error phrasing)
      const fallbackKeywords = ["maaf", "tidak tahu", "don't know", "sorry", "cannot answer"];
      const lowerResponse = botResponse.toLowerCase();
      const isFallback = fallbackKeywords.some(keyword => lowerResponse.includes(keyword));
      const fallbackReason = isFallback ? "Bot apologized or didn't know the answer" : null;

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
        // Update pesan terakhir di sidebar dan updated_at
        await supabase
          .from('chat_history')
          .update({ 
            last_message: botResponse.substring(0, 50) + (botResponse.length > 50 ? "..." : ""),
            updated_at: new Date().toISOString()
          })
          .eq('id', activeChatId);
      }

      // SIMPAN DETAIL PESAN KE TABEL chat_messages
      if (activeChatId) {
        const { data: insertedMsg, error: insertError } = await supabase.from('chat_messages').insert([
          { chat_id: activeChatId, role: 'user', content: currentInput },
          { 
            chat_id: activeChatId, 
            role: 'bot', 
            content: botResponse,
            response_time_ms: responseTimeMs,
            is_fallback: isFallback,
            fallback_reason: fallbackReason
          }
        ]).select();

        if (insertError) {
          console.error("Gagal menyimpan pesan:", insertError);
        } else if (insertedMsg && insertedMsg.length > 0) {
          const botMsgDb = insertedMsg.find(m => m.role === 'bot');
          if (botMsgDb) {
            // Update state messages agar pesan bot yang baru saja dibuat memiliki ID dari database
            setMessages(prev => {
              const newMsgs = [...prev];
              for (let i = newMsgs.length - 1; i >= 0; i--) {
                if (newMsgs[i].role === 'bot' && !newMsgs[i].id) {
                  newMsgs[i].id = botMsgDb.id;
                  break;
                }
              }
              return newMsgs;
            });
          }
        }
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
              <div className="message-wrapper">
                <div className="message-bubble">
                  {msg.content.split('\n').map((line, i) => <p key={i}>{line}</p>)}
                </div>
                {msg.role === 'bot' && !msg.isGreeting && (
                  <div className="feedback-container">
                    <span className="feedback-text">How helpful was this?</span>
                    <StarRating 
                      initialRating={msg.rating || 0}
                      onRate={async (rating) => {
                      if (msg.id) {
                        const { error } = await supabase
                          .from('chat_messages')
                          .update({ rating: rating })
                          .eq('id', msg.id);
                        
                        if (error) {
                          console.error("Error updating rating:", error);
                        } else {
                          console.log(`Saved rating ${rating} for bot message ${msg.id}`);
                        }
                      } else {
                        console.warn("Message ID not found, cannot save rating yet.");
                      }
                    }} />
                  </div>
                )}
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
