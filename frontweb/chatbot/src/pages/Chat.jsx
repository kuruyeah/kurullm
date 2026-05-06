import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../SupabaseClient';
import logoUMB from '../assets/logoUMB.png';
import '../styles/chat.css'; // Create this for the specific layout

function Chat() {
  const navigate = useNavigate();
  const scrollRef = useRef(null);
  
  // State
  const [user, setUser] = useState(null);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { role: 'bot', content: 'What can I help you?' }
  ]);
  const [history, setHistory] = useState([
    { id: 1, title: 'Academic Schedule q1', time: '2 hours ago' },
    { id: 2, title: 'How to pay tuition ?', time: '2 Days ago' },
    { id: 3, title: 'What is Mabim', time: '1 Week ago' }
  ]);

  // Load User Data on mount
  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        navigate('/'); // Redirect to login if not authenticated
      } else {
        setUser(user);
      }
    };
    getUser();
  }, [navigate]);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (e) => {
  e.preventDefault();
  if (!input.trim()) return;

  // 1. Add user message to UI immediately
  const userMessage = { role: 'user', content: input };
  setMessages(prev => [...prev, userMessage]);
  const currentInput = input; // Store input before clearing
  setInput('');

  try {
    // 2. Call your FastAPI backend
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: currentInput }),
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const data = await response.json();

    // 3. Add the real bot response from the RAG logic
    setMessages(prev => [...prev, { 
      role: 'bot', 
      content: data.answer 
    }]);

  } catch (error) {
    console.error("Error calling API:", error);
    setMessages(prev => [...prev, { 
      role: 'bot', 
      content: "Sorry, I'm having trouble connecting to the server." 
    }]);
  }
};

  const handleLogout = async () => {
  // Show a confirmation popup
    const confirmLogout = window.confirm("Are you sure you want to log out?");
    
    if (confirmLogout) {
        try {
        await supabase.auth.signOut();
        alert("You have successfully logged out.");
        navigate('/');
        } catch (error) {
        console.error("Error logging out:", error.message);
        alert("Error logging out. Please try again.");
        }
      }
    };

  return (
    <div className="chat-container">
      {/* LEFT SIDEBAR */}
      <aside className="sidebar">
        <div className="logo-section">
          <img src={logoUMB} alt="UMB Logo" className="umb-logo" />
          <button className="new-chat-btn">+ NEW CHAT</button>
        </div>

        <nav className="chat-history">
          <h3>Chat History</h3>
          {history.map(item => (
            <div key={item.id} className="history-item">
              <p className="history-title">{item.title}</p>
              <span className="history-time">{item.time}</span>
            </div>
          ))}
        </nav>

        <div className="user-profile" onClick={() => navigate('/profile')} style={{ cursor: 'pointer' }}>
          <div className="avatar-circle">
            {user?.user_metadata?.full_name?.split(' ').map(n => n[0]).join('').toUpperCase() || 'AP'}
          </div>
          <div className="user-info">
            <p className="user-name">{user?.full_name}</p>
            <span className="view-profile">View Profile &gt;</span>
          </div>
        </div>
      </aside>

      {/* MAIN CHAT AREA */}
      <main className="chat-main">
        <header className="chat-header">
          <h2>How to pay tuition?</h2>
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
              <svg viewBox="0 0 24 24" className="send-icon">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </form>
        </footer>
      </main>
    </div>
  );
}

export default Chat;