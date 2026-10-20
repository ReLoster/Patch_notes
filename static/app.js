function $(sel) { return document.querySelector(sel); }

function formatDate(ts) {
  return new Date(ts).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

function escapeHtml(text) {
  var div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function colorIndex(id) {
  var s = String(id);
  var sum = 0;
  for (var i = 0; i < s.length; i++) sum += s.charCodeAt(i);
  return sum % 5;
}

async function apiFetch(url, options) {
  options = options || {};
  var opts = Object.assign({ credentials: 'same-origin' }, options);
  if (opts.body && !opts.headers) {
    opts.headers = { 'Content-Type': 'application/json' };
  }
  var res = await fetch(url, opts);
  if (res.status === 401) {
    window.location.href = '/login.html';
    throw new Error('Unauthorized');
  }
  return res;
}

var currentUser = null;
var notes = [];
var folders = [];
var view = 'notes';
var currentFolderId = null;
var searchQuery = '';
var sortMode = 'custom';
var editingId = null;
var draggedId = null;

(async function init() {
  try {
    var res = await fetch('/api/auth/me', { credentials: 'same-origin' });
    if (!res.ok) { window.location.href = '/login.html'; return; }
    var data = await res.json();
    currentUser = data.user.login;
    $('#user-name').textContent = '👤 ' + currentUser;
    
    await loadData();
    
    $('#app').classList.remove('hidden');
    renderFolders();
    render();
    bindEvents();
  } catch (err) {
    console.error(err);
    window.location.href = '/login.html';
  }
})();

async function loadData() {
  var resNotes = await apiFetch('/api/notes');
  notes = (await resNotes.json()).notes;
  
  var resFolders = await apiFetch('/api/folders');
  folders = (await resFolders.json()).folders;
}

function renderFolders() {
  var list = $('#folders-list');
  list.innerHTML = '';
  
  var allBtn = document.createElement('div');
  allBtn.className = 'folder-item' + (currentFolderId === null ? ' active' : '');
  allBtn.innerHTML = '<span>Все заметки</span>';
  allBtn.onclick = function() { currentFolderId = null; renderFolders(); render(); };
  
  setupFolderDrop(allBtn, null);
  
  list.appendChild(allBtn);

  folders.forEach(function(f) {
    var div = document.createElement('div');
    div.className = 'folder-item' + (currentFolderId === f.id ? ' active' : '');
    div.innerHTML = '<span>' + escapeHtml(f.name) + '</span>' +
                    '<button class="del-btn link-btn" title="Удалить">×</button>';
    
    div.onclick = function() { currentFolderId = f.id; renderFolders(); render(); };
    
    div.querySelector('.del-btn').onclick = async function(e) {
      e.stopPropagation();
      if (!confirm('Удалить папку? Заметки в ней останутся.')) return;
      await apiFetch('/api/folders/' + f.id, { method: 'DELETE' });
      if (currentFolderId === f.id) currentFolderId = null;
      await loadData();
      renderFolders();
      render();
    };
    
    setupFolderDrop(div, f.id);
    
    list.appendChild(div);
  });
}

// Логика перетаскивания заметки на папку
function setupFolderDrop(element, folderId) {
  element.addEventListener('dragover', function(e) {
    if (!draggedId) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    element.classList.add('drop-target');
  });

  element.addEventListener('dragleave', function() {
    element.classList.remove('drop-target');
  });

  element.addEventListener('drop', async function(e) {
    e.preventDefault();
    element.classList.remove('drop-target');
    if (!draggedId) return;

    var note = notes.find(function(n) { return n.id === draggedId; });
    if (!note) return;

    if (note.folderId === folderId) return;

    try {
      await apiFetch('/api/notes/' + draggedId, {
        method: 'PATCH',
        body: JSON.stringify({ folderId: folderId })
      });
      draggedId = null;
      await loadData();
      renderFolders();
      render();
    } catch (err) { console.error(err); }
  });
}

function render() {
  document.querySelectorAll('.nav-btn').forEach(function(btn) {
    btn.classList.toggle('active', btn.dataset.view === view);
  });

  $('#view-title').textContent = view === 'notes' 
    ? (currentFolderId !== null ? 'Папка' : 'Заметки') 
    : 'Корзина';
  
  $('#new-note-btn').classList.toggle('hidden', view !== 'notes');

  var list = notes.filter(function(n) {
    return view === 'trash' ? n.deleted : !n.deleted;
  });

  if (view === 'notes' && currentFolderId !== null) {
    list = list.filter(function(n) { return n.folderId === currentFolderId; });
  }

  if (searchQuery !== '') {
    var q = searchQuery.toLowerCase();
    list = list.filter(function(n) {
      return n.title.toLowerCase().indexOf(q) !== -1 ||
             n.text.toLowerCase().indexOf(q) !== -1;
    });
  }

  list.sort(sorter);

  $('#empty-msg').textContent = list.length === 0
    ? (view === 'notes'
        ? (searchQuery ? 'Ничего не найдено' : 'Заметок нет. Создайте первую!')
        : 'Корзина пуста')
    : '';

  var grid = $('#notes-grid');
  grid.innerHTML = '';
  list.forEach(function(note) { grid.appendChild(makeCard(note)); });
}

function sorter(a, b) {
  if (a.isFavorite !== b.isFavorite) {
    return a.isFavorite ? -1 : 1;
  }
  
  switch (sortMode) {
    case 'custom':       return a.position - b.position;
    case 'updated-desc': return b.updatedAt - a.updatedAt;
    case 'updated-asc':  return a.updatedAt - b.updatedAt;
    case 'created-desc': return b.createdAt - a.createdAt;
    case 'created-asc':  return a.createdAt - b.createdAt;
    case 'title-asc':    return a.title.localeCompare(b.title, 'ru');
    case 'title-desc':   return b.title.localeCompare(a.title, 'ru');
    default: return 0;
  }
}

function makeCard(note) {
  var card = document.createElement('div');
  card.className = 'note-card color' + colorIndex(note.id) + (note.isFavorite ? ' is-favorite' : '');
  
  card.innerHTML =
    '<button class="favorite-btn ' + (note.isFavorite ? 'active' : '') + '" title="Избранное">★</button>' +
    '<h3>' + (escapeHtml(note.title) || 'Без названия') + '</h3>' +
    '<p>' + (escapeHtml(note.text) || '<i>Пусто</i>') + '</p>' +
    '<div class="note-dates">' +
      'Создана: ' + formatDate(note.createdAt) + '<br>' +
      'Изменена: ' + formatDate(note.updatedAt) +
    '</div>';

  card.querySelector('.favorite-btn').addEventListener('click', async function(e) {
    e.stopPropagation();
    await apiFetch('/api/notes/' + note.id, {
      method: 'PATCH',
      body: JSON.stringify({ isFavorite: !note.isFavorite })
    });
    await loadData();
    render();
  });

  card.addEventListener('click', function() { openEditor(note.id); });
  setupDragAndDrop(card, note.id);
  return card;
}

function setupDragAndDrop(card, noteId) {
  card.draggable = true;

  card.addEventListener('dragstart', function(e) {
    draggedId = noteId;
    card.classList.add('dragging');
    e.dataTransfer.setData('text/plain', String(noteId));
    e.dataTransfer.effectAllowed = 'move';

    var note = notes.find(function(n) { return n.id === noteId; });
    var ghost = document.createElement('div');
    ghost.className = 'drag-ghost';
    ghost.innerHTML = '📝 <span>' + (escapeHtml(note.title) || 'Заметка') + '</span>';
    document.body.appendChild(ghost);
    
    e.dataTransfer.setDragImage(ghost, 20, 20);
    setTimeout(function() { ghost.remove(); }, 0);
  });

  card.addEventListener('dragend', function() {
    draggedId = null;
    card.classList.remove('dragging');
    document.querySelectorAll('.note-card').forEach(function(el) { el.classList.remove('drag-over'); });
    document.querySelectorAll('.nav-btn').forEach(function(el) { el.classList.remove('drop-target'); });
    document.querySelectorAll('.folder-item').forEach(function(el) { el.classList.remove('drop-target'); });
  });

  card.addEventListener('dragover', function(e) {
    if (draggedId === null || draggedId === noteId) return;
    e.preventDefault();
    card.classList.add('drag-over');
  });

  card.addEventListener('dragleave', function() { card.classList.remove('drag-over'); });

  card.addEventListener('drop', function(e) {
    e.preventDefault();
    card.classList.remove('drag-over');
    if (draggedId === null || draggedId === noteId) return;
    moveNote(draggedId, noteId);
  });
}

async function moveNote(fromId, toId) {
  var fromIndex = notes.findIndex(function(n) { return n.id === fromId; });
  var toIndex = notes.findIndex(function(n) { return n.id === toId; });
  if (fromIndex === -1 || toIndex === -1) return;

  var moved = notes.splice(fromIndex, 1)[0];
  notes.splice(toIndex, 0, moved);

  if (sortMode !== 'custom') {
    sortMode = 'custom';
    $('#sort-label').textContent = 'По порядку';
  }
  render();

  try {
    await apiFetch('/api/notes/reorder', {
      method: 'POST',
      body: JSON.stringify({ order: notes.map(function(n) { return n.id; }) })
    });
  } catch (err) { console.error(err); }
}

function openEditor(noteId) {
  editingId = noteId;
  var note = noteId ? notes.find(function(n) { return n.id === noteId; }) : null;
  var isTrash = view === 'trash';

  $('#note-title').value = note ? note.title : '';
  $('#note-text').value = note ? note.text : '';
  $('#editor-meta').textContent = note
    ? 'Создана: ' + formatDate(note.createdAt) + ' · Изменена: ' + formatDate(note.updatedAt)
    : 'Новая заметка';

  $('#note-title').disabled = isTrash;
  $('#note-text').disabled = isTrash;
  $('#editor-save').classList.toggle('hidden', isTrash);
  $('#editor-restore').classList.toggle('hidden', !isTrash);
  $('#editor-restore').textContent = '♻ Восстановить';

  var delBtn = $('#editor-delete');
  if (isTrash) {
    delBtn.textContent = 'Удалить навсегда';
    delBtn.onclick = function() { deleteForever(noteId); };
  } else {
    delBtn.textContent = 'В корзину';
    delBtn.onclick = function() { moveToTrash(noteId); };
  }

  $('#editor-overlay').classList.remove('hidden');
}

function closeEditor() {
  $('#editor-overlay').classList.add('hidden');
  editingId = null;
}

async function saveEditor() {
  var title = $('#note-title').value.trim();
  var text = $('#note-text').value.trim();

  try {
    if (editingId) {
      await apiFetch('/api/notes/' + editingId, {
        method: 'PATCH',
        body: JSON.stringify({ title: title, text: text })
      });
    } else {
      await apiFetch('/api/notes', {
        method: 'POST',
        body: JSON.stringify({ title: title, text: text, folderId: currentFolderId })
      });
    }
    await loadData();
    render();
    closeEditor();
  } catch (err) { console.error(err); }
}

async function moveToTrash(noteId) {
  await apiFetch('/api/notes/' + noteId, { method: 'PATCH', body: JSON.stringify({ deleted: true }) });
  await loadData(); render(); closeEditor();
}

async function restoreNote(noteId) {
  await apiFetch('/api/notes/' + noteId, { method: 'PATCH', body: JSON.stringify({ deleted: false }) });
  await loadData(); render(); closeEditor();
}

async function deleteForever(noteId) {
  if (!confirm('Удалить заметку безвозвратно?')) return;
  await apiFetch('/api/notes/' + noteId, { method: 'DELETE' });
  await loadData(); render(); closeEditor();
}

function bindEvents() {
  document.querySelectorAll('.nav-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      view = btn.dataset.view;
      render();
    });
    bindSidebarDrop(btn);
  });

  $('#sidebar-toggle').addEventListener('click', function() {
    $('#sidebar').classList.toggle('collapsed');
  });

  var trigger = $('#sort-trigger');
  var options = $('#sort-options');
  trigger.addEventListener('click', function(e) {
    e.stopPropagation();
    options.classList.toggle('hidden');
  });
  options.addEventListener('click', function(e) {
    if (e.target.tagName === 'DIV') {
      sortMode = e.target.dataset.value;
      $('#sort-label').textContent = e.target.textContent;
      options.classList.add('hidden');
      render();
    }
  });
  document.addEventListener('click', function() {
    options.classList.add('hidden');
  });

  // --- ЛОГИКА МОДАЛКИ ПАПКИ ---
  $('#add-folder-btn').addEventListener('click', function() {
    $('#folder-name-input').value = '';
    $('#folder-overlay').classList.remove('hidden');
    $('#folder-name-input').focus();
  });

  $('#folder-cancel').addEventListener('click', function() {
    $('#folder-overlay').classList.add('hidden');
  });

  $('#folder-save').addEventListener('click', async function() {
    var name = $('#folder-name-input').value.trim();
    if (!name) return;
    await apiFetch('/api/folders', { method: 'POST', body: JSON.stringify({ name: name }) });
    $('#folder-overlay').classList.add('hidden');
    await loadData();
    renderFolders();
  });

  $('#folder-name-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      $('#folder-save').click();
    }
  });

  $('#logout-btn').addEventListener('click', async function() {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' });
    window.location.href = '/login.html';
  });

  $('#new-note-btn').addEventListener('click', function() { openEditor(null); });
  $('#editor-save').addEventListener('click', saveEditor);
  $('#editor-cancel').addEventListener('click', closeEditor);
  $('#editor-restore').addEventListener('click', function() {
    if (editingId) restoreNote(editingId);
  });

  $('#search-input').addEventListener('input', function() {
    searchQuery = this.value.trim();
    render();
  });

  $('#editor-overlay').addEventListener('click', function(e) {
    if (e.target === this) closeEditor();
  });
}

function bindSidebarDrop(btn) {
  var targetView = btn.dataset.view;

  btn.addEventListener('dragover', function(e) {
    if (!draggedId) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    btn.classList.add('drop-target');
  });

  btn.addEventListener('dragleave', function() { btn.classList.remove('drop-target'); });

  btn.addEventListener('drop', async function(e) {
    e.preventDefault();
    btn.classList.remove('drop-target');
    if (!draggedId) return;

    var note = notes.find(function(n) { return n.id === draggedId; });
    if (!note) return;

    var shouldBeDeleted = targetView === 'trash';
    if (note.deleted === shouldBeDeleted) return;

    try {
      await apiFetch('/api/notes/' + draggedId, {
        method: 'PATCH',
        body: JSON.stringify({ deleted: shouldBeDeleted })
      });
      draggedId = null;
      await loadData();
      render();
    } catch (err) { console.error(err); }
  });
}