(function () {
  const defaultConfig = {
    url: 'https://spckgpxzcxvogjamfsqr.supabase.co',
    anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNwY2tncHh6Y3h2b2dqYW1mc3FyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1NDg2NjQsImV4cCI6MjEwNDEyNDY2NH0.h52gkl9ms2vT785SUTmAT_IDzNfaa2jUpepEGIW0yZw'
  };

  window.__KINGDOM_SUPABASE_CONFIG__ = Object.assign({}, defaultConfig, window.__KINGDOM_SUPABASE_CONFIG__ || {});

  function isPlaceholder(value) {
    if (!value || typeof value !== 'string') return true;
    return value.includes('your-project-ref') || value.includes('your-anon-key') || value.includes('replace-me');
  }

  function getConfig() {
    return {
      url: (window.__KINGDOM_SUPABASE_CONFIG__?.url || '').trim(),
      anonKey: (window.__KINGDOM_SUPABASE_CONFIG__?.anonKey || '').trim()
    };
  }

  function getClient() {
    const { url, anonKey } = getConfig();
    if (!window.supabase || !url || !anonKey || isPlaceholder(url) || isPlaceholder(anonKey)) return null;
    if (!window.__KINGDOM_DEALERSHIP_CLIENT__) {
      window.__KINGDOM_DEALERSHIP_CLIENT__ = window.supabase.createClient(url, anonKey);
    }
    return window.__KINGDOM_DEALERSHIP_CLIENT__;
  }

  function isImagePath(value) {
    if (!value || typeof value !== 'string') return false;
    const cleaned = value.split('?')[0].split('#')[0].trim();
    if (!cleaned) return false;
    return /\.(jpe?g|png|gif|webp|svg|bmp|avif|jfif|heic|heif|tiff?|ico)$/i.test(cleaned);
  }

  function normalizeStoragePath(value) {
    return String(value || '')
      .replace(/^\/+/, '')
      .replace(/^storage\/v1\/object\/public\//i, '')
      .replace(/^public\//i, '')
      .replace(/^images\//i, '')
      .replace(/^vehicles\//i, 'vehicles/');
  }

  function resolveImageUrl(value) {
    if (!value) return '';
    const text = String(value).trim();
    if (!text) return '';

    const baseUrl = (window.__KINGDOM_SUPABASE_CONFIG__?.url || defaultConfig.url).replace(/\/$/, '');

    if (/^(https?:)?\/\//i.test(text) || text.startsWith('data:')) {
      const url = text.split('?')[0].split('#')[0];
      const match = url.match(/^(https?:\/\/[^/]+)\/storage\/v1\/object\/public\/(.*)$/i);
      if (match) {
        const [, host, remainder] = match;
        const clean = normalizeStoragePath(remainder);
        return clean ? `${host}/storage/v1/object/public/${clean}` : `${host}/storage/v1/object/public/`;
      }
      return url;
    }

    if (text.startsWith('/')) {
      const match = text.match(/^\/storage\/v1\/object\/public\/(.*)$/i);
      if (match) {
        const clean = normalizeStoragePath(match[1]);
        return clean ? `${baseUrl}/storage/v1/object/public/${clean}` : `${baseUrl}/storage/v1/object/public/`;
      }
      return text;
    }

    if (text.startsWith('images/') || text.startsWith('../images/') || text.startsWith('./images/')) return text;

    const clean = normalizeStoragePath(text);
    return clean ? `${baseUrl}/storage/v1/object/public/${clean}` : `${baseUrl}/storage/v1/object/public/`;
  }

  function normalizeInventory(rows) {
    if (!Array.isArray(rows)) return [];
    return rows.map(item => ({
      ...item,
      images: Array.isArray(item.images) ? item.images.map(resolveImageUrl) : []
    }));
  }

  function getLocalInventory() {
    try {
      return JSON.parse(localStorage.getItem('dealershipInventory') || '[]');
    } catch (error) {
      return [];
    }
  }

  function getFallbackInventory() {
    // Production site: inventory comes only from Supabase/local admin state.
    // Never inject demo vehicles into the customer-facing website.
    return [];
  }

  function setLocalInventory(rows) {
    const nextRows = Array.isArray(rows) ? rows : [];
    localStorage.setItem('dealershipInventory', JSON.stringify(nextRows));
  }

  async function fetchDealershipInventory() {
    const client = getClient();
    if (client) {
      try {
        const { data, error } = await client.from('vehicles').select('*').order('created_at', { ascending: false });
        if (!error && Array.isArray(data)) {
          const normalized = normalizeInventory(data);
          setLocalInventory(normalized);
          return normalized;
        }
        console.warn('Supabase live inventory load failed:', error?.message || 'Unknown error');
      } catch (error) {
        console.warn('Supabase inventory source unavailable:', error);
      }
    }

    const localInventory = normalizeInventory(getLocalInventory());
    if (localInventory.length) {
      return localInventory;
    }

    return [];
  }

  async function getLiveInventoryCount() {
    const rows = await fetchDealershipInventory();
    return Array.isArray(rows) ? rows.length : 0;
  }

  window.DealershipData = {
    getConfig,
    getClient,
    fetchDealershipInventory,
    getLiveInventoryCount,
    getLocalInventory,
    setLocalInventory
  };
})();
