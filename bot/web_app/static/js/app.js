// Wolloyewa Store Bot - Web App JS

const API_BASE = '/app/api';

// Cart stored in localStorage
const cart = {
  items: JSON.parse(localStorage.getItem('wolloyewa_cart') || '[]'),

  save() { localStorage.setItem('wolloyewa_cart', JSON.stringify(this.items)); },

  add(product, qty = 1) {
    const existing = this.items.find(i => i.id === product.id);
    if (existing) {
      existing.qty += qty;
    } else {
      this.items.push({ ...product, qty });
    }
    this.save();
    this.updateBadge();
    showToast(`${product.name} added to cart ✓`);
  },

  remove(productId) {
    this.items = this.items.filter(i => i.id !== productId);
    this.save();
    this.updateBadge();
  },

  updateQty(productId, qty) {
    const item = this.items.find(i => i.id === productId);
    if (item) { item.qty = qty; this.save(); }
  },

  total() { return this.items.reduce((s, i) => s + (i.price * i.qty), 0); },

  count() { return this.items.reduce((s, i) => s + i.qty, 0); },

  clear() { this.items = []; this.save(); this.updateBadge(); },

  updateBadge() {
    const badge = document.querySelector('.cart-badge');
    if (badge) {
      const c = this.count();
      badge.textContent = c;
      badge.style.display = c > 0 ? 'inline' : 'none';
    }
  }
};

// Init badge on load
document.addEventListener('DOMContentLoaded', () => cart.updateBadge());

let webAppAuthPromise = null;

async function getWebAppAccessToken(forceRefresh = false) {
  if (forceRefresh) localStorage.removeItem('wolloyewa_access_token');
  const existingToken = localStorage.getItem('wolloyewa_access_token');
  if (existingToken) return existingToken;

  const telegramApp = window.Telegram && window.Telegram.WebApp;
  if (!telegramApp || !telegramApp.initData) return null;
  if (webAppAuthPromise) return webAppAuthPromise;

  webAppAuthPromise = (async () => {
    const response = await fetch(`${API_BASE}/auth`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: telegramApp.initData })
    });
    if (!response.ok) {
      console.warn('Could not authenticate Telegram Web App user.', response.status);
      return null;
    }
    const data = await response.json();
    if (!data.access_token) {
      console.warn('Telegram Web App authentication returned no access token.');
      return null;
    }
    localStorage.setItem('wolloyewa_access_token', data.access_token);
    return data.access_token;
  })();

  try {
    return await webAppAuthPromise;
  } catch (error) {
    console.warn('Could not authenticate Telegram Web App user.', error);
    return null;
  } finally {
    webAppAuthPromise = null;
  }
}

async function loadUserProfileAvatars() {
  let token = await getWebAppAccessToken();
  const avatars = document.querySelectorAll('.user-profile-avatar');
  if (!token || !avatars.length) return;

  try {
    let response = await fetch(`${API_BASE}/user/profile/photo`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (response.status === 401) {
      token = await getWebAppAccessToken(true);
      if (!token) return;
      response = await fetch(`${API_BASE}/user/profile/photo`, {
        headers: { Authorization: `Bearer ${token}` }
      });
    }
    if (!response.ok) return;

    const imageUrl = URL.createObjectURL(await response.blob());
    avatars.forEach(avatar => {
      const image = document.createElement('img');
      image.src = imageUrl;
      image.alt = 'Profile photo';
      avatar.replaceChildren(image);
    });
  } catch (error) {
    console.warn('Could not load the profile photo.', error);
  }
}

window.getWebAppAccessToken = getWebAppAccessToken;
document.addEventListener('DOMContentLoaded', loadUserProfileAvatars);

// Toast notification
function showToast(msg, duration = 2500) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), duration);
}

// Format ETB currency
function formatPrice(amount) {
  return 'ETB ' + Number(amount).toLocaleString('en-ET', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// HTML-escape untrusted strings before injecting into innerHTML
function he(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Validate a URL is safe (http/https only) before using in src/href
function safeUrl(url) {
  if (!url) return '';
  try {
    const u = new URL(url);
    return (u.protocol === 'http:' || u.protocol === 'https:') ? url : '';
  } catch { return ''; }
}

window.he = he;
window.safeUrl = safeUrl;

// Category emoji map
const categoryEmoji = {
  electronics: '📱',
  clothing: '👕',
  food: '🍎',
  books: '📚',
  beauty: '💄',
  health: '💊',
  home: '🏠',
  sports: '⚽',
  default: '🛍️'
};

function getCategoryEmoji(cat) {
  if (!cat) return categoryEmoji.default;
  const k = cat.toLowerCase();
  return categoryEmoji[k] || categoryEmoji.default;
}

// Fetch products from API
async function fetchProducts(params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/products${qs ? '?' + qs : ''}`);
  if (!res.ok) throw new Error('Failed to load products');
  return res.json();
}

// Fetch single product
async function fetchProduct(id) {
  const res = await fetch(`${API_BASE}/product/${id}`);
  if (!res.ok) throw new Error('Product not found');
  return res.json();
}

window.cart = cart;
window.showToast = showToast;
window.formatPrice = formatPrice;
window.getCategoryEmoji = getCategoryEmoji;
window.fetchProducts = fetchProducts;
window.fetchProduct = fetchProduct;

function updateCartBadge() {
  const badge = document.getElementById('cart-count');
  const stored = JSON.parse(localStorage.getItem('cart') || '[]');
  const count = stored.reduce((s, i) => s + (i.qty || 1), 0);
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'inline' : 'none';
  }
  cart.updateBadge();
}
window.updateCartBadge = updateCartBadge;
