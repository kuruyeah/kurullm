import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { supabase } from '../SupabaseClient'; 
import { useModal } from '../components/ModalContext';
import worldBg from '../assets/worldbg.jpg'; 
import '../styles/login.css';

function Signup() {
  const navigate = useNavigate();
  const { showAlert } = useModal();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    nim: '',
    nama: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
    agree: false
  });

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleCheckNIM = async () => {
    if (!formData.nim) {
      return showAlert("Please enter a NIM first.", {
        title: "NIM Required",
        variant: "warning"
      });
    }
    
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from('users') 
        .select('full_name, email, phone_number, is_registered')
        .eq('nim', formData.nim) 
        .single();

      if (error || !data) {
        await showAlert("NIM not found. Ensure the NIM is pre-registered in the database.", {
          title: "NIM Not Found",
          variant: "warning"
        });
      } else if (data.is_registered) {
        await showAlert("This NIM is already registered. Please login instead.", {
          title: "Already Registered",
          variant: "info"
        });
      } else {
        setFormData(prev => ({
          ...prev,
          nama: data.full_name || '',
          email: data.email || '',
          phone: data.phone_number || ''
        }));
        await showAlert("NIM Verified! Information autofilled.", {
          title: "NIM Verified",
          variant: "success"
        });
      }
    } catch (err) {
      await showAlert("Error checking NIM.", {
        title: "Error",
        variant: "danger"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.password !== formData.confirmPassword) {
      return showAlert("Passwords do not match!", {
        title: "Password Mismatch",
        variant: "warning"
      });
    }
    if (!formData.agree) {
      return showAlert("Please check the 'Data already correct' box.", {
        title: "Confirmation Needed",
        variant: "warning"
      });
    }

    setLoading(true);

    try {
      // 1. Sign up for Supabase Auth
      // We pass the raw password; Supabase hashes it automatically in their 'auth' schema
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email: formData.email,
        password: formData.password,
        options: {
          emailRedirectTo: window.location.origin, 
          data: {
            full_name: formData.nama,
            nim: formData.nim
          }
        }
      });

      if (authError) throw authError;

      // 2. Update your custom 'users' table
      // We use .update() instead of .upsert() because the record MUST already exist.
      const { error: dbError } = await supabase
        .from('users')
        .update({
          full_name: formData.nama,
          email: formData.email,
          phone_number: formData.phone,
          is_registered: true // Mark as registered so they can't sign up twice
        })
        .eq('nim', formData.nim);

      if (dbError) throw dbError;

      await showAlert("Please check your email (" + formData.email + ") for a confirmation link.", {
        title: "Registration Successful!",
        variant: "success"
      });
      navigate('/');

    } catch (err) {
      console.error("Full error details:", err);
      await showAlert(err.message || "An error occurred", {
        title: "Registration Error",
        variant: "danger"
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page" style={{ backgroundImage: `url(${worldBg})` }}>
      <div className="glass-card signup-card">
        <div className="form-section full-width">
          <form onSubmit={handleSubmit} className="login-form">
            <h2 className="form-title">Student Register</h2>
            <p className="subtitle">
              Already have account? <Link to="/" className="link-text">Login</Link>
            </p>

            <div className="input-group">
              <label>NIM/ID</label>
              <div className="input-with-button" style={{ display: 'flex', gap: '10px' }}>
                <input 
                  type="text" 
                  name="nim" 
                  placeholder="Enter NIM/ID" 
                  value={formData.nim} 
                  onChange={handleChange} 
                  required 
                />
                <button 
                  type="button" 
                  className="check-button" 
                  onClick={handleCheckNIM} 
                  disabled={loading}
                >
                  Check NIM
                </button>
              </div>
            </div>

            <div className="input-group">
              <label>Name</label>
              <input 
                type="text" 
                name="nama" 
                placeholder="Name" 
                value={formData.nama} 
                onChange={handleChange} 
                required 
              />
            </div>

            <div className="input-group">
              <label>Email</label>
              <input 
                type="email" 
                name="email" 
                placeholder="email@email.com" 
                value={formData.email} 
                onChange={handleChange} 
                required 
              />
            </div>

            <div className="input-group">
              <label>Phone Number</label>
              <input 
                type="text" 
                name="phone" 
                placeholder="08xxxxxxxx" 
                value={formData.phone} 
                onChange={handleChange} 
                required 
              />
            </div>

            <div className="input-group">
              <label>Password</label>
              <input 
                type="password" 
                name="password" 
                placeholder="Enter Password" 
                value={formData.password} 
                onChange={handleChange} 
                required 
              />
            </div>

            <div className="input-group">
              <label>Confirm Password</label>
              <input 
                type="password" 
                name="confirmPassword" 
                placeholder="Confirm Password" 
                value={formData.confirmPassword} 
                onChange={handleChange} 
                required 
              />
            </div>

            <div className="form-options">
              <label className="checkbox-container">
                <input 
                  type="checkbox" 
                  name="agree" 
                  checked={formData.agree} 
                  onChange={handleChange} 
                  required 
                /> Data already correct
              </label>
            </div>

            <button type="submit" className="login-button signup-submit" disabled={loading}>
              {loading ? 'Processing...' : 'Daftar'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Signup;