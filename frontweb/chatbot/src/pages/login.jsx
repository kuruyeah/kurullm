import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { supabase } from '../SupabaseClient'; // Path confirmed from your project structure
import ultLogo from '../assets/Logo ULT Warna.webp'; 
import worldBg from '../assets/worldbg.jpg'; 
import '../styles/login.css';

function Login() {
  const [identifier, setIdentifier] = useState(''); // Can be Email or NIM
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    let loginEmail = identifier;

    /**
     * LOGIC: If identifier doesn't contain '@', we treat it as a NIM.
     * We query your 'users' table (based on image_0b642b.png) to find the linked email.
     */
    if (!identifier.includes('@')) {
      const { data, error } = await supabase
        .from('users') // Updated from 'profiles' to your new 'users' table
        .select('email')
        .eq('nim', identifier)
        .single();

      if (error || !data) {
        alert("NIM not found. Please check your ID or use Email.");
        setLoading(false);
        return;
      }
      loginEmail = data.email;
    }

    // Attempt Sign In using Supabase Auth
    const { data, error } = await supabase.auth.signInWithPassword({
      email: loginEmail,
      password: password,
    });

    if (error) {
      alert(error.message);
    } else {
      console.log("Logged in successfully:", data.user);
      navigate('/chat');
    }

    setLoading(false);
  };

  return (
    <div className="login-page" style={{ backgroundImage: `url(${worldBg})` }}>
      <div className="glass-card">
        
        {/* Left Side: Branding */}
        <div className="brand-section">
          <img src={ultLogo} alt="ULT Logo" className="brand-logo-img" />
          <p className="description">
            The Integrated Services Unit is an innovative solution that integrates various campus services into a 
            single system, providing ease, efficiency, and convenience for students, faculty, and staff in accessing 
            administrative, academic, and other services.
          </p>
        </div>

        {/* Right Side: Login Form */}
        <div className="form-section">
          <form onSubmit={handleSubmit} className="login-form">
            <h2 className="form-title">Welcome to the Integrated Services Unit</h2>
            <p className="subtitle">
              Please log in to access the registration services for Thesis Defense and Graduation.
            </p>

            <div className="input-group">
              <label>Email or NIM (ID)</label>
              <input 
                type="text" 
                placeholder="email@example.com or NIM (ID)" 
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            <div className="input-group">
              <label>Password</label>
              <input 
                type="password" 
                placeholder="Enter password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            <div className="form-options">
              <label className="checkbox-container">
                <input type="checkbox" /> Remember me
              </label>
            </div>

            <button type="submit" className="login-button" disabled={loading}>
              {loading ? 'Logging in...' : 'Log in'}
            </button>

            <p className="footer-text">
              Don't have an account? <Link to="/signup">Sign up now</Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Login;