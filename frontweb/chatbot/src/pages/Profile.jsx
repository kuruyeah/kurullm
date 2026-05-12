import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../SupabaseClient';
import Sidebar from '../components/Sidebar';
import '../styles/chat.css';
import '../styles/profile.css';

function Profile() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  useEffect(() => {
    const fetchProfile = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        navigate('/');
        return;
      }
      setUser(user);

      const { data, error } = await supabase
        .from('users')
        .select('*')
        .eq('id', user.id)
        .single();

      if (data) setProfileData(data);
      if (error) {
        setProfileData({
          full_name: user.user_metadata?.full_name || 'Student',
          email: user.email,
        });
      }
      setLoading(false);
    };
    fetchProfile();
  }, [navigate]);

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

  if (loading) return <div className="loading">Loading Profile...</div>;

  const initials = profileData?.full_name?.split(' ').map(n => n[0]).join('').toUpperCase() || 'AP';

  return (
    <div className="chat-container">
      <Sidebar
        user={user}
        profile={profileData}
        activePage="profile"
        onCollapsedChange={setIsSidebarCollapsed}
      />

      {/* PROFILE CONTENT */}
      <main className={`chat-main ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <header className="chat-header">
          <h2>My Profile</h2>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </header>

        <section className="profile-section">
          <div className="profile-header">
            <div className="profile-avatar-large">{initials}</div>
            <div className="profile-titles">
              <h1>{profileData?.full_name}</h1>
              <p className="profile-id">ID : {profileData?.nim}</p>
            </div>
          </div>

          <div className="profile-grid">
            <div className="info-card">
              <h3>ACADEMIC INFO</h3>
              <div className="field">
                <label>Faculty</label>
                <p>Computer Science</p>
              </div>
              <div className="field">
                <label>Major</label>
                <p>Informatics</p>
              </div>
            </div>

            <div className="info-card">
              <h3>CONTACT DETAILS</h3>
              <div className="field">
                <label>Email</label>
                <p>{profileData?.email}</p>
              </div>
              <div className="field">
                <label>Phone</label>
                <p>{profileData?.phone_number}</p>
              </div>
            </div>
          </div>

          <div className="profile-actions">
            <button className="back-btn" onClick={() => navigate('/chat')}>Back to Chat</button>
            <button className="save-btn">Save Changes</button>
          </div>
        </section>
      </main>
    </div>
  );
}

export default Profile;
