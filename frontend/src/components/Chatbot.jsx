import React, { useState, useEffect, useRef } from 'react';
import './ChatWidget.css';

const Chatbot = () => {
	const [isOpen, setIsOpen] = useState(false);
	const [messages, setMessages] = useState([
		{ text: "Vanguard Monitor: Ask me about vessel insurance or flag status.", sender: 'bot' }
	]);
	const [input, setInput] = useState("");
	const scrollRef = useRef(null);

	useEffect(() => {
		if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
	}, [messages]);

	const handleSend = async () => {
		if (!input.trim()) return;
		const userMsg = { text: input, sender: 'user' };
		setMessages(prev => [...prev, userMsg]);
		setInput("");

		try {
			const response = await fetch('/api/v1/agent-query', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ query: input }),
			});
			const data = await response.json();
			setMessages(prev => [...prev, { text: data.response, sender: 'bot' }]);
		} catch (error) {
			setMessages(prev => [...prev, { text: "Error: Could not reach agent.", sender: 'bot' }]);
		}
	};

	return (
		<div className="chatbot-container">
			{isOpen && (
				<div className="chat-popup">
					<div className="chat-header">
						<strong>SignalNexus Agent</strong>
						<button onClick={() => setIsOpen(false)}>×</button>
					</div>
					<div className="chat-messages" ref={scrollRef}>
						{messages.map((m, i) => (
							<div key={i} className={`msg ${m.sender}`}>{m.text}</div>
						))}
					</div>
					<div className="chat-input">
						<input 
							value={input} 
							onChange={(e) => setInput(e.target.value)} 
							onKeyDown={(e) => e.key === 'Enter' && handleSend()}
							placeholder="IMO number or vessel name..."
						/>
						<button onClick={handleSend}>Send</button>
					</div>
				</div>
			)}
			<button className="chat-fab" onClick={() => setIsOpen(!isOpen)}>
				{isOpen ? '✕' : '💬'}
			</button>
		</div>
	);
};

export default Chatbot;