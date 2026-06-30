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
