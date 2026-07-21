import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Import your page components
import Login from './pages/login';
import Chat from './pages/Chat';
import Signup from './pages/signup';
import Profile from './pages/Profile';
import Admin from './pages/Admin';

// Protect Admin Route
const AdminRoute = ({ children }) => {
  const role = localStorage.getItem('userRole');
  if (role !== 'admin') {
    // If not admin, restrict access and redirect to chat
    return <Navigate to="/chat" replace />;
  }
  return children;
};

// Protect Standard Routes (ensure user is logged in)
const ProtectedRoute = ({ children }) => {
  const role = localStorage.getItem('userRole');
  if (!role) {
    return <Navigate to="/" replace />;
  }
  return children;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        
        <Route path="/chat" element={
          <ProtectedRoute>
            <Chat />
          </ProtectedRoute>
        } />
        
        <Route path="/profile" element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        } />
        
        <Route path="/admin" element={
          <AdminRoute>
            <Admin />
          </AdminRoute>
        } />
      </Routes>
    </Router>
  );
}

export default App;