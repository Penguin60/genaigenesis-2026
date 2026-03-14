import React, { useState } from 'react';
import './ChatWidget.css';

const ChatWidget = () => {
	const [isOpen, setIsOpen] = useState(false);
	const [messages, setMessages] = useState([{ text: "Hello! How can I help with maritime risk today?", sender: 'bot' }]);
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
			setMessages(prev => [...prev, { text: "Error connecting to agent.", sender: 'bot' }]);
		}
	};

	return (
		<div className="chat-widget-container">
			{isOpen && (
				<div className="chat-window">
					<div className="chat-header">SignalNexus Agent</div>
					<div className="chat-body">
						{messages.map((m, i) => (
							<div key={i} className={`message ${m.sender}`}>{m.text}</div>
						))}
					</div>
					<div className="chat-footer">
						<input value={input} onChange={(e) => setInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleSend()} />
						<button onClick={handleSend}>Send</button>
					</div>
				</div>
			)}
			<button className="chat-fab" onClick={() => setIsOpen(!isOpen)}>
				{isOpen ? '✖' : '💬'}
			</button>
		</div>
	);
};

export default ChatWidget;