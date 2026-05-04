import React, { useState, useEffect, useRef } from "react";
import axios from "axios";

function ChatInterface() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const messagesEndRef = useRef(null);
  const apiUrl = process.env.REACT_APP_API_URL || "http://localhost:8000";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!query.trim()) return;
    const userMessage = { role: "user", content: query };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setLoading(true);
    setQuery("");
    try {
      const response = await axios.post(`${apiUrl}/query`, { query });
      const botMessage = {
        role: "assistant",
        content: response.data.answer,
        citations: response.data.citations || []
      };
      setMessages([...newMessages, botMessage]);
    } catch (err) {
      console.error(err);
      const errorMsg = { role: "assistant", content: "Error contacting server. Please check if the services are running." };
      setMessages([...newMessages, errorMsg]);
    }
    setLoading(false);
  };

  const openDocument = async (doc) => {
    try {
      const resp = await axios.get(`${apiUrl}/document/${doc.filename}`, {
        params: { highlight: doc.snippet }
      });
      setSelectedDoc({ ...doc, ...resp.data });
      
      // Give the DOM a moment to render the new content
      setTimeout(() => {
        const mark = document.querySelector('mark');
        if (mark) {
          mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 300);
    } catch (err) {
      console.error(err);
      setSelectedDoc({ ...doc, error: "Failed to load document content from server." });
    }
  };

  const formatMessageContent = (content) => {
    return content.split('\n').map((line, i) => (
      <span key={i}>
        {line}
        <br />
      </span>
    ));
  };

  return (
    <div style={{ 
      display: "flex", 
      height: "85vh", 
      backgroundColor: "#f5f7fb", 
      borderRadius: "12px", 
      overflow: "hidden", 
      boxShadow: "0 8px 30px rgba(0,0,0,0.1)",
      margin: "0 auto",
      maxWidth: "1400px"
    }}>
      {/* Chat panel */}
      <div style={{ 
        flex: "1.5", 
        display: "flex", 
        flexDirection: "column", 
        backgroundColor: "white",
        borderRight: "1px solid #e0e6ed"
      }}>
        <div style={{ padding: "1.5rem", borderBottom: "1px solid #e0e6ed", backgroundColor: "#fff" }}>
          <h3 style={{ margin: 0, color: "#1a202c", fontSize: "1.25rem" }}>Conversation</h3>
        </div>
        
        <div style={{ flex: 1, padding: "1.5rem", overflowY: "auto", display: "flex", flexDirection: "column", gap: "1rem" }}>
          {messages.length === 0 && (
            <div style={{ textAlign: "center", color: "#a0aec0", marginTop: "2rem" }}>
              <p>No messages yet. Start by asking a question!</p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} style={{ 
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "85%",
              display: "flex",
              flexDirection: "column",
              alignItems: msg.role === "user" ? "flex-end" : "flex-start"
            }}>
              <div style={{ 
                fontSize: "0.8rem", 
                fontWeight: "600", 
                color: "#718096", 
                marginBottom: "0.25rem",
                marginLeft: msg.role === "user" ? "0" : "0.5rem",
                marginRight: msg.role === "user" ? "0.5rem" : "0"
              }}>
                {msg.role === "user" ? "You" : "AI Assistant"}
              </div>
              <div style={{ 
                padding: "0.8rem 1.2rem", 
                borderRadius: "18px", 
                backgroundColor: msg.role === "user" ? "#3182ce" : "#edf2f7", 
                color: msg.role === "user" ? "white" : "#2d3748",
                lineHeight: "1.5",
                fontSize: "0.95rem",
                boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
                borderBottomRightRadius: msg.role === "user" ? "4px" : "18px",
                borderBottomLeftRadius: msg.role === "user" ? "18px" : "4px"
              }}>
                {formatMessageContent(msg.content)}
              </div>
              {msg.citations && msg.citations.length > 0 && (
                <div style={{ 
                  marginTop: "0.5rem", 
                  display: "flex", 
                  flexWrap: "wrap", 
                  gap: "0.5rem",
                  paddingLeft: "0.5rem"
                }}>
                  <span style={{ fontSize: "0.75rem", color: "#718096", width: "100%" }}>Sources:</span>
                  {msg.citations.map((c, i) => (
                    <button 
                      key={i} 
                      onClick={() => openDocument(c)} 
                      style={{ 
                        fontSize: "0.75rem", 
                        backgroundColor: "#fff", 
                        border: "1px solid #e2e8f0",
                        borderRadius: "6px",
                        padding: "2px 8px",
                        cursor: "pointer",
                        color: "#3182ce",
                        transition: "all 0.2s"
                      }}
                      onMouseOver={(e) => e.target.style.backgroundColor = "#ebf8ff"}
                      onMouseOut={(e) => e.target.style.backgroundColor = "#fff"}
                    >
                      {c.filename}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div style={{ alignSelf: "flex-start", padding: "0.8rem 1.2rem", backgroundColor: "#edf2f7", borderRadius: "18px", color: "#718096" }}>
              AI Assistant is thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={{ padding: "1.5rem", borderTop: "1px solid #e0e6ed" }}>
          <div style={{ display: "flex", backgroundColor: "#f7fafc", borderRadius: "25px", padding: "0.5rem 1rem", border: "1px solid #e2e8f0" }}>
            <input
              style={{ flex: 1, padding: "0.5rem", border: "none", backgroundColor: "transparent", outline: "none", fontSize: "0.95rem" }}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask a question..."
            />
            <button 
              onClick={handleSend} 
              disabled={loading || !query.trim()} 
              style={{ 
                backgroundColor: "#3182ce", 
                color: "white", 
                border: "none", 
                borderRadius: "50%", 
                width: "35px", 
                height: "35px", 
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                opacity: (loading || !query.trim()) ? 0.6 : 1
              }}
            >
              ➔
            </button>
          </div>
        </div>
      </div>

      {/* Document viewer panel */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", backgroundColor: "#fff" }}>
        <div style={{ padding: "1.5rem", borderBottom: "1px solid #e0e6ed" }}>
          <h3 style={{ margin: 0, color: "#1a202c", fontSize: "1.25rem" }}>Document Viewer</h3>
        </div>
        <div style={{ flex: 1, padding: "1.5rem", overflowY: "auto" }}>
          {selectedDoc ? (
            <div style={{ animation: "fadeIn 0.3s ease-in" }}>
              <div style={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}>
                <span style={{ 
                  backgroundColor: "#ebf8ff", 
                  color: "#3182ce", 
                  padding: "4px 10px", 
                  borderRadius: "6px", 
                  fontSize: "0.8rem", 
                  fontWeight: "600",
                  marginRight: "0.5rem"
                }}>
                  {selectedDoc.type?.toUpperCase() || "DOC"}
                </span>
                <h4 style={{ margin: 0, color: "#2d3748" }}>{selectedDoc.filename}</h4>
              </div>
              
              {selectedDoc.error && (
                <div style={{ padding: "1rem", backgroundColor: "#fff5f5", color: "#c53030", borderRadius: "8px", borderLeft: "4px solid #f56565", marginBottom: "1rem" }}>
                  {selectedDoc.error}
                </div>
              )}
              
              <div style={{ 
                backgroundColor: "#fff", 
                border: "1px solid #e2e8f0", 
                borderRadius: "8px", 
                padding: "1.5rem",
                lineHeight: "1.6",
                fontSize: "0.95rem",
                color: "#4a5568"
              }}>
                {(selectedDoc.type === 'pdf' || selectedDoc.type === 'txt') && selectedDoc.content ? (() => {
                  let html = selectedDoc.content;
                  if (selectedDoc.highlight) {
                    const escaped = selectedDoc.highlight.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    const regex = new RegExp(`(${escaped})`, 'gi');
                    html = html.replace(regex, '<mark style="background-color: #fefcbf; padding: 2px; border-radius: 2px; border-bottom: 2px solid #ecc94b;">$1</mark>');
                  }
                  return <div style={{ whiteSpace: 'pre-wrap' }} dangerouslySetInnerHTML={{ __html: html }} />;
                })() : (
                  <p style={{ fontStyle: "italic", color: "#718096" }}>
                    {selectedDoc.snippet || "No preview available for this document type."}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div style={{ 
              height: "100%", 
              display: "flex", 
              flexDirection: "column", 
              alignItems: "center", 
              justifyContent: "center", 
              color: "#a0aec0",
              textAlign: "center"
            }}>
              <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>📄</div>
              <p>Select a source from the chat<br />to view the document details here.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatInterface;
