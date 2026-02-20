/**
 * Knowledge Expert - Embeddable Chat Widget
 *
 * Usage:
 * 1. Include this script on your website:
 *    <script src="https://your-domain.com/static/js/widget.js" data-api-key="YOUR_API_KEY"></script>
 *
 * 2. Or initialize manually:
 *    KnowledgeExpert.init({
 *      apiKey: 'YOUR_API_KEY',
 *      apiUrl: 'https://your-domain.com',
 *      position: 'bottom-right',
 *      primaryColor: '#0d6efd',
 *      title: 'Ask us anything!'
 *    });
 */

(function() {
    'use strict';

    // Default configuration
    const defaults = {
        apiKey: null,
        apiUrl: null,  // Will be auto-detected from script src
        position: 'bottom-right', // bottom-right, bottom-left
        primaryColor: '#0d6efd',
        title: 'Knowledge Expert',
        subtitle: 'How can we help you?',
        placeholder: 'Type your question...',
        welcomeMessage: 'Hello! I\'m here to help answer your questions. What would you like to know?',
        buttonIcon: '💬',
        width: '380px',
        height: '500px'
    };

    let config = { ...defaults };
    let isOpen = false;
    let container = null;
    let messagesContainer = null;

    // Styles
    const styles = `
        .ke-widget-container {
            position: fixed;
            z-index: 99999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        }
        .ke-widget-container.bottom-right {
            bottom: 20px;
            right: 20px;
        }
        .ke-widget-container.bottom-left {
            bottom: 20px;
            left: 20px;
        }

        .ke-widget-button {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .ke-widget-button:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 16px rgba(0,0,0,0.2);
        }

        .ke-widget-chat {
            position: absolute;
            bottom: 70px;
            right: 0;
            background: white;
            border-radius: 12px;
            box-shadow: 0 5px 40px rgba(0,0,0,0.16);
            display: none;
            flex-direction: column;
            overflow: hidden;
        }
        .ke-widget-container.bottom-left .ke-widget-chat {
            right: auto;
            left: 0;
        }
        .ke-widget-chat.open {
            display: flex;
        }

        .ke-widget-header {
            padding: 16px;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .ke-widget-header-title {
            font-weight: 600;
            font-size: 16px;
        }
        .ke-widget-header-subtitle {
            font-size: 12px;
            opacity: 0.9;
        }
        .ke-widget-close {
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            opacity: 0.8;
            padding: 0;
            line-height: 1;
        }
        .ke-widget-close:hover {
            opacity: 1;
        }

        .ke-widget-messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            background: #f7f9fc;
        }

        .ke-widget-message {
            margin-bottom: 12px;
            max-width: 85%;
        }
        .ke-widget-message.user {
            margin-left: auto;
        }
        .ke-widget-message-content {
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.4;
        }
        .ke-widget-message.assistant .ke-widget-message-content {
            background: white;
            border: 1px solid #e5e7eb;
        }
        .ke-widget-message.user .ke-widget-message-content {
            color: white;
        }

        .ke-widget-input-container {
            padding: 12px;
            background: white;
            border-top: 1px solid #e5e7eb;
            display: flex;
            gap: 8px;
        }
        .ke-widget-input {
            flex: 1;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 14px;
            outline: none;
        }
        .ke-widget-input:focus {
            border-color: #0d6efd;
        }
        .ke-widget-send {
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            color: white;
            cursor: pointer;
            font-size: 14px;
            transition: opacity 0.2s;
        }
        .ke-widget-send:hover {
            opacity: 0.9;
        }
        .ke-widget-send:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .ke-widget-typing {
            display: flex;
            gap: 4px;
            padding: 10px 14px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            width: fit-content;
        }
        .ke-widget-typing span {
            width: 8px;
            height: 8px;
            background: #9ca3af;
            border-radius: 50%;
            animation: ke-typing 1.4s infinite ease-in-out;
        }
        .ke-widget-typing span:nth-child(1) { animation-delay: -0.32s; }
        .ke-widget-typing span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes ke-typing {
            0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }

        .ke-widget-powered {
            text-align: center;
            padding: 8px;
            font-size: 11px;
            color: #9ca3af;
            background: #f7f9fc;
        }
        .ke-widget-powered a {
            color: #6b7280;
            text-decoration: none;
        }
        .ke-widget-powered a:hover {
            text-decoration: underline;
        }
    `;

    // Initialize the widget
    function init(userConfig = {}) {
        // Merge user config with defaults
        config = { ...defaults, ...userConfig };

        // Auto-detect API URL from script source
        if (!config.apiUrl) {
            const scriptTag = document.querySelector('script[data-api-key]');
            if (scriptTag && scriptTag.src) {
                const url = new URL(scriptTag.src);
                config.apiUrl = url.origin;
            }
        }

        // Get API key from script tag if not provided
        if (!config.apiKey) {
            const scriptTag = document.querySelector('script[data-api-key]');
            if (scriptTag) {
                config.apiKey = scriptTag.getAttribute('data-api-key');
            }
        }

        if (!config.apiKey) {
            console.error('Knowledge Expert Widget: API key is required');
            return;
        }

        // Inject styles
        const styleEl = document.createElement('style');
        styleEl.textContent = styles;
        document.head.appendChild(styleEl);

        // Create widget container
        container = document.createElement('div');
        container.className = `ke-widget-container ${config.position}`;
        container.innerHTML = createWidgetHTML();
        document.body.appendChild(container);

        // Get references
        messagesContainer = container.querySelector('.ke-widget-messages');

        // Bind events
        bindEvents();

        // Add welcome message
        addMessage(config.welcomeMessage, 'assistant');
    }

    function createWidgetHTML() {
        return `
            <div class="ke-widget-chat" style="width: ${config.width}; height: ${config.height};">
                <div class="ke-widget-header" style="background: ${config.primaryColor};">
                    <div>
                        <div class="ke-widget-header-title">${escapeHtml(config.title)}</div>
                        <div class="ke-widget-header-subtitle">${escapeHtml(config.subtitle)}</div>
                    </div>
                    <button class="ke-widget-close">&times;</button>
                </div>
                <div class="ke-widget-messages"></div>
                <div class="ke-widget-input-container">
                    <input type="text" class="ke-widget-input" placeholder="${escapeHtml(config.placeholder)}">
                    <button class="ke-widget-send" style="background: ${config.primaryColor};">Send</button>
                </div>
                <div class="ke-widget-powered">
                    Powered by <a href="https://matthewcarlsonconsulting.com" target="_blank">Knowledge Expert</a>
                </div>
            </div>
            <button class="ke-widget-button" style="background: ${config.primaryColor};">
                ${config.buttonIcon}
            </button>
        `;
    }

    function bindEvents() {
        // Toggle chat
        const button = container.querySelector('.ke-widget-button');
        const chat = container.querySelector('.ke-widget-chat');
        const closeBtn = container.querySelector('.ke-widget-close');
        const input = container.querySelector('.ke-widget-input');
        const sendBtn = container.querySelector('.ke-widget-send');

        button.addEventListener('click', () => {
            isOpen = !isOpen;
            chat.classList.toggle('open', isOpen);
            if (isOpen) {
                input.focus();
            }
        });

        closeBtn.addEventListener('click', () => {
            isOpen = false;
            chat.classList.remove('open');
        });

        // Send message
        const sendMessage = () => {
            const text = input.value.trim();
            if (!text) return;

            addMessage(text, 'user');
            input.value = '';
            sendQuery(text);
        };

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    function addMessage(text, role) {
        const msgEl = document.createElement('div');
        msgEl.className = `ke-widget-message ${role}`;
        msgEl.innerHTML = `
            <div class="ke-widget-message-content" ${role === 'user' ? `style="background: ${config.primaryColor};"` : ''}>
                ${formatMessage(text)}
            </div>
        `;
        messagesContainer.appendChild(msgEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return msgEl;
    }

    function showTyping() {
        const typingEl = document.createElement('div');
        typingEl.className = 'ke-widget-message assistant';
        typingEl.id = 'ke-typing-indicator';
        typingEl.innerHTML = `
            <div class="ke-widget-typing">
                <span></span><span></span><span></span>
            </div>
        `;
        messagesContainer.appendChild(typingEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function hideTyping() {
        const typingEl = document.getElementById('ke-typing-indicator');
        if (typingEl) {
            typingEl.remove();
        }
    }

    async function sendQuery(text) {
        const sendBtn = container.querySelector('.ke-widget-send');
        const input = container.querySelector('.ke-widget-input');

        sendBtn.disabled = true;
        input.disabled = true;
        showTyping();

        try {
            const response = await fetch(`${config.apiUrl}/api/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${config.apiKey}`
                },
                body: JSON.stringify({ query: text })
            });

            const data = await response.json();

            hideTyping();

            if (response.ok) {
                addMessage(data.response, 'assistant');
            } else {
                addMessage(data.error || 'Sorry, something went wrong. Please try again.', 'assistant');
            }
        } catch (error) {
            hideTyping();
            addMessage('Sorry, I couldn\'t connect to the server. Please try again later.', 'assistant');
            console.error('Knowledge Expert Widget Error:', error);
        } finally {
            sendBtn.disabled = false;
            input.disabled = false;
            input.focus();
        }
    }

    function formatMessage(text) {
        // Simple markdown-like formatting
        return escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Expose public API
    window.KnowledgeExpert = {
        init: init,
        open: () => {
            if (container) {
                isOpen = true;
                container.querySelector('.ke-widget-chat').classList.add('open');
            }
        },
        close: () => {
            if (container) {
                isOpen = false;
                container.querySelector('.ke-widget-chat').classList.remove('open');
            }
        }
    };

    // Auto-initialize if script has data-api-key attribute
    document.addEventListener('DOMContentLoaded', () => {
        const scriptTag = document.querySelector('script[data-api-key]');
        if (scriptTag) {
            init();
        }
    });
})();
