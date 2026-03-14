import React, { useState } from 'react';
import './ChatWidget.css';

const ChatWidget = () => {
		const [isOpen, setIsOpen] = useState(false);
		const [messages, setMessages] = useState([{ text: "Vanguard Monitor: Ready for IMO risk analysis.", sender: 'bot' }]);
		const [input, setInput] = useState("");

		const handleSend = async () => {
				if (!input.trim()) return;
				const userMsg = { text: input, sender: 'user' };
				setMessages(prev => [...prev, userMsg]);
				setInput("");

				try {
						const res = await fetch('/api/v1/agent-query', {
								method: 'POST',
								headers: { 'Content-Type': 'application/json' },
								body: JSON.stringify({ query: input })
						});
						const data = await res.json();
						setMessages(prev => [...prev, { text: data.response, sender: 'bot' }]);
				} catch (e) {
						setMessages(prev => [...prev, { text: "Error: Could not reach agent.", sender: 'bot' }]);
				}
		};

		return (
				<div className="chat-widget-wrapper">
						{isOpen && (
								<div className="chat-popup-window">
										<div className="chat-header">SignalNexus Agent</div>
										<div className="chat-messages-area">
												{messages.map((m, i) => (
														<div key={i} className={`chat-msg ${m.sender}`}>{m.text}</div>
												))}
										</div>
										<div className="chat-input-bar">
												<input 
														value={input} 
														onChange={(e) => setInput(e.target.value)} 
														onKeyDown={(e) => e.key === 'Enter' && handleSend()} 
														placeholder="Enter IMO..."
												/>
												<button onClick={handleSend}>Send</button>
										</div>
								</div>
						)}
						<button className="chat-fab-button" onClick={() => setIsOpen(!isOpen)}>
								{isOpen ? '✕' : '💬'}
						</button>
				</div>
		);
};

export default ChatWidget;