import React, { useState } from "react";
import axios from "axios";

function ChatInterface() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const apiUrl = process.env.REACT_APP_API_URL || "http://localhost:8000";

  const handleSend = async () => {
    if (!query.trim()) return;
    const userMessage = { role: "user", content: query };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setLoading(true);
    try {
      const response = await axios.post(
        `${process.env.REACT_APP_API_URL || "http://localhost:8000"}/query`,
        { query }
      );
      const botMessage = {
        role: "assistant",
        content: response.data.answer,
        citations: response.data.citations || []
      };
      setMessages([...newMessages, botMessage]);
    } catch (err) {
      console.error(err);
      const errorMsg = { role: "assistant", content: "Error contacting server." };
      setMessages([...newMessages, errorMsg]);
    }
    setLoading(false);
    setQuery("");
  };

  const openDocument = async (doc) => {
    try {
      const resp = await axios.get(`${apiUrl}/document/${doc.filename}`, {
        params: { highlight: doc.snippet }
      });
      setSelectedDoc({ ...doc, ...resp.data });
    } catch (err) {
      console.error(err);
      setSelectedDoc({ ...doc, error: "Failed to load document" });
    }
  };

  // Upload functionality removed – documents are processed automatically on server startup

  return (
    <div style={{ display: "flex", height: "80vh", border: "1px solid #ccc" }}>
      {/* Chat panel */}
      <div style={{ flex: 1, padding: "1rem", overflowY: "auto" }}>
        <h3>Chat</h3>
        <div style={{ marginBottom: "1rem" }}>
          {messages.map((msg, idx) => (
            <div key={idx} style={{ marginBottom: "0.5rem" }}>
              <strong>{msg.role === "user" ? "You" : "Bot"}:</strong> {msg.content}
              {msg.citations && msg.citations.length > 0 && (
                <div style={{ fontSize: "0.9em", color: "#555" }}>
                  Sources: {msg.citations.map((c, i) => (
                    <span key={i} onClick={() => openDocument(c)} style={{ cursor: "pointer", textDecoration: "underline", marginRight: "0.5rem" }}>
                      {c.filename}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && <div>Loading...</div>}
        </div>
        {/* Upload functionality removed – documents are processed automatically on server startup */}
        <div style={{ display: "flex" }}>
          <input
            style={{ flex: 1, padding: "0.5rem" }}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask a question about your documents..."
          />
          <button onClick={handleSend} disabled={loading} style={{ marginLeft: "0.5rem" }}>
            Send
          </button>
        </div>
      </div>

      {/* Document viewer panel */}
      <div style={{ flex: 1, padding: "1rem", borderLeft: "1px solid #ccc", overflowY: "auto" }}>
        <h3>Document Viewer</h3>
        {selectedDoc ? (
          <div>
            <h4>{selectedDoc.filename}</h4>
            {selectedDoc.error && <p style={{color: 'red'}}>{selectedDoc.error}</p>}
            {(selectedDoc.type === 'pdf' || selectedDoc.type === 'txt') && selectedDoc.content && (() => {
              let html = selectedDoc.content;
              if (selectedDoc.highlight) {
                const escaped = selectedDoc.highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const regex = new RegExp(`(${escaped})`, 'gi');
                html = selectedDoc.content.replace(regex, '<mark>$1</mark>');
              }
              return <div style={{whiteSpace: 'pre-wrap', maxHeight: '500px', overflow: 'auto'}} dangerouslySetInnerHTML={{__html: html}} />;
            })()}
            {selectedDoc.type === 'docx' && (
              <p>{selectedDoc.message || "DOCX preview not implemented yet."}</p>
            )}
            {/* Fallback for unknown types */}
            {(!selectedDoc.type || selectedDoc.type === 'unknown') && <p>{selectedDoc.snippet}</p>}
          </div>
        ) : (
          <p>Select a document from search results to view it here.</p>
        )}
      </div>
    </div>
  );
}

export default ChatInterface;
