/**
 * Knowledge Expert - Embeddable Chat Widget
 *
 * Usage:
 *
 * 1. Floating popup (default) - adds a chat button to corner of page:
 *    <script src="https://your-domain.com/static/js/widget.js"
 *            data-api-key="YOUR_API_KEY"></script>
 *
 * 2. Inline embed - renders into a specific container:
 *    <div id="knowledge-expert-container"></div>
 *    <script src="https://your-domain.com/static/js/widget.js"
 *            data-api-key="YOUR_API_KEY"
 *            data-container="knowledge-expert-container"></script>
 *
 * 3. Manual initialization:
 *    KnowledgeExpert.init({
 *      apiKey: 'YOUR_API_KEY',
 *      apiUrl: 'https://your-domain.com',
 *      container: 'my-container-id',  // optional, omit for floating popup
 *      primaryColor: '#0d6efd',
 *      title: 'Ask us anything!'
 *    });
 */

(function() {
    'use strict';

    // Default configuration
    const defaults = {
        apiKey: null,
        apiUrl: null,  // Auto-detected from script src
        container: null,  // Target container ID for inline mode
        position: 'bottom-right',
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
    let widgetRoot = null;
    let messagesContainer = null;
    let isInlineMode = false;

    // Styles for floating popup mode
    const popupStyles = `
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
    `;

    // Styles shared by both modes
    const sharedStyles = `
        .ke-widget-header-bar {
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
        .ke-widget-input-area {
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
            font-family: inherit;
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

    // Inline mode styles
    const inlineStyles = `
        .ke-inline-widget {
            display: flex;
            flex-direction: column;
            height: 100%;
            min-height: 350px;
            border-radius: 8px;
            overflow: hidden;
            background: white;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        }
        .ke-inline-widget .ke-widget-messages {
            min-height: 200px;
            max-height: 400px;
        }
    `;

    function init(userConfig = {}) {
        config = { ...defaults, ...userConfig };

        // Auto-detect from script tag attributes
        const scriptTag = document.querySelector('script[data-api-key]');
        if (scriptTag) {
            if (!config.apiUrl && scriptTag.src) {
                const url = new URL(scriptTag.src);
                config.apiUrl = url.origin;
            }
            if (!config.apiKey) {
                config.apiKey = scriptTag.getAttribute('data-api-key');
            }
            if (!config.container) {
                config.container = scriptTag.getAttribute('data-container');
            }
        }

        if (!config.apiKey) {
            console.error('Knowledge Expert Widget: API key is required');
            return;
        }

        isInlineMode = !!config.container;

        // Inject styles
        const styleEl = document.createElement('style');
        styleEl.textContent = sharedStyles + (isInlineMode ? inlineStyles : popupStyles);
        document.head.appendChild(styleEl);

        if (isInlineMode) {
            initInline();
        } else {
            initPopup();
        }

        addMessage(config.welcomeMessage, 'assistant');
    }

    // Inline mode: render directly into the target container
    function initInline() {
        const targetEl = document.getElementById(config.container);
        if (!targetEl) {
            console.error('Knowledge Expert Widget: Container #' + config.container + ' not found');
            return;
        }

        // Clear the container (removes "Loading Knowledge Expert..." placeholder)
        targetEl.innerHTML = '';

        const wrapper = document.createElement('div');
        wrapper.className = 'ke-inline-widget';
        wrapper.innerHTML = `
            <div class="ke-widget-messages"></div>
            <div class="ke-widget-input-area">
                <input type="text" class="ke-widget-input" placeholder="${escapeHtml(config.placeholder)}">
                <button class="ke-widget-send" style="background: ${config.primaryColor};">Send</button>
            </div>
        `;
        targetEl.appendChild(wrapper);

        widgetRoot = wrapper;
        messagesContainer = wrapper.querySelector('.ke-widget-messages');

        bindInputEvents();
    }

    // Floating popup mode (original behavior)
    function initPopup() {
        widgetRoot = document.createElement('div');
        widgetRoot.className = `ke-widget-container ${config.position}`;
        widgetRoot.innerHTML = `
            <div class="ke-widget-chat" style="width: ${config.width}; height: ${config.height};">
                <div class="ke-widget-header-bar" style="background: ${config.primaryColor};">
                    <div>
                        <div class="ke-widget-header-title">${escapeHtml(config.title)}</div>
                        <div class="ke-widget-header-subtitle">${escapeHtml(config.subtitle)}</div>
                    </div>
                    <button class="ke-widget-close">&times;</button>
                </div>
                <div class="ke-widget-messages"></div>
                <div class="ke-widget-input-area">
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
        document.body.appendChild(widgetRoot);

        messagesContainer = widgetRoot.querySelector('.ke-widget-messages');

        // Popup toggle events
        const button = widgetRoot.querySelector('.ke-widget-button');
        const chat = widgetRoot.querySelector('.ke-widget-chat');
        const closeBtn = widgetRoot.querySelector('.ke-widget-close');

        button.addEventListener('click', () => {
            isOpen = !isOpen;
            chat.classList.toggle('open', isOpen);
            if (isOpen) {
                widgetRoot.querySelector('.ke-widget-input').focus();
            }
        });

        closeBtn.addEventListener('click', () => {
            isOpen = false;
            chat.classList.remove('open');
        });

        bindInputEvents();
    }

    function bindInputEvents() {
        const input = widgetRoot.querySelector('.ke-widget-input');
        const sendBtn = widgetRoot.querySelector('.ke-widget-send');

        const sendMessage = () => {
            const text = input.value.trim();
            if (!text) return;
            addMessage(text, 'user');
            input.value = '';
            sendQuery(text);
        };

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
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
        if (typingEl) typingEl.remove();
    }

    async function sendQuery(text) {
        const sendBtn = widgetRoot.querySelector('.ke-widget-send');
        const input = widgetRoot.querySelector('.ke-widget-input');

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

    // Public API
    window.KnowledgeExpert = {
        init: init,
        open: () => {
            if (widgetRoot && !isInlineMode) {
                isOpen = true;
                widgetRoot.querySelector('.ke-widget-chat').classList.add('open');
            }
        },
        close: () => {
            if (widgetRoot && !isInlineMode) {
                isOpen = false;
                widgetRoot.querySelector('.ke-widget-chat').classList.remove('open');
            }
        }
    };

    // Auto-initialize from script tag
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            const scriptTag = document.querySelector('script[data-api-key]');
            if (scriptTag) init();
        });
    } else {
        // DOM already loaded (script loaded async/deferred or late)
        const scriptTag = document.querySelector('script[data-api-key]');
        if (scriptTag) init();
    }
})();
