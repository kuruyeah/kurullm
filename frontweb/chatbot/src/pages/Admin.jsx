import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import Calendar from "react-calendar";
import { supabase } from "../SupabaseClient";

// Styles and Assets
import "../styles/admin.css";
import "react-calendar/dist/Calendar.css";

/**
 * AdminPage Component
 * Handles dashboard metrics, category management, and file uploads.
 */
function AdminPage() {
  const navigate = useNavigate();
  const [category, setCategory] = useState("");
  const [file, setFile] = useState(null);

  // --- Metrics State ---
  const [metrics, setMetrics] = useState({
    totalSessions: 0,
    activeUsers: 0,
    resolutionRate: "0%",
    fallbackRate: "0%",
    avgResponseTime: "0s",
    csatScore: "0.0"
  });

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const { count: sessionCount } = await supabase
          .from('chat_history')
          .select('*', { count: 'exact', head: true });
        
        const { count: userCount } = await supabase
          .from('users')
          .select('*', { count: 'exact', head: true });

        setMetrics({
          totalSessions: sessionCount || 124,
          activeUsers: userCount || 42,
          resolutionRate: "85%",   
          fallbackRate: "15%",     
          avgResponseTime: "1.2s", 
          csatScore: "4.7"         
        });

      } catch (err) {
        console.error("Error fetching metrics:", err);
      }
    };
    fetchMetrics();
  }, []);

  // --- API Handlers ---

  const handleLogout = async () => {
    if (window.confirm("Are you sure you want to log out?")) {
      await supabase.auth.signOut();
      localStorage.removeItem('userRole');
      navigate('/');
    }
  };

  const addCategory = async () => {
    if (!category.trim()) {
      alert("Please enter a category name.");
      return;
    }
    try {
      await axios.post("http://127.0.0.1:8000/category", { name: category });
      alert("Category added successfully!");
      setCategory(""); 
    } catch (err) {
      console.error("Category Error:", err);
      alert("Failed to add category.");
    }
  };

  const uploadFile = async () => {
    if (!file) {
      alert("Please choose a file first.");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    try {
      await axios.post("http://127.0.0.1:8000/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      alert("Uploaded successfully!");
      setFile(null);
    } catch (err) {
      console.error("Upload Error:", err);
      alert("Error during file upload.");
    }
  };

  return (
    <div className="admin">
      <header className="header">
        <div>
          <h2>Admin Dashboard</h2>
          <p className="admin-subtitle">Pantau performa dan matrik interaksi chatbot Anda.</p>
        </div>
        <div className="logout" style={{ cursor: "pointer" }} onClick={handleLogout}>
          🔓 Logout
        </div>
      </header>

      <main className="main admin-main-layout">
        
        {/* TOP PANEL: METRICS DASHBOARD */}
        <section className="metrics-dashboard">
          
          <div className="metric-card gradient-1">
            <div className="metric-icon">👥</div>
            <div className="metric-info">
              <h3>{metrics.totalSessions} / {metrics.activeUsers}</h3>
              <p>Total Sesi & Pengguna Aktif</p>
              <small>Interaksi unik bulanan</small>
            </div>
          </div>

          <div className="metric-card gradient-2">
            <div className="metric-icon">✅</div>
            <div className="metric-info">
              <h3>{metrics.resolutionRate}</h3>
              <p>Tingkat Resolusi</p>
              <small>Diselesaikan tanpa agen</small>
            </div>
          </div>

          <div className="metric-card gradient-3">
            <div className="metric-icon">⚠️</div>
            <div className="metric-info">
              <h3>{metrics.fallbackRate}</h3>
              <p>Tingkat Kegagalan</p>
              <small>Memicu pesan error/agen</small>
            </div>
          </div>

          <div className="metric-card gradient-4">
            <div className="metric-icon">⚡</div>
            <div className="metric-info">
              <h3>{metrics.avgResponseTime}</h3>
              <p>Waktu Respons Rata-Rata</p>
              <small>Kecepatan membalas pesan</small>
            </div>
          </div>

          <div className="metric-card gradient-5">
            <div className="metric-icon">⭐</div>
            <div className="metric-info">
              <h3>{metrics.csatScore} / 5.0</h3>
              <p>Skor Kepuasan (CSAT)</p>
              <small>Umpan balik rata-rata</small>
            </div>
          </div>

        </section>

        <div className="admin-bottom-layout">
          {/* LEFT PANEL */}
          <section className="left">
            <div className="calendar-container">
              <Calendar />
            </div>
          </section>

          {/* RIGHT PANEL */}
          <section className="right">
            <div className="profile">
              <div className="avatar">AD</div>
              <div>
                <h2>Administrator</h2>
                <p className="id">Role: Admin</p>
              </div>
            </div>

            <div className="category">
              <input
                type="text"
                placeholder="⬛ Input Your Category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
              <button onClick={addCategory}>Add</button>
            </div>

            <div className="upload-box">
              <label className="upload-label">
                <input
                  type="file"
                  accept=".pdf,.doc,.docx"
                  onChange={(e) => setFile(e.target.files[0])}
                  style={{ display: "none" }} 
                />
                <div className="upload-content">
                  <div className="plus">+</div>
                  <p>{file ? file.name : "Upload New Regulation"}</p>
                  <small>(Text Based Doc. Ex: PDF, Docs)</small>
                </div>
              </label>
            </div>

            <button className="save-btn" onClick={uploadFile}>
              Save Changes
            </button>
          </section>
        </div>
      </main>
    </div>
  );
}

export default AdminPage;