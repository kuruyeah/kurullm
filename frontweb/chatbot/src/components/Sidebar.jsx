import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../SupabaseClient';
import logoUMB from '../assets/logoumbwhite.webp';

function Sidebar({
  user,
  profile,
  history,
  currentChatId,
  onSelectChat,
  onNewChat,
  activePage = 'chat',
  onCollapsedChange,
}) {
  const navigate = useNavigate();
  const [localUser, setLocalUser] = useState(null);
  const [localHistory, setLocalHistory] = useState([]);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('sidebarCollapsed') === 'true');

  useEffect(() => {
    if (user) return;
    const loadUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setLocalUser(user);
    };

    loadUser();
  }, [user]);

  useEffect(() => {
    if (history) return;

    const loadHistory = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { data, error } = await supabase
        .from('chat_history')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });

      if (!error && data) setLocalHistory(data);
    };

    loadHistory();
  }, [history]);

  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', String(collapsed));
    onCollapsedChange?.(collapsed);
  }, [collapsed, onCollapsedChange]);

  const visibleHistory = history || localHistory;
  const activeUser = user || localUser;
  const displayName = profile?.full_name || activeUser?.user_metadata?.full_name || 'Student';
  const initials = useMemo(() => (
    displayName
      .split(' ')
      .filter(Boolean)
      .map((part) => part[0])
      .join('')
      .slice(0, 2)
      .toUpperCase() || 'AP'
  ), [displayName]);

  const handleNewChat = () => {
    onNewChat?.();
    navigate('/chat');
  };

  const handleHistoryClick = (chatId) => {
    if (onSelectChat) {
      onSelectChat(chatId);
      return;
    }

    navigate('/chat');
  };

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <button
        className="collapse-btn"
        type="button"
        onClick={() => setCollapsed((value) => !value)}
        aria-label={collapsed ? 'Open sidebar' : 'Close sidebar'}
      >
        {collapsed ? '>' : '<'}
      </button>

      <div className="logo-section">
        <img src={logoUMB} alt="UMB Logo" className="umb-logo" />
        <button className="new-chat-btn" onClick={handleNewChat}>+ NEW CHAT</button>
      </div>

      <nav className="chat-history">
        <h3>Chat History</h3>
        {visibleHistory.length === 0 ? (
          <p className="empty-history">No history yet.</p>
        ) : (
          visibleHistory.map((item) => (
            <button
              key={item.id}
              className={`history-item ${currentChatId === item.id ? 'active' : ''}`}
              type="button"
              onClick={() => handleHistoryClick(item.id)}
            >
              <span className="history-title">{item.title}</span>
              <span className="history-time">
                {item.created_at ? new Date(item.created_at).toLocaleDateString() : item.time}
              </span>
            </button>
          ))
        )}
      </nav>

      <div
        className={`user-profile ${activePage === 'profile' ? 'active' : ''}`}
        onClick={() => navigate('/profile')}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === 'Enter') navigate('/profile');
        }}
      >
        <div className="avatar-circle">{initials}</div>

        <div className="user-info">
          <p className="user-name">{displayName}</p>
          <span className="view-profile">View Profile &gt;</span>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
