const API_URL = '/api';

// Store token in localStorage
function setToken(token) {
    localStorage.setItem('token', token);
}

// Get token from localStorage
function getToken() {
    return localStorage.getItem('token');
}

// Remove token (logout)
function removeToken() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
}

// Store user info
function setUser(user) {
    localStorage.setItem('user', JSON.stringify(user));
}

// Get user info
function getUser() {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
}

// Check if user is logged in
function isLoggedIn() {
    return getToken() !== null;
}

// Make authenticated request
async function authFetch(url, options = {}) {
    const token = getToken();

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = 'Bearer ' + token;
    }

    const response = await fetch(API_URL + url, {
        ...options,
        headers
    });

    // If token expired, redirect to login
    if (response.status === 401) {
        removeToken();
        window.location.href = '/pages/auth/login.html';
        return null;
    }

    return response;
}

// Login
async function login(email, password) {
    const response = await fetch(API_URL + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (response.ok) {
        setToken(data.token);
        setUser(data.user);
        return { success: true, user: data.user };
    } else {
        return { success: false, error: data.error };
    }
}

// Register
async function register(email, username, password) {
    const response = await fetch(API_URL + '/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, username, password })
    });

    const data = await response.json();

    if (response.ok) {
        setToken(data.token);
        setUser(data.user);
        return { success: true, user: data.user };
    } else {
        return { success: false, error: data.error };
    }
}

// Logout
function logout() {
    removeToken();
    window.location.href = '/';
}

// Protect page - redirect to login if not authenticated
function requireAuth() {
    if (!isLoggedIn()) {
        window.location.href = '/pages/auth/login.html';
        return false;
    }
    return true;
}

// Protect page - redirect if not admin
function requireAdmin() {
    if (!isLoggedIn()) {
        window.location.href = '/pages/auth/login.html';
        return false;
    }
    var user = getUser();
    if (!user || user.role !== 'admin') {
        window.location.href = '/';
        return false;
    }
    return true;
}

// Redirect if already logged in (for login/register pages)
function redirectIfLoggedIn(redirectUrl = '/') {
    if (isLoggedIn()) {
        window.location.href = redirectUrl;
    }
}

// Update nav links based on login state
function updateNavLinks() {
    if (!isLoggedIn()) {
        var profileLinks = document.querySelectorAll('a[href="/pages/profile.html"]');
        for (var i = 0; i < profileLinks.length; i++) {
            profileLinks[i].href = '/pages/auth/login.html';
        }

        var offersLinks = document.querySelectorAll('a[href="/pages/offers/offers.html"]');
        for (var i = 0; i < offersLinks.length; i++) {
            offersLinks[i].style.display = 'none';
        }
    }
}

// Update cart badge count on nav
function updateCartBadge() {
    if (!isLoggedIn()) return;
    var token = getToken();
    fetch(API_URL + '/cart', {
        headers: { 'Authorization': 'Bearer ' + token }
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        var count = (data.cart || []).length;
        var badges = document.querySelectorAll('.cart-badge');
        for (var i = 0; i < badges.length; i++) {
            if (count > 0) {
                badges[i].textContent = count;
                badges[i].style.display = 'inline-block';
            } else {
                badges[i].style.display = 'none';
            }
        }
    })
    .catch(function() {});
}

// Run on page load
document.addEventListener('DOMContentLoaded', function() {
    updateNavLinks();
    updateCartBadge();
});
