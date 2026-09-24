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
    if (!window.__KINGDOM_SUPABASE_CLIENT__) {
      window.__KINGDOM_SUPABASE_CLIENT__ = window.supabase.createClient(url, anonKey);
    }
    return window.__KINGDOM_SUPABASE_CLIENT__;
  }

  function getLocalInquiries() {
    try {
      return JSON.parse(localStorage.getItem('inquiries') || '[]');
    } catch (error) {
      return [];
    }
  }

  function setLocalInquiries(rows) {
    localStorage.setItem('inquiries', JSON.stringify(rows));
  }

  function getLocalVehicles() {
    try {
      return JSON.parse(localStorage.getItem('vehicles') || '[]');
    } catch (error) {
      return [];
    }
  }

  function getFallbackVehicles() { return []; }

  function normalizeStoragePath(value) {
    return String(value || '')
      .replace(/^\/+/, '')
      .replace(/^storage\/v1\/object\/public\//i, '')
      .replace(/^public\//i, '')
      .replace(/^images\//i, '')
      .replace(/^vehicles\//i, 'vehicles/');
  }

  function normalizeSupabaseImageUrl(value) {
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
    if (/\.(jpe?g|png|gif|webp|svg|bmp|avif|jfif|heic|heif|tiff?|ico)$/i.test(text)) return text;

    const clean = normalizeStoragePath(text);
    return clean ? `${baseUrl}/storage/v1/object/public/${clean}` : `${baseUrl}/storage/v1/object/public/`;
  }

  function setLocalVehicles(rows) {
    const normalizedRows = Array.isArray(rows) ? rows.map(item => ({
      ...item,
      images: Array.isArray(item.images) ? item.images.map(normalizeSupabaseImageUrl).filter(Boolean) : []
    })) : [];
    localStorage.setItem('vehicles', JSON.stringify(normalizedRows));
  }

  async function saveInquiry(record) {
    const payload = {
      vehicle: record.vehicle || 'Untitled vehicle',
      vehicle_id: record.id || record.vehicle_id || '',
      name: record.name || '',
      contact: record.contact || '',
      message: record.message || '',
      status: record.status || 'new',
      reply: record.reply || '',
      history: Array.isArray(record.history) ? record.history : [],
      created_at: new Date(record.ts || Date.now()).toISOString()
    };

    const client = getClient();
    if (client) {
      try {
        const { data, error } = await client.from('inquiries').insert([payload]).select();
        if (!error) {
          return { source: 'supabase', rows: data || [] };
        }
        console.warn('Supabase inquiry insert failed:', error.message);
      } catch (error) {
        console.warn('Supabase unavailable:', error);
      }
    }

    const rows = getLocalInquiries();
    rows.push({ ...payload, ts: payload.created_at ? Date.parse(payload.created_at) : Date.now() });
    setLocalInquiries(rows);
    return { source: 'localStorage', rows };
  }

  async function loadInquiries() {
    const client = getClient();
    if (client) {
      try {
        const { data, error } = await client.from('inquiries').select('*').order('created_at', { ascending: false });
        if (!error) {
          return (data || []).map(item => ({
            ...item,
            ts: item.created_at ? Date.parse(item.created_at) : Date.now(),
            history: Array.isArray(item.history) ? item.history : []
          }));
        }
        console.warn('Supabase inquiry load failed:', error.message);
      } catch (error) {
        console.warn('Supabase unavailable:', error);
      }
    }

    return getLocalInquiries();
  }

  async function syncInquiryList(rows) {
    const client = getClient();
    if (client) {
      try {
        const { error } = await client.from('inquiries').upsert(rows.map(item => ({
          id: item.id || undefined,
          vehicle: item.vehicle || 'Untitled vehicle',
          vehicle_id: item.vehicle_id || item.id || '',
          name: item.name || '',
          contact: item.contact || '',
          message: item.message || '',
          status: item.status || 'new',
          reply: item.reply || '',
          history: Array.isArray(item.history) ? item.history : [],
          created_at: item.created_at || new Date(item.ts || Date.now()).toISOString()
        })), { onConflict: 'id' });
        if (!error) {
          return true;
        }
        console.warn('Supabase inquiry sync failed:', error.message);
      } catch (error) {
        console.warn('Supabase unavailable:', error);
      }
    }

    setLocalInquiries(rows);
    return true;
  }

  async function loadVehicles() {
    const client = getClient();
    if (client) {
      try {
        const { data, error } = await client.from('vehicles').select('*').order('created_at', { ascending: false });
        if (!error) {
          const rows = (data || []).length ? (data || []).map(item => {
            const title = item.title || item.name || 'Vehicle';
            const titleParts = title.split(/\s+/).filter(Boolean);
            const make = item.make || item.brand || titleParts[0] || 'Vehicle';
            const model = item.model || titleParts.slice(1).join(' ') || title;
            return {
              ...item,
              id: item.id || item.slug || item.vehicle_id || '',
              make,
              brand: item.brand || make,
              model,
              title,
              type: item.type || 'vehicle'
            };
          }) : getFallbackVehicles();
          setLocalVehicles(rows);
          return rows;
        }
        console.warn('Supabase vehicle load failed:', error.message);
      } catch (error) {
        console.warn('Supabase unavailable:', error);
      }
    }

    const localRows = getLocalVehicles();
    if (Array.isArray(localRows) && localRows.length) {
      return localRows;
    }

    const fallbackRows = getFallbackVehicles();
    setLocalVehicles(fallbackRows);
    return fallbackRows;
  }

  async function syncVehicleList(rows) {
    const client = getClient();
    if (client) {
      try {
        const { error } = await client.from('vehicles').upsert(rows.map(item => {
          const title = item.title || item.name || 'Untitled vehicle';
          const payload = {
            id: item.id || item.slug || item.vehicle_id || undefined,
            slug: item.slug || item.id || item.vehicle_id || '',
            title,
            price: item.price || '',
            year: item.year || '',
            mileage: item.mileage || '',
            transmission: item.transmission || '',
            vin: item.vin || '',
            condition: item.condition || '',
            history: item.history || '',
            location: item.location || '',
            fuel: item.fuel || '',
            created_at: item.created_at || new Date(item.ts || Date.now()).toISOString()
          };

          if (Array.isArray(item.images) && item.images.length) payload.images = item.images;

          return payload;
        }), { onConflict: 'id' });
        if (!error) return true;
        console.warn('Supabase vehicle sync failed:', error.message);
      } catch (error) {
        console.warn('Supabase unavailable:', error);
      }
    }

    setLocalVehicles(rows);
    return true;
  }

  async function deleteVehicle(vehicleId) {
    const id = String(vehicleId || '').trim();
    if (!id) return false;

    const client = getClient();
    if (client) {
      try {
        const { error } = await client.from('vehicles').delete().eq('id', id);
        if (!error) return true;
        console.warn('Supabase vehicle delete failed:', error.message);
      } catch (error) {
        console.warn('Supabase unavailable:', error);
      }
    }

    const rows = getLocalVehicles().filter(item => String(item.id || item.slug || item.vehicle_id) !== id);
    setLocalVehicles(rows);
    return true;
  }

  async function signUpCustomer({ email, password, metadata = {} }) {
    const client = getClient();
    if (!client || !email || !password) {
      return { error: null, localFallback: true };
    }

    const { data, error } = await client.auth.signUp({
      email,
      password,
      options: { data: metadata }
    });

    return { data, error };
  }

  async function signInCustomer({ contact, password }) {
    const client = getClient();
    if (!client || !contact || !password) {
      return { error: null, localFallback: true };
    }

    if (/@/.test(contact)) {
      const { data, error } = await client.auth.signInWithPassword({
        email: contact,
        password
      });
      return { data, error };
    }

    const { data, error } = await client.auth.signInWithOtp({
      phone: contact,
      options: { shouldCreateUser: false }
    });

    return { data, error };
  }

  window.KingdomSupabase = {
    getConfig,
    isConfigured: Boolean(getConfig().url && getConfig().anonKey && !isPlaceholder(getConfig().url) && !isPlaceholder(getConfig().anonKey) && getClient()),
    saveInquiry,
    loadInquiries,
    syncInquiryList,
    loadVehicles,
    syncVehicleList,
    deleteVehicle,
    signUpCustomer,
    signInCustomer,
    getLocalInquiries,
    setLocalInquiries,
    getLocalVehicles,
    setLocalVehicles
  };
})();
