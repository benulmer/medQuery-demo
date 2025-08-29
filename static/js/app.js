// MedQuery AI - Web Interface JavaScript

class MedQueryApp {
    constructor() {
        this.currentUser = null;
        this.chatHistory = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadUsers();
        this.setupTextarea();
    }

    bindEvents() {
        // User selection
        document.getElementById('userList').addEventListener('click', (e) => {
            const userCard = e.target.closest('.user-card');
            if (userCard) {
                this.selectUser(userCard.dataset.userId);
            }
        });

        // Switch user button
        document.getElementById('switchUserBtn').addEventListener('click', () => {
            this.showUserModal();
        });

        // New chat button
        document.getElementById('newChatBtn').addEventListener('click', () => {
            this.newChat();
        });

        // Send message
        document.getElementById('sendBtn').addEventListener('click', () => {
            this.sendMessage();
        });

        // Example queries
        document.getElementById('exampleQueries').addEventListener('click', (e) => {
            if (e.target.classList.contains('example-btn')) {
                document.getElementById('messageInput').value = e.target.textContent;
                this.updateSendButton();
            }
        });

        // Enter key to send
        document.getElementById('messageInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Input change to update send button
        document.getElementById('messageInput').addEventListener('input', () => {
            this.updateSendButton();
            this.autoResize();
        });
    }

    setupTextarea() {
        const textarea = document.getElementById('messageInput');
        this.autoResize = () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        };
    }

    async loadUsers() {
        try {
            const response = await fetch('/api/users');
            const data = await response.json();
            this.renderUsers(data.users);
        } catch (error) {
            console.error('Error loading users:', error);
        }
    }

    renderUsers(users) {
        const userList = document.getElementById('userList');
        userList.innerHTML = users.map(user => `
            <div class="user-card" data-user-id="${user.id}">
                <div class="user-avatar">${user.avatar}</div>
                <div class="user-details">
                    <h4>${user.name}</h4>
                    <div class="user-role">${user.role}</div>
                </div>
            </div>
        `).join('');
    }

    async selectUser(userId) {
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/user/select', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: userId })
            });

            const data = await response.json();
            
            if (data.success) {
                this.currentUser = data.user;
                this.updateUserInterface(data.user, data.permissions);
                this.hideUserModal();
                this.showWelcomeMessage();
            } else {
                this.showError('Failed to select user: ' + data.error);
            }
        } catch (error) {
            console.error('Error selecting user:', error);
            this.showError('Network error occurred');
        } finally {
            this.showLoading(false);
        }
    }

    updateUserInterface(user, permissions) {
        // Update user info in sidebar
        document.getElementById('userName').textContent = user.name;
        document.getElementById('userRole').textContent = user.role;
        
        // Get avatar from user list
        const userCard = document.querySelector(`[data-user-id="${user.id}"]`);
        if (userCard) {
            const avatar = userCard.querySelector('.user-avatar').textContent;
            document.getElementById('userAvatar').textContent = avatar;
        }

        // Update permissions
        const permissionsList = document.getElementById('permissionsList');
        permissionsList.innerHTML = permissions.map(permission => `
            <li class="${permission.includes('❌') ? 'denied' : ''}">${permission}</li>
        `).join('');

        // Update example queries based on role
        this.updateExampleQueries(user.role);
    }

    updateExampleQueries(role) {
        const examples = {
            doctor: [
                "Summarize Jane Smith's health history",
                "What medications is patient P001 taking?",
                "Show me David Chen's recent visit notes"
            ],
            researcher: [
                "Find patients with Type 2 Diabetes",
                "What's the average age of patients with Hypertension?",
                "Show population statistics for Asthma patients"
            ],
            marketing: [
                "What percentage of patients are over 60?",
                "How many patients take Metformin?",
                "Show aggregate medication usage statistics"
            ],
            intern: [
                "What can I do with this system?",
                "How does access control work?",
                "What are the different user roles?"
            ]
        };

        const exampleQueries = document.getElementById('exampleQueries');
        exampleQueries.innerHTML = (examples[role] || examples.intern).map(query => `
            <button class="example-btn">${query}</button>
        `).join('');
    }

    showUserModal() {
        document.getElementById('userModal').classList.add('active');
        document.getElementById('chatInterface').classList.remove('active');
    }

    hideUserModal() {
        document.getElementById('userModal').classList.remove('active');
        document.getElementById('chatInterface').classList.add('active');
    }

    showWelcomeMessage() {
        const chatMessages = document.getElementById('chatMessages');
        const welcomeMessage = chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'block';
        }
    }

    newChat() {
        this.chatHistory = [];
        const chatMessages = document.getElementById('chatMessages');
        // Clear all messages except welcome
        const messages = chatMessages.querySelectorAll('.message');
        messages.forEach(msg => msg.remove());
        this.showWelcomeMessage();
    }

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || !this.currentUser) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        input.value = '';
        this.updateSendButton();
        this.autoResize();

        // Hide welcome message
        const welcomeMessage = document.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }

        try {
            this.showLoading(true);
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            
            if (response.ok) {
                this.addMessage(data.message, 'assistant', {
                    success: data.success,
                    accessLevel: data.access_level,
                    redactedFields: data.redacted_fields,
                    timestamp: data.timestamp,
                    source: data.source,
                    sql: data.sql
                });
            } else {
                this.addMessage(data.error || 'An error occurred', 'assistant', {
                    success: false,
                    error: true
                });
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage('Network error occurred. Please try again.', 'assistant', {
                success: false,
                error: true
            });
        } finally {
            this.showLoading(false);
        }
    }

    addMessage(text, sender, metadata = {}) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender} ${metadata.error ? 'error-message' : ''}`;

        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        let headerContent = '';
        if (sender === 'assistant') {
            headerContent = `
                <div class="message-header">
                    <i class="fas fa-robot"></i>
                    <span>MedQuery AI</span>
                </div>
            `;
        }

        let footerContent = '';
        if (metadata.accessLevel) {
            footerContent = `
                <div class="message-footer">
                    <span class="access-level">${metadata.accessLevel}</span>
                    <span class="timestamp">${timestamp}</span>
                </div>
            `;
            
            if (metadata.redactedFields && metadata.redactedFields.length > 0) {
                footerContent += `
                    <div class="redacted-info">
                        <i class="fas fa-shield-alt"></i>
                        Redacted: ${metadata.redactedFields.join(', ')}
                    </div>
                `;
            }
        }

        const sqlSection = (metadata.sql && metadata.sql.length > 0) ? `
            <div class="sql-toggle">
                <button class="toggle-sql-btn">Show SQL</button>
                <pre class="sql-block" style="display:none;">${metadata.sql}</pre>
            </div>
        ` : '';

        const sourceBadge = metadata.source ? `<span class="source-badge">${metadata.source.toUpperCase()}</span>` : '';

        messageDiv.innerHTML = `
            <div class="message-content">
                ${headerContent}
                <div class="message-text">${this.formatMessage(text)}</div>
                ${sqlSection}
                ${footerContent}
                <div class="message-meta">${sourceBadge}</div>
            </div>
        `;

        chatMessages.appendChild(messageDiv);

        // Wire up toggle if present
        const toggleBtn = messageDiv.querySelector('.toggle-sql-btn');
        const sqlBlock = messageDiv.querySelector('.sql-block');
        if (toggleBtn && sqlBlock) {
            toggleBtn.addEventListener('click', () => {
                const isHidden = sqlBlock.style.display === 'none';
                sqlBlock.style.display = isHidden ? 'block' : 'none';
                toggleBtn.textContent = isHidden ? 'Hide SQL' : 'Show SQL';
            });
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Store in history
        this.chatHistory.push({
            text,
            sender,
            timestamp: new Date().toISOString(),
            metadata
        });
    }

    formatMessage(text) {
        // Basic text formatting
        return text
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    updateSendButton() {
        const input = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const hasText = input.value.trim().length > 0;
        
        sendBtn.disabled = !hasText || !this.currentUser;
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }

    showError(message) {
        // Could be enhanced with a toast notification system
        console.error(message);
        alert(message);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.medQueryApp = new MedQueryApp();
});

// Service worker registration for PWA capabilities (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((registration) => {
                console.log('SW registered: ', registration);
            })
            .catch((registrationError) => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}