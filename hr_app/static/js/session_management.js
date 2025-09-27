/**
 * Frontend session management utilities for HR Solutions
 * Handles session timeout warnings and automatic logout
 */

class SessionManager {
    constructor() {
        this.sessionTimeout = 3600000; // 1 hour in milliseconds
        this.warningTime = 300000; // 5 minutes before timeout
        this.checkInterval = 60000; // Check every minute
        
        this.warningShown = false;
        this.logoutTimer = null;
        this.checkTimer = null;
        
        this.init();
    }
    
    init() {
        // Start session monitoring
        this.startSessionMonitoring();
        
        // Listen for user activity
        this.bindActivityListeners();
        
        // Listen for storage events (for multiple tab management)
        window.addEventListener('storage', (e) => {
            if (e.key === 'session_logout') {
                // Another tab logged out, redirect this tab too
                window.location.href = '/login/';
            }
        });
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                // Page became visible, check session status
                this.checkSessionStatus();
            }
        });
    }
    
    startSessionMonitoring() {
        // Check session status periodically
        this.checkTimer = setInterval(() => {
            this.checkSessionStatus();
        }, this.checkInterval);
    }
    
    bindActivityListeners() {
        // Reset timeout on user activity
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        events.forEach(event => {
            document.addEventListener(event, () => {
                this.resetSessionTimeout();
            }, { passive: true });
        });
    }
    
    resetSessionTimeout() {
        // Clear existing timeout
        if (this.logoutTimer) {
            clearTimeout(this.logoutTimer);
        }
        
        // Hide warning if shown
        this.hideSessionWarning();
        
        // Set new timeout
        this.logoutTimer = setTimeout(() => {
            this.handleSessionTimeout();
        }, this.sessionTimeout);
        
        // Set warning timer
        setTimeout(() => {
            if (!this.warningShown) {
                this.showSessionWarning();
            }
        }, this.sessionTimeout - this.warningTime);
    }
    
    checkSessionStatus() {
        // Make AJAX call to check if session is still valid
        fetch('/api/session-status/', {
            method: 'GET',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (response.status === 401 || response.status === 403) {
                // Session invalid, logout
                this.logout('Session expired');
            }
        })
        .catch(error => {
            console.log('Session check failed:', error);
        });
    }
    
    showSessionWarning() {
        if (this.warningShown) return;
        
        this.warningShown = true;
        
        // Create warning modal
        const modal = document.createElement('div');
        modal.id = 'session-warning-modal';
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.zIndex = '9999';
        
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-warning">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle"></i> Session Timeout Warning
                        </h5>
                    </div>
                    <div class="modal-body">
                        <p>Your session will expire in <span id="countdown">5:00</span> due to inactivity.</p>
                        <p>Click "Stay Logged In" to continue your session.</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="sessionManager.logout('User chose to logout')">
                            Logout Now
                        </button>
                        <button type="button" class="btn btn-primary" onclick="sessionManager.extendSession()">
                            Stay Logged In
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Start countdown
        this.startCountdown();
    }
    
    startCountdown() {
        let timeLeft = 300; // 5 minutes in seconds
        const countdownElement = document.getElementById('countdown');
        
        const countdown = setInterval(() => {
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            
            if (countdownElement) {
                countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
            
            timeLeft--;
            
            if (timeLeft < 0) {
                clearInterval(countdown);
                this.handleSessionTimeout();
            }
        }, 1000);
    }
    
    hideSessionWarning() {
        const modal = document.getElementById('session-warning-modal');
        if (modal) {
            modal.remove();
        }
        this.warningShown = false;
    }
    
    extendSession() {
        // Make AJAX call to extend session
        fetch('/api/extend-session/', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCsrfToken()
            }
        })
        .then(response => {
            if (response.ok) {
                // Session extended successfully
                this.hideSessionWarning();
                this.resetSessionTimeout();
                
                // Show success message
                this.showNotification('Session extended successfully', 'success');
            } else {
                // Session extension failed
                this.logout('Session extension failed');
            }
        })
        .catch(error => {
            console.error('Session extension failed:', error);
            this.logout('Session extension error');
        });
    }
    
    handleSessionTimeout() {
        this.logout('Session timed out');
    }
    
    logout(reason) {
        // Clear timers
        if (this.logoutTimer) {
            clearTimeout(this.logoutTimer);
        }
        if (this.checkTimer) {
            clearInterval(this.checkTimer);
        }
        
        // Signal other tabs to logout
        localStorage.setItem('session_logout', Date.now().toString());
        
        // Show logout message
        this.showNotification(`Logging out: ${reason}`, 'warning');
        
        // Redirect to logout page after short delay
        setTimeout(() => {
            window.location.href = '/logout/';
        }, 2000);
    }
    
    getCsrfToken() {
        // Get CSRF token from meta tag or cookie
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    showNotification(message, type = 'info') {
        // Create notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '10000';
        notification.style.minWidth = '300px';
        
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    destroy() {
        // Clean up timers and listeners
        if (this.logoutTimer) {
            clearTimeout(this.logoutTimer);
        }
        if (this.checkTimer) {
            clearInterval(this.checkTimer);
        }
        
        // Remove event listeners would require storing references
        // For simplicity, we'll let the page unload handle cleanup
    }
}

// Initialize session manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if user is authenticated
    if (document.body.dataset.authenticated === 'true') {
        window.sessionManager = new SessionManager();
    }
});

// Prevent multiple tab login attempts
window.addEventListener('beforeunload', function() {
    if (window.sessionManager) {
        window.sessionManager.destroy();
    }
});