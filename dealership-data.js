(function () {
  const defaultConfig = {
    url: 'https://invsxcmcczwckmfkynzk.supabase.co',
    anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImludnN4Y21jY3p3Y2ttZmt5bnprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA0NzE0NTEsImV4cCI6MjEwNjA0NzQ1MX0._zv75lSG6VIkk_Fxoh_aH25NRHO1DvXyqBJwaT_2-YM'
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

  function getCloudinaryConfig() {
    const value = window.__KINGDOM_CLOUDINARY_CONFIG__ || {};
    return {
      cloudName: String(value.cloudName || value.cloud_name || 'z2geao1b').trim(),
      folder: String(value.folder || value.path || '').trim().replace(/^\/+|\/+$/g, ''),
      transform: String(value.transform || value.transforms || value.transformation || 'f_auto,q_auto').trim()
    };
  }

  function toCloudinaryUrl(value) {
    if (!value) return '';
    const text = String(value).trim();
    if (!text) return '';
    if (/^https?:\/\//i.test(text) && /res\.cloudinary\.com\//i.test(text)) return text;

    const { cloudName, folder, transform } = getCloudinaryConfig();
    if (!cloudName) return value;

    const raw = text.split('?')[0].split('#')[0].replace(/^\/+/, '');
    const base = `https://res.cloudinary.com/${cloudName}/image/upload`;
    const clean = raw
      .replace(/^storage\/v1\/object\/public\//i, '')
      .replace(/^public\//i, '')
      .replace(/^images\//i, '')
      .replace(/^vehicles\//i, '')
      .replace(/^\/+/, '')
      .replace(/\/+$/g, '');

    const transformPath = transform ? `${transform}/` : '';
    const folderPath = folder ? `${folder}/` : '';
    if (!clean) return `${base}/${transformPath}${folderPath}`.replace(/\/+$/, '');
    return `${base}/${transformPath}${folderPath}${clean}`;
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

    const cloudUrl = toCloudinaryUrl(text);
    if (cloudUrl && cloudUrl !== text) return cloudUrl;

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
