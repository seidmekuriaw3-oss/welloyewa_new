// Wolloyewa Store Bot - Web App JS

const API_BASE = '/app/api';

function loadSavedCart() {
  try {
    const savedItems = JSON.parse(localStorage.getItem('wolloyewa_cart') || '[]');
    if (!Array.isArray(savedItems)) return [];
    return savedItems
      .filter(item =>
        item &&
        Number.isSafeInteger(Number(item.id)) &&
        Number(item.id) > 0 &&
        typeof item.name === 'string' &&
        Number.isFinite(Number(item.price)) &&
        Number(item.price) >= 0 &&
        Number.isSafeInteger(Number(item.qty)) &&
        Number(item.qty) > 0
      )
      .map(item => ({
        ...item,
        id: Number(item.id),
        price: Number(item.price),
        qty: Number(item.qty),
      }));
  } catch (error) {
    console.warn('Could not restore the saved cart.', error);
    return [];
  }
}

// Cart stored in localStorage
const cart = {
  items: loadSavedCart(),

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
let webAppAuthGeneration = 0;

async function getWebAppAccessToken(forceRefresh = false) {
  if (forceRefresh) {
    localStorage.removeItem('wolloyewa_access_token');
    sessionStorage.removeItem('wolloyewa_logged_out');
    webAppAuthGeneration += 1;
  }
  if (sessionStorage.getItem('wolloyewa_logged_out') === 'true') return null;
  const existingToken = localStorage.getItem('wolloyewa_access_token');
  if (existingToken) {
    syncAuthenticationNavigation();
    return existingToken;
  }

  const telegramApp = window.Telegram && window.Telegram.WebApp;
  if (!telegramApp || !telegramApp.initData) return null;
  if (webAppAuthPromise) return webAppAuthPromise;

  const generation = webAppAuthGeneration;
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
    if (
      generation !== webAppAuthGeneration ||
      sessionStorage.getItem('wolloyewa_logged_out') === 'true'
    ) return null;
    localStorage.setItem('wolloyewa_access_token', data.access_token);
    syncAuthenticationNavigation();
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

async function authenticatedFetch(url, options = {}) {
  let token = await getWebAppAccessToken();
  if (!token) throw new Error('Please sign in to continue.');

  const send = accessToken => fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${accessToken}`
    }
  });

  let response = await send(token);
  if (response.status === 401) {
    token = await getWebAppAccessToken(true);
    if (!token) return response;
    response = await send(token);
  }
  return response;
}

let profileAvatarObjectUrl = null;

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
    if (!response.ok) {
      if (response.status === 404) resetUserProfileAvatars();
      return;
    }

    const imageUrl = URL.createObjectURL(await response.blob());
    const previousObjectUrl = profileAvatarObjectUrl;
    avatars.forEach(avatar => {
      const image = document.createElement('img');
      image.src = imageUrl;
      image.alt = window.localizeWebAppText
        ? window.localizeWebAppText('Profile photo')
        : 'Profile photo';
      avatar.replaceChildren(image);
    });
    profileAvatarObjectUrl = imageUrl;
    if (previousObjectUrl) URL.revokeObjectURL(previousObjectUrl);
  } catch (error) {
    console.warn('Could not load the profile photo.', error);
  }
}

function resetUserProfileAvatars() {
  document.querySelectorAll('.user-profile-avatar').forEach(avatar => {
    avatar.replaceChildren();
    avatar.textContent = avatar.dataset.defaultAvatar || 'W';
  });
  if (profileAvatarObjectUrl) {
    URL.revokeObjectURL(profileAvatarObjectUrl);
    profileAvatarObjectUrl = null;
  }
}

window.getWebAppAccessToken = getWebAppAccessToken;
window.authenticatedFetch = authenticatedFetch;
window.refreshUserProfileAvatars = loadUserProfileAvatars;
window.resetUserProfileAvatars = resetUserProfileAvatars;

async function uploadUserProfileImage(file, onProgress = () => {}) {
  let token = await getWebAppAccessToken();
  if (!token) throw new Error('Could not upload the profile photo.');

  const send = accessToken => new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open('PUT', `${API_BASE}/user/profile/photo`);
    request.setRequestHeader('Authorization', `Bearer ${accessToken}`);
    request.upload.addEventListener('progress', event => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    });
    request.addEventListener('load', () => {
      let result = {};
      try {
        result = JSON.parse(request.responseText);
      } catch {
        result = {};
      }
      resolve({ status: request.status, result });
    });
    request.addEventListener('error', () => reject(new Error('Could not upload the profile photo.')));
    request.addEventListener('abort', () => reject(new Error('Could not upload the profile photo.')));
    const formData = new FormData();
    formData.append('image', file);
    request.send(formData);
  });

  let response = await send(token);
  if (response.status === 401) {
    token = await getWebAppAccessToken(true);
    if (!token) throw new Error('Could not upload the profile photo.');
    response = await send(token);
  }
  if (response.status < 200 || response.status >= 300) {
    const detail = response.result.detail;
    throw new Error(Array.isArray(detail) ? detail.map(item => item.msg).join(' ') : detail
      || 'Could not upload the profile photo.');
  }
  onProgress(1);
  return response.result;
}

async function removeUserProfileImage() {
  const response = await authenticatedFetch(`${API_BASE}/user/profile/photo`, {
    method: 'DELETE'
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new Error(result.detail || 'Could not remove the profile image.');
  }
  return response.json();
}

window.uploadUserProfileImage = uploadUserProfileImage;
window.removeUserProfileImage = removeUserProfileImage;

async function updateWishlistOnServer(productId, shouldSave) {
  const token = await getWebAppAccessToken();
  if (!token) return false;

  const response = await authenticatedFetch(
    `${API_BASE}/user/wishlist/${Number(productId)}`,
    { method: shouldSave ? 'PUT' : 'DELETE' }
  );
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new Error(result.detail || 'Saved products could not be updated.');
  }
  return true;
}

async function syncWishlistWithServer() {
  const token = await getWebAppAccessToken();
  if (!token) return null;

  const localItems = window.productWishlist ? window.productWishlist.items() : [];
  const response = await authenticatedFetch(`${API_BASE}/user/wishlist/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_ids: localItems.slice(0, 500).map(item => Number(item.id))
    })
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new Error(result.detail || 'Saved products could not be synchronized.');
  }

  const result = await response.json();
  if (window.productWishlist) {
    window.productWishlist.merge(result.items || []);
    document.querySelectorAll('[data-wishlist-toggle]').forEach(button => {
      const saved = window.productWishlist.has(button.dataset.productId);
      button.classList.toggle('is-saved', saved);
      button.setAttribute('aria-pressed', String(saved));
    });
  }
  return result;
}

window.updateWishlistOnServer = updateWishlistOnServer;
window.syncWishlistWithServer = syncWishlistWithServer;
document.addEventListener('DOMContentLoaded', () => {
  if (window.productWishlist) {
    syncWishlistWithServer().catch(error => {
      console.warn('Saved products could not be synchronized.', error);
    });
  }
});
document.addEventListener('DOMContentLoaded', loadUserProfileAvatars);

function syncAuthenticationNavigation() {
  const logoutButton = document.getElementById('drawerLogoutButton');
  if (!logoutButton) return;
  const isLoggedOut = sessionStorage.getItem('wolloyewa_logged_out') === 'true';
  logoutButton.hidden = isLoggedOut || !localStorage.getItem('wolloyewa_access_token');
}

async function logoutWebApp() {
  const token = localStorage.getItem('wolloyewa_access_token');
  webAppAuthGeneration += 1;
  webAppAuthPromise = null;
  sessionStorage.setItem('wolloyewa_logged_out', 'true');
  localStorage.removeItem('wolloyewa_access_token');
  syncAuthenticationNavigation();

  if (token) {
    fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      keepalive: true
    }).catch(error => console.warn('Server-side logout could not be completed.', error));
  }
  window.location.assign('/app/login?logged_out=1');
}

window.logoutWebApp = logoutWebApp;
document.addEventListener('storage', event => {
  if (event.key === 'wolloyewa_access_token' && !event.newValue) {
    sessionStorage.setItem('wolloyewa_logged_out', 'true');
    syncAuthenticationNavigation();
  }
});
document.addEventListener('DOMContentLoaded', syncAuthenticationNavigation);

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
    const u = new URL(url, window.location.origin);
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
