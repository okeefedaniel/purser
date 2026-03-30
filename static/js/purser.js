/* Purser client-side utilities */

// Configure htmx to include CSRF token
document.addEventListener('DOMContentLoaded', function() {
    document.body.addEventListener('htmx:configRequest', function(event) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            event.detail.headers['X-CSRFToken'] = csrfToken.value;
        } else {
            // Fallback: read from cookie
            const cookie = document.cookie.split(';')
                .find(c => c.trim().startsWith('csrftoken='));
            if (cookie) {
                event.detail.headers['X-CSRFToken'] = cookie.split('=')[1];
            }
        }
    });
});
