// Admin frontend logic. Requires session auth token set by login.html
(function(){
  const isLocalDev = ['localhost', '127.0.0.1'].includes(window.location.hostname);
  const API_BASE = isLocalDev ? 'http://127.0.0.1:5001' : '';
  const API_PREFIX = isLocalDev ? '' : '/api';

  function adminUrl(path) {
    return `${API_BASE}${API_PREFIX}${path}`;
  }

  async function apiFetch(path, options = {}) {
    const url = adminUrl(path);
    try {
      const response = await fetch(url, options);
      if (response.ok || response.status >= 400) {
        return response;
      }
    } catch (error) {
      if (!isLocalDev) {
        throw error;
      }
      const fallback = await fetch('http://127.0.0.1:5000' + path, options);
      if (fallback.ok || fallback.status >= 400) return fallback;
    }
    throw new Error('Admin API unavailable');
  }

  function refreshDashboardSummary() {
    const mediaCount = document.getElementById('stat-media');
    const mediaStatus = document.getElementById('media-status');
    const systemStatus = document.getElementById('system-status');
    const systemNote = document.getElementById('system-note');
    const vehiclesCount = document.getElementById('stat-vehicles');
    const inquiriesCount = document.getElementById('stat-inquiries');
    const recentList = document.getElementById('recent-activity-list');
    const hudTimestamp = document.getElementById('hud-timestamp');
    const hudAlert = document.getElementById('hud-alert');

    if (hudTimestamp) {
      const now = new Date();
      hudTimestamp.textContent = now.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
    }

    if (hudAlert) {
      const minute = new Date().getMinutes();
      hudAlert.textContent = minute % 2 === 0 ? 'Operations nominal' : 'Sync window active';
    }

    if (mediaCount) {
      const raw = mediaCount.textContent || '0';
      const value = Number.parseInt(raw, 10);
      mediaCount.textContent = Number.isFinite(value) ? String(value) : '0';
    }

    if (mediaStatus) {
      const text = mediaStatus.textContent || '';
      mediaStatus.textContent = text && text !== 'Media library' ? text : 'Live media library';
    }

    if (systemStatus) {
      systemStatus.textContent = 'Online';
    }

    if (systemNote) {
      systemNote.textContent = 'System healthy';
    }

    if (recentList) {
      const vehicles = Number.parseInt(vehiclesCount?.textContent || '0', 10) || 0;
      const inquiries = Number.parseInt(inquiriesCount?.textContent || '0', 10) || 0;
      const media = Number.parseInt(mediaCount?.textContent || '0', 10) || 0;
      const syncStamp = new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
      recentList.innerHTML = [
        `<li>${vehicles} live vehicle listings</li>`,
        `<li>${inquiries} customer inquiries</li>`,
        `<li>${media} uploaded media files</li>`,
        `<li>Last sync: ${syncStamp}</li>`
      ].join('');
    }
  }

  const authKey = 'adminAuth';
  if (!sessionStorage.getItem(authKey)){
    window.location.href = 'login.html';
    return;
  }

  const logoutButton = document.getElementById('logout');
  if (logoutButton) {
    logoutButton.addEventListener('click', function(e){
      e.preventDefault();
      sessionStorage.removeItem(authKey);
      sessionStorage.removeItem('adminUser');
      window.location.href = 'login.html';
    });
  }

  const themeToggle = document.getElementById('theme-toggle');
  function applyTheme(theme){
    if (theme === 'dark') document.body.classList.add('dark');
    else document.body.classList.remove('dark');

    if (themeToggle) {
      themeToggle.setAttribute('aria-pressed', theme === 'dark');
      const small = themeToggle.querySelector('.small');
      if (small) small.textContent = theme === 'dark' ? 'Dark' : 'Light';
      const dot = themeToggle.querySelector('.dot');
      if (dot) dot.style.background = theme === 'dark' ? 'var(--accent-dark)' : 'var(--accent)';
    }
  }

  const savedTheme = localStorage.getItem('adminTheme') || 'light';
  applyTheme(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', function(){
      const next = document.body.classList.contains('dark') ? 'light' : 'dark';
      localStorage.setItem('adminTheme', next);
      applyTheme(next);
    });
  }

  function guessVehicleImage(href){
    const slug = href
      .replace(/^.*?vehicle-/, '')
      .replace(/\.html$/, '')
      .trim();

    if (!slug || slug === '#' || slug === 'undefined') return '';

    const candidates = [
      `../images/${slug}/1.jpg`,
      `../images/${slug}/thumb.jpg`,
      `../images/${slug}/cover.jpg`,
      `../images/${slug}/2.jpg`,
      `../images/${slug}/main.jpg`
    ];

    return candidates[0];
  }

  function normalizeStoragePath(value) {
    return String(value || '')
      .replace(/^\/+/, '')
      .replace(/^storage\/v1\/object\/public\//i, '')
      .replace(/^public\//i, '')
      .replace(/^images\//i, '')
      .replace(/^vehicles\//i, 'vehicles/');
  }

  function toPublicImageUrl(value) {
    if (!value || typeof value !== 'string') return '';
    const trimmed = value.trim();
    if (!trimmed) return '';

    const baseUrl = (window.__KINGDOM_SUPABASE_CONFIG__?.url || 'https://spckgpxzcxvogjamfsqr.supabase.co').replace(/\/$/, '');

    if (/^(https?:)?\/\//i.test(trimmed) || trimmed.startsWith('data:')) {
      const url = trimmed.split('?')[0].split('#')[0];
      const match = url.match(/^(https?:\/\/[^/]+)\/storage\/v1\/object\/public\/(.*)$/i);
      if (match) {
        const [, host, remainder] = match;
        const clean = normalizeStoragePath(remainder);
        return clean ? `${host}/storage/v1/object/public/${clean}` : `${host}/storage/v1/object/public/`;
      }
      return url;
    }

    if (trimmed.startsWith('/')) {
      const match = trimmed.match(/^\/storage\/v1\/object\/public\/(.*)$/i);
      if (match) {
        const clean = normalizeStoragePath(match[1]);
        return clean ? `${baseUrl}/storage/v1/object/public/${clean}` : `${baseUrl}/storage/v1/object/public/`;
      }
      return trimmed;
    }

    const clean = normalizeStoragePath(trimmed);
    return clean ? `${baseUrl}/storage/v1/object/public/${clean}` : `${baseUrl}/storage/v1/object/public/`;
  }

  function normalizeImageList(images) {
    if (!Array.isArray(images)) return [];
    return images.map(value => toPublicImageUrl(value)).filter(Boolean);
  }

  function isImagePath(value) {
    if (!value || typeof value !== 'string') return false;
    const cleaned = value.split('?')[0].split('#')[0].trim();
    if (!cleaned) return false;
    return /\.(jpe?g|png|gif|webp|svg|bmp|avif|jfif|heic|heif|tiff?|ico)$/i.test(cleaned);
  }

  function toMediaPreviewUrl(filePath) {
    if (!filePath || typeof filePath !== 'string') return '';
    const trimmed = filePath.trim();
    if (!trimmed) return '';
    if (/^https?:\/\//i.test(trimmed) || trimmed.startsWith('data:')) return trimmed;
    if (trimmed.startsWith('../') || trimmed.startsWith('/')) return trimmed;
    return `../${trimmed.replace(/^\.?\//, '')}`;
  }

  function bindFileSourceButtons() {
    document.querySelectorAll('.file-source-btn').forEach(button => {
      const inputId = button.dataset.fileInput;
      const input = inputId ? document.getElementById(inputId) : null;
      if (!input) return;

      button.addEventListener('click', () => {
        if (button.dataset.capture === '') {
          input.removeAttribute('capture');
        } else {
          input.setAttribute('capture', button.dataset.capture || 'environment');
        }
        input.click();
      });
    });
  }

  function renderFilePreview(input, previewEl) {
    if (!input || !previewEl) return;
    const files = Array.from(input.files || []).filter(file => file && file.type && file.type.startsWith('image/'));
    previewEl.innerHTML = '';

    if (!files.length) return;

    const first = files[0];
    const mainUrl = URL.createObjectURL(first);
    const mainTile = document.createElement('div');
    mainTile.className = 'file-preview-tile file-preview-primary';

    const img = document.createElement('img');
    img.src = mainUrl;
    img.alt = first.name;

    const name = document.createElement('span');
    name.textContent = first.name.length > 24 ? `${first.name.slice(0, 21)}...` : first.name;

    mainTile.appendChild(img);
    mainTile.appendChild(name);
    previewEl.appendChild(mainTile);

    if (files.length > 1) {
      const thumbRow = document.createElement('div');
      thumbRow.className = 'file-preview-row';

      files.slice(1).forEach(file => {
        const thumbUrl = URL.createObjectURL(file);
        const thumb = document.createElement('div');
        thumb.className = 'file-preview-thumb';

        const thumbImg = document.createElement('img');
        thumbImg.src = thumbUrl;
        thumbImg.alt = file.name;

        thumb.appendChild(thumbImg);
        thumbRow.appendChild(thumb);
      });

      previewEl.appendChild(thumbRow);
    }
  }

  /**
   * @typedef {Object} VehiclePhoto
   * @property {string} url Public URL of the stored image.
   * @property {string} filename Sanitized storage filename.
   * @property {string} path Storage path relative to the vehicles bucket.
   * @property {string} contentType Image MIME type.
   * @property {number} size Uploaded size in bytes.
   * @property {string} uploadedAt ISO-8601 upload timestamp.
   */

  function renderUploadedPhotos(photos, previewEl) {
    if (!previewEl) return;
    previewEl.innerHTML = '';
    (Array.isArray(photos) ? photos : []).forEach(photo => {
      const tile = document.createElement('div');
      tile.className = 'file-preview-tile';
      const image = document.createElement('img');
      image.src = photo.url;
      image.alt = photo.filename || 'Uploaded vehicle photo';
      image.onerror = () => { image.style.display = 'none'; };
      const caption = document.createElement('span');
      const size = Number(photo.size) ? ` · ${Math.max(1, Math.round(photo.size / 1024))} KB` : '';
      caption.textContent = `${photo.filename || 'Photo'}${size}`;
      tile.append(image, caption);
      previewEl.appendChild(tile);
    });
  }

  function bindPreviewInputs() {
    const inputs = [
      document.getElementById('create-files'),
      document.getElementById('files')
    ].filter(Boolean);

    inputs.forEach(input => {
      const previewId = input.id === 'create-files' ? 'create-file-preview' : 'upload-file-preview';
      const previewEl = document.getElementById(previewId);
      if (!previewEl) return;

      input.addEventListener('change', () => {
        if (input.files && input.files.length) {
          renderFilePreview(input, previewEl);
        } else {
          previewEl.innerHTML = '';
        }
      });
    });
  }

  function getSelectedVehicleIds(){
    const list = document.getElementById('vehicle-list');
    if (!list) return [];
    return [...list.querySelectorAll('.vehicle-select:checked')].map(item => item.value).filter(Boolean);
  }

  async function deleteVehicleRequest(id, password){
    const fd = new FormData();
    fd.append('id', id);
    fd.append('current_password', password);

    const r = await apiFetch('/admin/delete_vehicle', { method: 'POST', body: fd });
    const j = await r.json().catch(() => ({}));

    if (!r.ok) {
      throw new Error(j.error || r.statusText || 'Deletion request failed');
    }

    if (window.KingdomSupabase && typeof window.KingdomSupabase.deleteVehicle === 'function') {
      await window.KingdomSupabase.deleteVehicle(id);
    }

    if (typeof loadVehicles === 'function') {
      await loadVehicles();
    }

    return j;
  }

  async function bulkDeleteSelectedVehicles(){
    const selected = getSelectedVehicleIds();
    if (!selected.length) {
      alert('Select at least one vehicle to remove from the storefront.');
      return;
    }

    const password = window.prompt('Enter your current admin password to remove the selected vehicles from the storefront:');
    if (!password) {
      return;
    }

    try {
      const result = [];
      for (const id of selected) {
        try {
          await deleteVehicleRequest(id, password);
          result.push(id);
        } catch (error) {
          console.error('Bulk delete failed for', id, error);
        }
      }

      if (result.length) {
        alert(`${result.length} vehicle${result.length > 1 ? 's were' : ' was'} removed from the storefront.`);
      } else {
        alert('None of the selected vehicles could be removed. Check the password and try again.');
      }
    } catch (error) {
      console.error(error);
      alert('Bulk storefront removal failed. Check the password and try again.');
    }
  }

  async function loadVehicles(){
    const list = document.getElementById('vehicle-list');
    const countEl = document.getElementById('stat-vehicles');
    const bulkBar = document.getElementById('bulk-delete-bar');
    const selectAll = document.getElementById('select-all-vehicles');
    const bulkRemove = document.getElementById('bulk-remove-vehicles');

    if (bulkRemove) {
      bulkRemove.onclick = bulkDeleteSelectedVehicles;
    }

    try {
      const supabaseApi = window.KingdomSupabase;
      const vehicles = supabaseApi && typeof supabaseApi.loadVehicles === 'function' ? await supabaseApi.loadVehicles() : [];
      const rows = Array.isArray(vehicles) ? vehicles : [];

      if (countEl) countEl.textContent = String(rows.length);
      refreshDashboardSummary();
      if (!list) return;

      list.innerHTML = '';
      if (bulkBar) {
        bulkBar.hidden = rows.length === 0;
      }
      if (selectAll) {
        selectAll.checked = false;
      }
      if (!rows.length) {
        list.innerHTML = '<li>No vehicles yet.</li>';
        return;
      }

      rows.forEach(item => {
        const title = item.title || item.name || `${item.year || ''} ${item.make || item.brand || ''} ${item.model || ''}`.trim() || 'Untitled';
        const id = item.id || item.slug || item.vehicle_id || 'vehicle';
        const href = `../vehicle.html?id=${encodeURIComponent(id)}`;
        const imageSrc = Array.isArray(item.images) && item.images.length ? item.images[0] : '';
        const itemNode = document.createElement('li');
        const galleryImages = Array.isArray(item.images) ? item.images.filter(Boolean) : [];
        itemNode.innerHTML = `
          <button type="button" data-id="${id}" class="vehicle-card-action btn btn-danger remove-storefront">Remove from storefront</button>
          <div class="vehicle-list-row">
            <label class="vehicle-select-wrap"><input type="checkbox" class="vehicle-select" value="${id}" /></label>
            <img class="vehicle-thumbnail" src="${imageSrc}" alt="${title}" onerror="this.onerror=null;this.removeAttribute('src');" />
            <div class="vehicle-list-meta">
              <strong>${title}</strong>
              <a href="${href}" target="_blank">Open page</a>
              <small>${galleryImages.length} photo${galleryImages.length === 1 ? '' : 's'} in gallery</small>
            </div>
          </div>
          <div class="admin-gallery-strip">
            ${galleryImages.map((src, index) => `<img src="${src}" alt="${title} photo ${index + 1}" loading="lazy" onerror="this.onerror=null;this.removeAttribute('src');" />`).join('')}
          </div>
          <div class="mini-actions">
            <button type="button" data-id="${id}" class="mini-btn del">Delete</button>
            <button type="button" data-id="${id}" data-images="${Array.isArray(item.images)?item.images.length:0}" class="mini-btn regen">Thumbs</button>
          </div>
        `;
        list.appendChild(itemNode);
      });

      if (selectAll) {
        selectAll.onchange = function(){
          const checked = this.checked;
          list.querySelectorAll('.vehicle-select').forEach(checkbox => { checkbox.checked = checked; });
        };
      }

      list.querySelectorAll('.remove-storefront').forEach(button => button.addEventListener('click', async function(e){
        const id = e.target.dataset.id;
        const password = window.prompt('Enter your current admin password to remove this vehicle from the storefront:');
        if (!password) return;
        try {
          await deleteVehicleRequest(id, password);
          alert('Vehicle removed from the storefront.');
        } catch (error) {
          alert(error.message || 'Could not remove the vehicle.');
        }
      }));

      list.querySelectorAll('.del').forEach(button => button.addEventListener('click', e => {
        const id = e.target.dataset.id;
        promptDelete(id);
      }));

      list.querySelectorAll('.regen').forEach(button => button.addEventListener('click', async function(e){
        const id = e.target.dataset.id;
        const imagesCount = parseInt(e.target.dataset.images || '0', 10) || 0;
        if (imagesCount === 0) { alert('No images uploaded for this vehicle — upload images first.'); return; }
        const sizes = prompt('Enter sizes comma-separated (e.g. 800x600,400x300)', '800x600,400x300');
        if (sizes === null) return;
        const pwd = prompt('Admin current password (required)');
        if (!pwd) { alert('Password required'); return; }

        e.target.textContent = 'Working...';
        try {
          const fd = new FormData();
          fd.append('id', id);
          fd.append('sizes', sizes);
          fd.append('current_password', pwd);

          const r = await apiFetch('/admin/regenerate_thumbs', { method: 'POST', body: fd });
          const j = await r.json();

          if (r.ok) {
            alert('Thumbs regenerated: ' + (j.written || []).join(', '));
          } else {
            alert('Error: ' + (j.error || r.statusText));
          }
        } catch (err) {
          alert('Could not reach admin API');
        } finally {
          e.target.textContent = 'Thumbs';
        }
      }));
    } catch (error) {
      console.error(error);
      if (list) list.innerHTML = '<li>Could not load vehicles.</li>';
    }
  }

  function createDeleteModal(){
    let modal = document.getElementById('delete-confirm-modal');
    if (modal) return modal;

    modal = document.createElement('div');
    modal.id = 'delete-confirm-modal';
    modal.className = 'delete-confirm-modal';
    modal.innerHTML = `
      <div class="delete-confirm-card" role="dialog" aria-modal="true" aria-labelledby="delete-confirm-title">
        <h3 id="delete-confirm-title">Are you sure you want to delete?</h3>
        <p class="delete-confirm-text">This removes the listing, generated page, gallery files, and the matching inventory record.</p>
        <label class="delete-password-wrap">
          <span>Admin password</span>
          <input id="delete-confirm-password" type="password" placeholder="Current admin password" autocomplete="current-password" />
        </label>
        <div class="delete-confirm-actions">
          <button type="button" class="btn btn-ghost delete-cancel">Cancel</button>
          <button type="button" class="btn btn-primary delete-confirm">Confirm</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('.delete-cancel').addEventListener('click', function(){
      modal.classList.remove('open');
      modal.dataset.vehicleId = '';
      modal.querySelector('#delete-confirm-password').value = '';
    });

    modal.querySelector('.delete-confirm').addEventListener('click', async function(){
      const id = modal.dataset.vehicleId;
      const password = (modal.querySelector('#delete-confirm-password') || {}).value || '';
      if (!id) return;
      if (!password.trim()) {
        alert('Admin password is required to delete a vehicle.');
        return;
      }

      const submitBtn = modal.querySelector('.delete-confirm');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Deleting...';

      try {
        const fd = new FormData();
        fd.append('id', id);
        fd.append('current_password', password);

        const r = await apiFetch('/admin/delete_vehicle', {
          method: 'POST',
          body: fd
        });
        const j = await r.json().catch(() => ({}));

        if (!r.ok) {
          throw new Error(j.error || r.statusText || 'Deletion request failed');
        }

        if (window.KingdomSupabase && typeof window.KingdomSupabase.deleteVehicle === 'function') {
          await window.KingdomSupabase.deleteVehicle(id);
        }

        modal.classList.remove('open');
        modal.dataset.vehicleId = '';
        modal.querySelector('#delete-confirm-password').value = '';
        if (typeof loadVehicles === 'function') await loadVehicles();
        alert('Vehicle deleted successfully.');
      } catch (error) {
        console.error(error);
        alert('Admin API is unavailable. Start tools/admin_api.py, then try deleting the vehicle again so generated files and page references are cleaned up.');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Confirm';
      }
    });

    return modal;
  }

  function promptDelete(id){
    const modal = createDeleteModal();
    modal.dataset.vehicleId = id;
    modal.querySelector('#delete-confirm-password').value = '';
    modal.classList.add('open');
  }

  function createMediaLightbox(){
    let lightbox = document.getElementById('media-lightbox');
    if (lightbox) return lightbox;

    lightbox = document.createElement('div');
    lightbox.id = 'media-lightbox';
    lightbox.className = 'media-lightbox';
    lightbox.innerHTML = `
      <div class="media-lightbox-inner">
        <button type="button" class="media-lightbox-close" aria-label="Close preview">×</button>
        <img src="" alt="Vehicle media preview" />
        <div class="media-lightbox-meta">
          <strong>Vehicle preview</strong>
          <span>Preview</span>
        </div>
      </div>
    `;

    lightbox.querySelector('.media-lightbox-close').addEventListener('click', function(){
      lightbox.classList.remove('open');
      lightbox.querySelector('img').src = '';
    });

    lightbox.addEventListener('click', function(event){
      if (event.target === lightbox) {
        lightbox.classList.remove('open');
        lightbox.querySelector('img').src = '';
      }
    });

    document.body.appendChild(lightbox);
    return lightbox;
  }

  function bindMediaGalleryInteractions(){
    const list = document.getElementById('media-list');
    const searchInput = document.getElementById('media-search');
    if (!list || !searchInput) return;

    let dragItem = null;

    const applyFilter = () => {
      const term = searchInput.value.trim().toLowerCase();
      list.querySelectorAll('.media-card').forEach(card => {
        const text = (card.dataset.vehicle || '').toLowerCase() + ' ' + (card.dataset.fileText || '').toLowerCase();
        card.style.display = text.includes(term) ? '' : 'none';
      });
    };

    searchInput.addEventListener('input', applyFilter);

    list.querySelectorAll('.media-card').forEach(card => {
      const img = card.querySelector('img');
      const vehicleText = card.dataset.vehicle || '';
      const fileText = Array.from(card.querySelectorAll('.media-name')).map(el => el.textContent).join(' ');
      card.dataset.vehicle = vehicleText;
      card.dataset.fileText = fileText;

      card.addEventListener('dragstart', function(){
        dragItem = card;
        card.classList.add('dragging');
        list.classList.add('drag-active');
      });

      card.addEventListener('dragend', function(){
        dragItem = null;
        card.classList.remove('dragging');
        list.classList.remove('drag-active');
      });

      card.addEventListener('dragover', function(event){
        event.preventDefault();
        if (dragItem && dragItem !== card) {
          const cards = Array.from(list.querySelectorAll('.media-card')).filter(item => item.style.display !== 'none');
          const currentIndex = cards.indexOf(card);
          const dragIndex = cards.indexOf(dragItem);
          if (currentIndex > -1 && dragIndex > -1 && currentIndex !== dragIndex) {
            list.insertBefore(dragItem, currentIndex > dragIndex ? card.nextSibling : card);
          }
        }
      });

      if (img) {
        img.addEventListener('click', function(){
          const lightbox = createMediaLightbox();
          const imgNode = lightbox.querySelector('img');
          imgNode.src = img.src;
          lightbox.querySelector('strong').textContent = vehicleText;
          lightbox.classList.add('open');
        });
      }
    });

    list.addEventListener('dragover', function(event){
      event.preventDefault();
    });
  }

  async function removeMediaFile(vehicleId, filePath){
    const password = prompt('Enter your current admin password to remove this media file');
    if (!password) return;

    try {
      const fd = new FormData();
      fd.append('current_password', password);
      fd.append('vehicle_id', vehicleId);
      fd.append('file_path', filePath);

      const r = await apiFetch('/admin/delete_media', { method: 'POST', body: fd });
      const j = await r.json().catch(() => ({}));

      if (!r.ok) {
        throw new Error(j.error || r.statusText || 'Media removal failed');
      }

      if (typeof loadMediaLibrary === 'function') await loadMediaLibrary();
      alert('Media removed successfully.');
    } catch (error) {
      console.error(error);
      alert(error.message || 'Failed to remove media. Start tools/admin_api.py first.');
    }
  }

  async function loadMediaLibrary(){
    const list = document.getElementById('media-list');
    const countEl = document.getElementById('stat-media');
    const statusEl = document.getElementById('media-status');
    if (!list) return;

    try {
      const r = await apiFetch('/admin/list_media');
      const j = await r.json().catch(() => ({ media: [] }));
      const media = Array.isArray(j.media) ? j.media : [];
      const totalFiles = media.reduce((sum, item) => sum + (Array.isArray(item.files) ? item.files.length : 0), 0);
      if (countEl) countEl.textContent = String(totalFiles);
      if (statusEl) statusEl.textContent = totalFiles ? 'Live library' : 'No uploads yet';
      refreshDashboardSummary();

      list.innerHTML = '';
      if (!media.length) {
        list.innerHTML = '<li class="media-empty">No uploaded media yet.</li>';
        return;
      }

      media.forEach(item => {
        const vehicleId = item.vehicle_id || 'unknown';
        const files = Array.isArray(item.files) ? item.files : [];
        const firstFile = files[0];
        const card = document.createElement('li');
        card.className = 'media-card';
        card.draggable = true;
        card.dataset.vehicle = vehicleId;

        const previewSrc = firstFile && (firstFile.url || firstFile.path) ? toMediaPreviewUrl(firstFile.url || firstFile.path) : '';
        const preview = previewSrc && isImagePath(previewSrc)
          ? `<img src="${previewSrc}" alt="${vehicleId}" onerror="this.onerror=null;this.removeAttribute('src');" />`
          : '<div class="placeholder">IMG</div>';

        card.innerHTML = `
          <div class="media-preview">
            ${preview}
          </div>
          <div class="media-body">
            <div class="media-head">
              <strong>${vehicleId}</strong>
              <button type="button" class="mini-btn risk" data-vehicle="${vehicleId}">Delete vehicle</button>
            </div>
            ${files.map(file => `
              <div class="media-row">
                <div class="media-meta">
                  <span class="media-name">${file.name}</span>
                  <small>${file.size ? Math.max(1, Math.round(file.size / 1024)) + ' KB' : 'image'}</small>
                </div>
                <div class="media-actions">
                  <button type="button" class="mini-btn del" data-vehicle="${vehicleId}" data-file="${file.path}">Remove</button>
                </div>
              </div>
            `).join('')}
          </div>
        `;
        list.appendChild(card);
      });

      bindMediaGalleryInteractions();

      list.querySelectorAll('[data-file]').forEach(button => {
        button.addEventListener('click', function(){
          const vehicleId = this.dataset.vehicle;
          const filePath = this.dataset.file;
          removeMediaFile(vehicleId, filePath);
        });
      });

      list.querySelectorAll('[data-vehicle]:not([data-file])').forEach(button => {
        button.addEventListener('click', function(){
          promptDelete(this.dataset.vehicle);
        });
      });
    } catch (error) {
      console.error(error);
      list.innerHTML = '<li class="media-empty">Could not load media library.</li>';
      if (statusEl) statusEl.textContent = 'Library unavailable';
    }
  }

  async function readInquiries(){
    const supabaseApi = window.KingdomSupabase;
    if (supabaseApi && supabaseApi.isConfigured) {
      try {
        const rows = await supabaseApi.loadInquiries();
        if (Array.isArray(rows)) return rows;
      } catch (error) {
        console.warn('Supabase inquiry fetch failed:', error);
      }
    }

    try {
      return JSON.parse(localStorage.getItem('inquiries') || '[]');
    } catch (error) {
      return [];
    }
  }

  async function saveInquiries(arr){
    const supabaseApi = window.KingdomSupabase;
    if (supabaseApi && supabaseApi.isConfigured) {
      await supabaseApi.syncInquiryList(arr);
      return;
    }

    localStorage.setItem('inquiries', JSON.stringify(arr));
  }

  function buildReplyBody(item, message){
    const name = item.name || 'Customer';
    const vehicle = item.vehicle || 'your selected vehicle';
    const channel = (item.contact || '').trim();
    return {
      subject: 'Re: Your inquiry about ' + vehicle,
      body: `Hello ${name},\n\nThank you for your interest in ${vehicle}.\n\n${message}\n\nKind regards,\nKingdom AutoMobile\nwww.kingdomautomobile.com`,
      mailto: channel.includes('@')
        ? `mailto:${channel}?subject=${encodeURIComponent('Re: Your inquiry about ' + vehicle)}&body=${encodeURIComponent(`Hello ${name},\n\nThank you for your interest in ${vehicle}.\n\n${message}\n\nKind regards,\nKingdom AutoMobile\nwww.kingdomautomobile.com`)}`
        : '',
      sms: channel && !channel.includes('@')
        ? `sms:${channel.replace(/\D/g, '')}`
        : ''
    };
  }

  function normalizeMessageThread(item){
    const initial = item.message || '';
    const history = Array.isArray(item.history) ? item.history : [];
    if (!history.length && initial) {
      return [{ role: 'customer', text: initial, ts: item.ts || Date.now() }];
    }
    return history;
  }

  async function sendReply(item, message){
    const trimmed = (message || '').trim();
    if (!trimmed) {
      alert('Write a reply before sending it.');
      return;
    }

    const arr = await readInquiries();
    const updated = arr.map(entry => {
      const match = entry.ts === item.ts && entry.contact === item.contact && entry.name === item.name && entry.vehicle === item.vehicle;
      if (!match) return entry;

      const history = normalizeMessageThread(entry);
      history.push({ role: 'admin', text: trimmed, ts: Date.now() });

      return {
        ...entry,
        reply: trimmed,
        status: 'sent',
        replySentAt: new Date().toISOString(),
        history
      };
    });
    await saveInquiries(updated);

    const { mailto, sms } = buildReplyBody(item, trimmed);
    const target = item.contact && item.contact.includes('@') ? mailto : sms;

    if (target) {
      window.location.href = target;
    }

    await loadInquiries();
    alert('Customer reply saved and marked as sent.');
  }

  async function loadInquiries(){
    const ul = document.getElementById('inquiry-list');
    const countEl = document.getElementById('stat-inquiries');
    if (!ul) return;

    const arr = (await readInquiries()).slice().reverse();
    if (countEl) countEl.textContent = String(arr.length);
    refreshDashboardSummary();
    ul.innerHTML = '';

    if (!arr.length) {
      ul.innerHTML = '<li>No inquiries yet.</li>';
      return;
    }

    arr.forEach(item => {
      const li = document.createElement('li');
      const contact = item.contact || 'No contact';
      const vehicle = item.vehicle || 'Vehicle inquiry';
      const thread = normalizeMessageThread(item);
      const status = item.status === 'sent' || item.reply ? 'Sent' : 'Pending';
      const replyText = item.reply || 'Thank you for your interest in ' + vehicle + '. We would be happy to help with this vehicle.';

      const threadHtml = thread.map(entry => `
        <div class="thread-entry ${entry.role === 'admin' ? 'admin' : 'customer'}">
          <strong>${entry.role === 'admin' ? 'Kingdom' : (item.name || 'Customer')}</strong>
          <p>${(entry.text || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>
          <small>${new Date(entry.ts).toLocaleString()}</small>
        </div>
      `).join('');

      li.innerHTML = `
        <div class="inquiry-header">
          <div>
            <strong>${item.name || 'Unknown'}</strong><br />
            <small>${contact} • ${vehicle}</small>
          </div>
          <span class="status-badge ${status === 'Sent' ? 'sent' : 'pending'}">${status}</span>
        </div>
        <div class="inquiry-message">${item.message || ''}</div>
        <div class="thread">
          ${threadHtml}
        </div>
        <small>${new Date(item.ts).toLocaleString()}</small>
        <div class="inquiry-panel">
          <div class="reply-box ${item.reply ? 'open' : ''}">
            <textarea class="reply-text">${replyText}</textarea>
            <div class="reply-actions">
              <button type="button" class="send-reply-btn">Send reply</button>
              <button type="button" class="close-reply-btn">Close</button>
            </div>
          </div>
          <div class="reply-actions">
            <button type="button" class="reply-btn">Reply</button>
          </div>
        </div>
      `;

      const replyBox = li.querySelector('.reply-box');
      const replyBtn = li.querySelector('.reply-btn');
      const closeBtn = li.querySelector('.close-reply-btn');
      const sendBtn = li.querySelector('.send-reply-btn');
      const textarea = li.querySelector('.reply-text');

      replyBtn.addEventListener('click', () => {
        replyBox.classList.toggle('open');
      });

      closeBtn.addEventListener('click', () => {
        replyBox.classList.remove('open');
      });

      sendBtn.addEventListener('click', () => {
        sendReply(item, textarea.value);
      });

      ul.appendChild(li);
    });
  }

  const rotateForm = document.getElementById('rotate-creds');
  if (rotateForm) {
    rotateForm.addEventListener('submit', async function(e){
      e.preventDefault();
      const fd = new FormData(e.target);
      const current = fd.get('current');
      const username = fd.get('username');
      const password = fd.get('password');
      const resEl = document.getElementById('rotate-result');

      if (resEl) resEl.textContent = 'Rotating...';
      try {
        const r = await apiFetch('/admin/rotate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ current_password: current, new_username: username, new_password: password })
        });
        const j = await r.json();
        if (r.ok) {
          if (resEl) resEl.textContent = 'Credentials rotated. New user: ' + j.creds.username + '. Update saved.';
        } else {
          if (resEl) resEl.textContent = 'Error: ' + (j.error || r.statusText);
        }
      } catch (err) {
        if (resEl) resEl.textContent = 'Could not reach admin API (start tools/admin_api.py)';
      }
    });
  }

  bindFileSourceButtons();
  bindPreviewInputs();

  const uploadForm = document.getElementById('upload-images');
  if (uploadForm) {
    const modeSelect = uploadForm.querySelector('[name="mode"]');
    const uploadButton = uploadForm.querySelector('button[type="submit"]');
    if (modeSelect && uploadButton) {
      modeSelect.addEventListener('change', () => {
        uploadButton.textContent = modeSelect.value === 'replace' ? 'Replace Photos' : 'Upload Photos';
      });
    }
    uploadForm.addEventListener('submit', async function(e){
      e.preventDefault();
      const fd = new FormData();
      const id = uploadForm.querySelector('input[name="id"]').value.trim();
      const files = document.getElementById('files').files;
      const mode = uploadForm.querySelector('[name="mode"]').value;
      const submitButton = uploadForm.querySelector('button[type="submit"]');

      if (!id) {
        alert('Vehicle ID is required');
        return;
      }
      if (!files.length) {
        alert('Select at least one image to upload.');
        return;
      }

      for (let i = 0; i < files.length; i++) fd.append('files', files[i]);
      fd.append('id', id);
      fd.append('mode', mode);
      const currentPassword = uploadForm.querySelector('[name="current_password"]')?.value || '';
      if (!currentPassword) {
        alert('Admin password is required.');
        return;
      }
      fd.append('current_password', currentPassword);

      const resEl = document.getElementById('upload-res');
      if (resEl) resEl.textContent = mode === 'replace' ? 'Replacing photos...' : 'Uploading photos...';
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = mode === 'replace' ? 'Replacing…' : 'Uploading…';
      }

      try {
        const r = await apiFetch('/admin/upload', { method: 'POST', body: fd });
        const j = await r.json();
        if (r.ok) {
          const count = Number(j.count || (j.photos || []).length || files.length);
          const successText = mode === 'replace'
            ? `${count} photo${count === 1 ? '' : 's'} replaced successfully.`
            : `${count} photo${count === 1 ? '' : 's'} added successfully.`;
          if (resEl) resEl.textContent = successText;
          uploadForm.reset();
          const uploadPreview = document.getElementById('upload-file-preview');
          renderUploadedPhotos(j.photos, uploadPreview);
          if (typeof loadVehicles === 'function') await loadVehicles();
          if (typeof loadMediaLibrary === 'function') await loadMediaLibrary();
        } else {
          if (resEl) resEl.textContent = 'Error: ' + (j.error || r.statusText);
        }
      } catch (err) {
        if (resEl) resEl.textContent = 'Could not reach admin API (start tools/admin_api.py)';
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.textContent = mode === 'replace' ? 'Replace Photos' : 'Upload Photos';
        }
      }
    });
  }

  const createForm = document.getElementById('create-vehicle');
  if (createForm) {
    createForm.addEventListener('submit', async function(e){
      e.preventDefault();
      const fd = new FormData();
      const fields = [
        'current_password', 'id', 'brand', 'title', 'year_model', 'engine_capacity', 'mileage',
        'transmission', 'fuel', 'price', 'price_range', 'shipping_cost', 'service_fees', 'duty',
        'port_charges', 'total_landed_cost', 'current_location', 'vin', 'history', 'status', 'featured'
      ];

      const values = {};
      fields.forEach(key => {
        const field = createForm.querySelector('[name="' + key + '"]');
        if (field && field.value) {
          fd.append(key, field.value);
          values[key] = field.value;
        }
      });

      const files = document.getElementById('create-files').files;
      const imageList = [];

      // If files present, upload them first to get public URLs (ensures sanitized names)
      if (files && files.length) {
        try {
          const upFd = new FormData();
          const vidField = createForm.querySelector('[name="id"]');
          const vid = (vidField && vidField.value) ? vidField.value : '';
          upFd.append('id', vid);
          const currentPassword = createForm.querySelector('[name="current_password"]')?.value || '';
          upFd.append('current_password', currentPassword);
          for (let i = 0; i < files.length; i++) {
            upFd.append('files', files[i]);
          }
          const upR = await apiFetch('/admin/upload', { method: 'POST', body: upFd });
          const upJ = await upR.json().catch(() => ({}));
          if (upR.ok) {
            const uploaded = Array.isArray(upJ.files) ? upJ.files : (upJ.uploaded_urls || upJ.files || []);
            // ensure we have public URLs
            for (const u of uploaded) {
              if (u) imageList.push(u);
            }
            // append images as JSON so create_vehicle can use them
            fd.append('images', JSON.stringify(imageList));
          } else {
            console.warn('Upload step failed, continuing with local files');
            for (let i = 0; i < files.length; i++) {
              fd.append('files', files[i]);
              imageList.push(files[i].name);
            }
          }
        } catch (err) {
          console.warn('Upload to admin/upload failed, falling back to direct create upload', err);
          for (let i = 0; i < files.length; i++) {
            fd.append('files', files[i]);
            imageList.push(files[i].name);
          }
        }
      }

      const resEl = document.getElementById('create-res');
      if (resEl) resEl.textContent = 'Creating...';

      try {
        const r = await apiFetch('/admin/create_vehicle', { method: 'POST', body: fd });
        const j = await r.json();
        if (r.ok) {
          const successText = 'Uploaded successfully';
          if (resEl) resEl.textContent = successText;
          const createPreview = document.getElementById('create-file-preview');
          if (createPreview) createPreview.innerHTML = '';
          if (window.KingdomSupabase && typeof window.KingdomSupabase.syncVehicleList === 'function') {
            const vehicleId = values.id || values.title || 'vehicle';
            const record = {
              id: vehicleId,
              slug: vehicleId,
              title: values.title || `${values.brand || ''} ${values.year_model || ''}`.trim() || 'New Vehicle',
              brand: values.brand || '',
              make: values.brand || '',
              model: values.title || values.year_model || '',
              year: values.year_model || '',
              price: values.price || values.price_range || 'Contact for pricing',
              mileage: values.mileage || '',
              transmission: values.transmission || '',
              fuel: values.fuel || '',
              vin: values.vin || '',
              history: values.history || '',
              location: values.current_location || 'Tamale',
              images: imageList.length ? normalizeImageList(imageList) : [],
              created_at: new Date().toISOString()
            };
            await window.KingdomSupabase.syncVehicleList([record]);
          }
          createForm.reset();
          if (typeof loadVehicles === 'function') await loadVehicles();
          if (typeof loadMediaLibrary === 'function') await loadMediaLibrary();
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        } else {
          if (resEl) resEl.textContent = 'Error: ' + (j.error || r.statusText);
        }
      } catch (err) {
        const vehicleId = values.id || values.title || 'vehicle';
        const syncRecord = {
          id: vehicleId,
          slug: vehicleId,
          title: values.title || `${values.brand || ''} ${values.year_model || ''}`.trim() || 'New Vehicle',
          brand: values.brand || '',
          make: values.brand || '',
          model: values.title || values.year_model || '',
          year: values.year_model || '',
          price: values.price || values.price_range || 'Contact for pricing',
          mileage: values.mileage || '',
          transmission: values.transmission || '',
          fuel: values.fuel || '',
          vin: values.vin || '',
          history: values.history || '',
          location: values.current_location || 'Tamale',
            images: imageList.length ? normalizeImageList(imageList) : [],
          created_at: new Date().toISOString()
        };
        if (window.KingdomSupabase && typeof window.KingdomSupabase.syncVehicleList === 'function') {
          try {
            await window.KingdomSupabase.syncVehicleList([syncRecord]);
            if (resEl) resEl.textContent = 'Saved to database.';
          } catch (syncErr) {
            console.error(syncErr);
            if (resEl) resEl.textContent = 'Could not reach admin API or database.';
          }
        } else if (resEl) {
          resEl.textContent = 'Could not reach admin API (start tools/admin_api.py)';
        }
      }
    });
  }

  if (document.getElementById('media-list')) {
    loadMediaLibrary();
  }

  loadVehicles();
  loadInquiries();
  refreshDashboardSummary();
})();
