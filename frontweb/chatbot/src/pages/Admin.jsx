import { useState } from "react";
import axios from "axios";
import Calendar from "react-calendar";

// Styles and Assets
import "../styles/admin.css";
import "react-calendar/dist/Calendar.css";

/**
 * AdminPage Component
 * Handles category management, file uploads, and chat interactions.
 */
function AdminPage() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState("");
  const [category, setCategory] = useState("");
  const [file, setFile] = useState(null);

  // --- API Handlers ---

  // Handle Chat Messaging
  const sendMessage = async () => {
    try {
      const res = await axios.post("http://127.0.0.1:8000/chat", {
        message: message,
      });
      setResponse(res.data.answer);
    } catch (err) {
      console.error("Chat Error:", err);
      alert("Failed to send message.");
    }
  };

  // Handle Adding New Category
  const addCategory = async () => {
    if (!category.trim()) {
      alert("Please enter a category name.");
      return;
    }

    try {
      await axios.post("http://127.0.0.1:8000/category", {
        name: category,
      });
      alert("Category added successfully!");
      setCategory(""); // Clear input on success
    } catch (err) {
      console.error("Category Error:", err);
      alert("Failed to add category.");
    }
  };

  // Handle File Upload
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
      setFile(null); // Reset file input
    } catch (err) {
      console.error("Upload Error:", err);
      alert("Error during file upload.");
    }
  };

  return (
    <div className="admin">
      {/* HEADER */}
      <header className="header">
        <h2>Admin Dashboard</h2>
        <div className="logout" style={{ cursor: "pointer" }}>
          🔓 Logout
        </div>
      </header>

      <main className="main">
        {/* LEFT PANEL */}
        <section className="left">
          <img src={logo} alt="Application Logo" className="logo" />
          <div className="calendar">
            <Calendar />
          </div>
        </section>

        {/* RIGHT PANEL */}
        <section className="right">
          {/* USER PROFILE */}
          <div className="profile">
            <div className="avatar">AE</div>
            <div>
              <h2>Andrew Erlan</h2>
              <p className="id">ID : 41523010047</p>
            </div>
          </div>

          {/* CATEGORY MANAGEMENT */}
          <div className="category">
            <input
              type="text"
              placeholder="⬛ Input Your Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
            <button onClick={addCategory}>Add</button>
          </div>

          {/* UPLOAD BOX */}
          <div className="upload-box">
            <label className="upload-label">
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={(e) => setFile(e.target.files[0])}
                style={{ display: "none" }} // Hide the default ugly button
              />
              <div className="upload-content">
                <div className="plus">+</div>
                <p>{file ? file.name : "Upload New Regulation"}</p>
                <small>(Text Based Doc. Ex: PDF, Docs)</small>
              </div>
            </label>
          </div>

          {/* SAVE BUTTON */}
          <button className="save-btn" onClick={uploadFile}>
            Save Changes
          </button>
        </section>
      </main>
    </div>
  );
}

export default AdminPage;