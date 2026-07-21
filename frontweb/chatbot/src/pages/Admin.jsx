import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { supabase } from "../SupabaseClient";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import { Users, MessageSquare, Clock, Star, LogOut, UploadCloud, FileText, CheckCircle2 } from 'lucide-react';

import "../styles/admin.css";

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'];

function AdminPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Dashboard Metrics
  const [metrics, setMetrics] = useState({
    totalSessions: 0,
    activeUsers: 0,
    avgDuration: "0m 0s",
    csatScore: "0.0",
    fallbackRate: 0,
    handoverRate: 0,
    avgResponseTime: 0
  });

  const [chartData, setChartData] = useState([]);
  const [csatData, setCsatData] = useState([]);
  const [failedQuestions, setFailedQuestions] = useState([]);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // 1. Fetch Chat History (Sessions & Users)
      const { data: historyData, error: historyError } = await supabase.from('chat_history').select('*');
      
      if (historyError) {
        console.error("Supabase Error fetching chat_history:", historyError);
      } else {
        console.log("Fetched chat_history:", historyData?.length, "rows");
      }
      
      let totalSessions = 0;
      let uniqueUsers = new Set();
      let totalDurationMs = 0;
      let sessionsWithDuration = 0;

      if (historyData && historyData.length > 0) {
        totalSessions = historyData.length;
        historyData.forEach(session => {
          uniqueUsers.add(session.user_id);
          
          // Calculate duration if updated_at exists
          if (session.updated_at && session.created_at) {
            const start = new Date(session.created_at);
            const end = new Date(session.updated_at);
            const durationMs = end - start;
            
            // Filter out anomalous data (e.g. > 24 hours) caused by the recent schema update
            if (durationMs > 0 && durationMs < 86400000) {
              totalDurationMs += durationMs;
              sessionsWithDuration++;
            }
          }
        });
      }

      const activeUsers = uniqueUsers.size;
      const avgDurationMs = sessionsWithDuration > 0 ? totalDurationMs / sessionsWithDuration : 0;
      
      let formattedDuration = "0s";
      if (avgDurationMs > 0) {
        const hours = Math.floor(avgDurationMs / 3600000);
        const minutes = Math.floor((avgDurationMs % 3600000) / 60000);
        const seconds = Math.floor((avgDurationMs % 60000) / 1000);
        
        if (hours > 0) {
          formattedDuration = `${hours}h ${minutes}m`;
        } else if (minutes > 0) {
          formattedDuration = `${minutes}m ${seconds}s`;
        } else {
          formattedDuration = `${seconds}s`;
        }
      }

      // 2. Fetch Chat Messages for deep dive analytics
      const { data: messagesData, error: messagesError } = await supabase.from('chat_messages').select('*');
      
      if (messagesError) {
        console.error("Supabase Error fetching chat_messages:", messagesError);
      } else {
        console.log("Fetched chat_messages:", messagesData?.length, "rows");
      }
      
      let totalRatings = 0;
      let ratingCount = 0;
      let fallbacks = 0;
      let handovers = 0;
      let totalResponseTime = 0;
      let botMessagesCount = 0;
      
      let hourCounts = Array(24).fill(0);
      let csatDistribution = { 'Very Satisfied': 0, 'Satisfied': 0, 'Neutral': 0, 'Dissatisfied': 0, 'Very Dissatisfied': 0 };
      let failedQMap = {};

      if (messagesData && messagesData.length > 0) {
        messagesData.forEach(msg => {
          // Time volume mapping
          const hour = new Date(msg.created_at).getHours();
          hourCounts[hour]++;

          if (msg.role === 'bot') {
            botMessagesCount++;
            if (msg.is_fallback) {
              fallbacks++;
              // Track failed questions
              const reason = msg.fallback_reason || 'Out of domain';
              if (failedQMap[reason]) {
                failedQMap[reason].frequency++;
              } else {
                failedQMap[reason] = { 
                  question: "Simulated Failed Q (Needs User Msg link)", 
                  frequency: 1, 
                  reason: reason 
                };
              }
            }
            if (msg.is_handover) handovers++;
            if (msg.response_time_ms) totalResponseTime += msg.response_time_ms;
            
            // CSAT Calculation
            if (msg.rating > 0) {
              totalRatings += msg.rating;
              ratingCount++;
              
              if (msg.rating === 5) csatDistribution['Very Satisfied']++;
              else if (msg.rating === 4) csatDistribution['Satisfied']++;
              else if (msg.rating === 3) csatDistribution['Neutral']++;
              else if (msg.rating === 2) csatDistribution['Dissatisfied']++;
              else if (msg.rating === 1) csatDistribution['Very Dissatisfied']++;
            }
          }
        });
      }

      // Final Metric Calculations
      const csatScore = ratingCount > 0 ? (totalRatings / ratingCount).toFixed(1) : "0.0";
      const fallbackRate = botMessagesCount > 0 ? Math.round((fallbacks / botMessagesCount) * 100) : 0;
      const handoverRate = botMessagesCount > 0 ? Math.round((handovers / botMessagesCount) * 100) : 0;
      const avgResponseTime = botMessagesCount > 0 ? Math.round(totalResponseTime / botMessagesCount) : 0;

      // Format Chart Data
      const formattedChartData = hourCounts.map((count, index) => ({
        time: `${index.toString().padStart(2, '0')}:00`,
        volume: count
      }));

      const formattedCsatData = [
        { name: 'Very Satisfied', value: csatDistribution['Very Satisfied'] },
        { name: 'Satisfied', value: csatDistribution['Satisfied'] },
        { name: 'Neutral', value: csatDistribution['Neutral'] },
        { name: 'Dissatisfied', value: csatDistribution['Dissatisfied'] + csatDistribution['Very Dissatisfied'] },
      ].filter(item => item.value > 0);

      // Default fallback data if none exists
      if (formattedCsatData.length === 0) {
        formattedCsatData.push({ name: 'No Data', value: 1 });
      }

      const formattedFailedQuestions = Object.values(failedQMap).sort((a, b) => b.frequency - a.frequency).slice(0, 5);

      setMetrics({
        totalSessions,
        activeUsers,
        avgDuration: formattedDuration,
        csatScore,
        fallbackRate,
        handoverRate,
        avgResponseTime
      });
      
      setChartData(formattedChartData);
      setCsatData(formattedCsatData);
      setFailedQuestions(formattedFailedQuestions);

    } catch (err) {
      console.error("Error fetching dashboard data:", err);
    }
  };

  const handleLogout = async () => {
    if (window.confirm("Are you sure you want to log out?")) {
      await supabase.auth.signOut();
      localStorage.removeItem('userRole');
      navigate('/');
    }
  };

  const handleFileUpload = async () => {
    if (!file) {
      alert("Please choose a file first.");
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      // Connects to Python Backend for immediate embedding
      await axios.post("http://127.0.0.1:8000/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      alert("Regulation uploaded & embedded successfully!");
      setFile(null);
    } catch (err) {
      console.error("Upload Error:", err);
      alert("Error during file upload.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="admin-layout">
      <main className="admin-main">
        
        {/* Header */}
        <header className="admin-header">
          <div className="header-title">
            <h1>Analytics Overview</h1>
            <p>Monitor your chatbot's performance and knowledge base.</p>
          </div>
          <div className="header-actions">
            <div className="admin-profile">
              <div className="admin-avatar">AD</div>
              <div className="admin-info">
                <h3>Administrator</h3>
                <p>System Admin</p>
              </div>
            </div>
            <button className="btn-logout" onClick={handleLogout}>
              <LogOut size={18} /> Logout
            </button>
          </div>
        </header>

        {metrics.totalSessions === 0 && (
          <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', padding: '1rem', borderRadius: '0.5rem', marginBottom: '1.5rem', color: '#ef4444' }}>
            <strong>⚠️ No Data Found:</strong> Your Supabase tables are either completely empty, or Row Level Security (RLS) is blocking the admin from reading the data. Send a test message in the chatbot first, and if it still doesn't show up, check your Supabase RLS policies.
          </div>
        )}

        {/* Executive Overview */}
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-header">
              <h3 className="metric-title">Total Sessions</h3>
              <div className="metric-icon-wrapper blue"><MessageSquare size={20} /></div>
            </div>
            <p className="metric-value">{metrics.totalSessions}</p>
            <div className="metric-badge positive">+12% from last month</div>
          </div>

          <div className="metric-card">
            <div className="metric-header">
              <h3 className="metric-title">Active Users</h3>
              <div className="metric-icon-wrapper green"><Users size={20} /></div>
            </div>
            <p className="metric-value">{metrics.activeUsers}</p>
            <div className="metric-badge neutral">Current active</div>
          </div>

          <div className="metric-card">
            <div className="metric-header">
              <h3 className="metric-title">Average Duration</h3>
              <div className="metric-icon-wrapper purple"><Clock size={20} /></div>
            </div>
            <p className="metric-value">{metrics.avgDuration}</p>
            <div className="metric-badge neutral">Per session</div>
          </div>

          <div className="metric-card">
            <div className="metric-header">
              <h3 className="metric-title">CSAT Score</h3>
              <div className="metric-icon-wrapper orange"><Star size={20} /></div>
            </div>
            <p className="metric-value">{metrics.csatScore}</p>
            <div className="metric-badge positive">Excellent</div>
          </div>
        </div>

        {/* Main Analytics & Bot Quality */}
        <div className="charts-grid">
          <div className="chart-card">
            <div className="chart-header">
              <h3>Peak Activity Time</h3>
              <p>Chat volume distribution by hour</p>
            </div>
            <div className="area-chart-wrapper">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} />
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <RechartsTooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}/>
                  <Area type="monotone" dataKey="volume" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorVolume)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="chart-card">
            <div className="chart-header">
              <h3>Bot Quality Analysis</h3>
              <p>Friction & Performance indicators</p>
            </div>
            <div className="quality-metrics">
              
              <div className="quality-item">
                <div className="quality-header">
                  <span>Fallback Rate</span>
                  <span>{metrics.fallbackRate}%</span>
                </div>
                <div className="progress-bar-bg">
                  <div className={`progress-bar-fill ${metrics.fallbackRate > 20 ? 'danger' : 'warning'}`} style={{ width: `${metrics.fallbackRate}%` }}></div>
                </div>
                <span className="quality-target">Target: &lt; 15%</span>
              </div>

              <div className="quality-item">
                <div className="quality-header">
                  <span>Handover Rate</span>
                  <span>{metrics.handoverRate}%</span>
                </div>
                <div className="progress-bar-bg">
                  <div className={`progress-bar-fill ${metrics.handoverRate > 10 ? 'danger' : 'warning'}`} style={{ width: `${metrics.handoverRate}%` }}></div>
                </div>
                <span className="quality-target">Target: &lt; 10%</span>
              </div>

              <div className="speed-metric">
                <div className="speed-value">{metrics.avgResponseTime} <span style={{fontSize: '1rem', color: '#64748b'}}>ms</span></div>
                <div className="speed-status"><div className="dot"></div> Very Fast</div>
                <div className="quality-target" style={{marginTop: '0.2rem'}}>Average Response Speed</div>
              </div>

            </div>
          </div>
        </div>

        {/* Deep Dive Metrics & Upload */}
        <div className="bottom-grid">
          
          <div className="chart-card">
            <div className="chart-header">
              <h3>Top Failed Questions</h3>
              <p>Common questions triggering fallbacks</p>
            </div>
            <div className="table-container">
              <table className="modern-table">
                <thead>
                  <tr>
                    <th>Failed Question</th>
                    <th>Freq.</th>
                    <th>Reason</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {failedQuestions.map((item, idx) => (
                    <tr key={idx}>
                      <td style={{fontWeight: 500}}>{item.question}</td>
                      <td>{item.frequency}</td>
                      <td><span className="reason-badge">{item.reason}</span></td>
                      <td><button className="btn-retrain">Retrain</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="chart-card">
            <div className="chart-header">
              <h3>CSAT Breakdown</h3>
              <p>Satisfaction Distribution</p>
            </div>
            <div className="pie-chart-wrapper">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={csatData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {csatData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                  <Legend verticalAlign="bottom" height={36}/>
                </PieChart>
              </ResponsiveContainer>
            </div>
            
            <div style={{marginTop: '2rem'}}>
               <div className="chart-header">
                  <h3>Knowledge Base</h3>
                  <p>Upload files to retrain bot</p>
               </div>
               <div className="upload-zone">
                  <UploadCloud className="upload-icon" size={40} />
                  <h4>Upload Regulation</h4>
                  <p>Drop file here or click to browse</p>
                  
                  <label className="upload-label">
                    Choose File
                    <input
                      type="file"
                      className="upload-input"
                      accept=".pdf,.doc,.docx,.txt"
                      onChange={(e) => setFile(e.target.files[0])}
                    />
                  </label>
                  
                  {file && (
                    <div className="file-name">
                      <FileText size={16} /> {file.name}
                      <CheckCircle2 size={16} color="#10b981" />
                    </div>
                  )}
               </div>
               
               <button 
                  className="btn-save" 
                  onClick={handleFileUpload} 
                  disabled={!file || uploading}
               >
                 {uploading ? "Processing..." : "Process & Embed Document"}
               </button>
            </div>

          </div>

        </div>

      </main>
    </div>
  );
}

export default AdminPage;