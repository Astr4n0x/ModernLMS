/**
 * Teacher Admin Panel JS - adapted for Django LMS
 * Handles: navigation, cascade selects, attachment rows, live monitoring AJAX
 */

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initSidebarToggle();
    initThemeToggle();
    initCascadeSelects();
    initAttachmentRows();
    initLiveCards();
    initImportModal();
});

// --- Module Navigation (URL-based - sections activated server-side via ?section= param) ---
function initNavigation() {
    // Navigation is now handled entirely by URL ?section= query params.
    // Sidebar links are real <a> tags - no JS toggling needed.
    // Mobile menu toggle:
    document.getElementById('menu-toggle')?.addEventListener('click', () => {
        document.querySelector('.sidebar').classList.toggle('open');
    });
}

function initSidebarToggle() {
    const toggleBtn = document.getElementById('sidebar-collapse-btn');
    toggleBtn?.addEventListener('click', () => {
        document.querySelector('.sidebar').classList.toggle('collapsed');
        document.querySelector('.main-content').classList.toggle('expanded');
    });
}

// --- Theme Toggle ---
function initThemeToggle() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    if (themeToggleBtn && themeIcon) {
        const currentTheme = localStorage.getItem('theme') || 'light';
        if (currentTheme === 'dark') {
            themeIcon.classList.replace('ri-moon-line', 'ri-sun-line');
        }

        themeToggleBtn.addEventListener('click', () => {
            let theme = document.documentElement.getAttribute('data-theme');
            if (theme === 'dark') {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
                themeIcon.classList.replace('ri-sun-line', 'ri-moon-line');
            } else {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                themeIcon.classList.replace('ri-moon-line', 'ri-sun-line');
            }
        });
    }
}

// --- Cascade: Course → Subject → Topic ---
function initCascadeSelects() {
    // Shared API base paths (provided globally via inline script in base_teacher.html if needed, 
    // but here we can just use relative paths since we know the routing).
    
    $('.course-select, #exam-course-select').on('change', function(e) {
        const courseId = $(this).val();
        if (!courseId) return;
        
        // Find relative subject dropdown based on data-target attribute or closest container
        const subjectSelect = document.getElementById(e.target.dataset.subjectTarget) || 
                              document.getElementById('upload-subject') || 
                              document.getElementById('topic-subject') ||
                              document.getElementById('exam-subject-select');
                              
        if (subjectSelect) {
            subjectSelect.disabled = true;
            subjectSelect.innerHTML = '<option value="" disabled selected>Loading...</option>';

            fetch(`/api/subjects/${courseId}/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(r => r.json())
            .then(data => {
                subjectSelect.innerHTML = '<option value="" selected>None</option>';
                data.subjects.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.id;
                    opt.textContent = s.title;
                    subjectSelect.appendChild(opt);
                });
                subjectSelect.disabled = false;
                $(subjectSelect).trigger('change.select2');
                
                // Trigger subject change to clear topic
                $(subjectSelect).trigger('change');
            });
        }
    });

    $('.subject-select, #exam-subject-select').on('change', function(e) {
        const subjectId = $(this).val();

        const topicSelect = document.getElementById(e.target.dataset.topicTarget) || 
                            document.getElementById('upload-topic') ||
                            document.getElementById('exam-topic-select');
        
        if (topicSelect) {
            if (!subjectId) {
                topicSelect.innerHTML = '<option value="" selected>None</option>';
                $(topicSelect).trigger('change.select2');
                return;
            }

            topicSelect.disabled = true;
            topicSelect.innerHTML = '<option value="" disabled selected>Loading...</option>';

            fetch(`/api/topics/${subjectId}/`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(r => r.json())
            .then(data => {
                topicSelect.innerHTML = '<option value="" selected>None</option>';
                data.topics.forEach(t => {
                    const opt = document.createElement('option');
                    opt.value = t.id;
                    opt.textContent = t.title;
                    topicSelect.appendChild(opt);
                });
                topicSelect.disabled = false;
                $(topicSelect).trigger('change.select2');
            });
        }
    });
}

// --- Dynamic Attachment Rows ---
function initAttachmentRows() {
    const addBtn = document.getElementById('add-attachment-btn');
    const container = document.getElementById('attachments-container');
    if (!addBtn || !container) return;

    addBtn.addEventListener('click', () => {
        const idx = container.children.length;
        const row = document.createElement('div');
        row.className = 'attachment-row';
        row.style.cssText = 'display:grid; grid-template-columns: 1fr 1fr auto; gap: 0.75rem; margin-bottom: 0.75rem; padding: 1rem; background: var(--bg-body, #f8f9fa); border-radius: 8px; border: 1px solid var(--border-color, #e2e8f0);';
        row.innerHTML = `
            <div class="form-group">
                <label style="font-size:0.8rem; font-weight:600; color: var(--text-secondary);">Name</label>
                <input type="text" name="attachment_name" placeholder="e.g. Chapter Slides" style="width:100%; padding:0.6rem 0.75rem; border:1px solid var(--border-color,#e2e8f0); border-radius:6px; font-size:0.875rem;">
            </div>
            <div class="form-group">
                <label style="font-size:0.8rem; font-weight:600; color: var(--text-secondary);">Type & Source</label>
                <select name="attachment_type" style="width:100%; padding:0.6rem 0.75rem; border:1px solid var(--border-color,#e2e8f0); border-radius:6px; font-size:0.875rem; margin-bottom:0.4rem;">
                    <option value="pdf">PDF</option>
                    <option value="slide">Slide</option>
                    <option value="note">Note</option>
                    <option value="link">External Link</option>
                    <option value="other">Other</option>
                </select>
                <input type="url" name="attachment_url" placeholder="Or paste URL here" style="width:100%; padding:0.6rem 0.75rem; border:1px solid var(--border-color,#e2e8f0); border-radius:6px; font-size:0.875rem;">
            </div>
            <div class="form-group" style="display:flex; flex-direction:column; justify-content:flex-end;">
                <label style="font-size:0.8rem; font-weight:600; color: var(--text-secondary);">File</label>
                <input type="file" style="font-size:0.8rem;">
                <button type="button" onclick="this.closest('.attachment-row').remove()" style="margin-top:0.5rem; padding:0.3rem 0.6rem; background:#fee2e2; color:#dc2626; border:1px solid #fca5a5; border-radius:4px; cursor:pointer; font-size:0.8rem;">✕ Remove</button>
            </div>
        `;
        container.appendChild(row);
    });
}

// --- Live Cards Click → Monitor ---
let activeSessionId = null;
let activeNodeId = null;
let teacherLiveSocket = null;
const seenTeacherCommentIds = new Set();

function initLiveCards() {
    document.querySelectorAll('.live-card[data-session-id]').forEach(card => {
        card.addEventListener('click', () => {
            const sessionId = card.dataset.sessionId;
            const nodeId = card.dataset.nodeId;
            const title = card.dataset.title;
            const youtubeUrl = card.dataset.youtubeUrl || '';
            enterLiveMonitor(sessionId, nodeId, title, youtubeUrl);
        });
    });

    document.getElementById('back-to-live-list')?.addEventListener('click', exitLiveMonitor);
    document.getElementById('end-live-btn')?.addEventListener('click', handleEndLive);
}

function enterLiveMonitor(sessionId, nodeId, title, youtubeUrl) {
    activeSessionId = sessionId;
    activeNodeId = nodeId;
    document.getElementById('live-list-view').classList.add('hidden');
    document.getElementById('live-stream-view').classList.remove('hidden');
    document.getElementById('back-to-live-list').classList.remove('hidden');
    document.getElementById('live-lesson-title').textContent = title;

    // Clear previous comments and reset deduplication
    document.getElementById('comments-feed').innerHTML = '';
    seenTeacherCommentIds.clear();

    // Reset viewer count
    const viewerCountEl = document.getElementById('teacher-viewer-count');
    if (viewerCountEl) viewerCountEl.innerHTML = '<i class="ri-eye-line"></i> Connecting...';

    // Set live video iframe src
    const iframe = document.getElementById('live-video-iframe');
    if (iframe) {
        iframe.src = youtubeUrl ? youtubeUrl + '?autoplay=1' : '';
    }

    // Step 1: Fetch existing comments from the database
    fetch(`/live/comments/${nodeId}/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(r => r.json())
    .then(data => {
        if (data.comments && data.comments.length > 0) {
            data.comments.forEach(c => {
                seenTeacherCommentIds.add(c.id);
                appendTeacherComment(c);
            });
        }
    })
    .catch(err => console.error('Failed to load past comments for teacher:', err))
    .finally(() => {
        // Step 2: Connect WebSocket for new real-time comments
        connectTeacherWebSocket(nodeId);
    });
}

function exitLiveMonitor() {
    if (teacherLiveSocket) {
        teacherLiveSocket.close();
        teacherLiveSocket = null;
    }
    activeSessionId = null;
    activeNodeId = null;
    // Stop video playback
    const iframe = document.getElementById('live-video-iframe');
    if (iframe) iframe.src = '';

    document.getElementById('live-stream-view').classList.add('hidden');
    document.getElementById('live-list-view').classList.remove('hidden');
    document.getElementById('back-to-live-list').classList.add('hidden');
}

function connectTeacherWebSocket(nodeId) {
    if (!nodeId) return;
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${wsScheme}://${window.location.host}/ws/live/${nodeId}/`;
    
    teacherLiveSocket = new WebSocket(wsUrl);

    teacherLiveSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === 'comment') {
            // Deduplicate: skip comments already rendered from the initial AJAX fetch
            if (data.comment.id && seenTeacherCommentIds.has(data.comment.id)) return;
            if (data.comment.id) seenTeacherCommentIds.add(data.comment.id);
            appendTeacherComment(data.comment);
        } else if (data.type === 'viewer_count') {
            const viewerCountEl = document.getElementById('teacher-viewer-count');
            if (viewerCountEl) {
                viewerCountEl.innerHTML = `<i class="ri-eye-line"></i> ${data.count} Watching`;
            }
        }
    };
    
    teacherLiveSocket.onclose = function(e) {
        console.error('Teacher live socket closed. Code:', e.code, 'Reason:', e.reason || 'none');
        const viewerCountEl = document.getElementById('teacher-viewer-count');
        if (viewerCountEl) {
            viewerCountEl.innerHTML = `<i class="ri-eye-line"></i> Offline (code: ${e.code})`;
        }
    };
}

function appendTeacherComment(comment) {
    const feed = document.getElementById('comments-feed');
    const el = document.createElement('div');
    el.className = 'comment';
    el.innerHTML = `
        <div class="comment-meta">
            <span class="comment-author">${escapeHtml(comment.author)}</span>
            <span class="comment-time">${comment.time_display}</span>
        </div>
        <div class="comment-text">${escapeHtml(comment.text)}</div>
    `;
    feed.appendChild(el);
    feed.scrollTop = feed.scrollHeight;
}

function handleEndLive() {
    if (!activeSessionId) return;
    if (!confirm('End this live session? This will mark the lesson as "Past Live" and students will no longer be able to comment.')) return;

    // Call end-live endpoint
    fetch(`/live/${activeSessionId}/end/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(r => r.json())
    .then(data => {
        showToast(data.message || 'Live session ended.');
        exitLiveMonitor();
        // Update status in manage table if visible
        setTimeout(() => location.reload(), 1500);
    })
    .catch(() => showToast('Could not end session. Please refresh.'));
}

function showToast(message) {
    const toast = document.getElementById('toast');
    const msg = document.getElementById('toast-msg');
    if (msg) msg.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3000);
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str || ''));
    return div.innerHTML;
}

// --- Content Builder Logic ---
document.addEventListener('DOMContentLoaded', () => {
    const courseSelect = document.getElementById('builder-course-select');
    const workspace = document.getElementById('builder-workspace');
    const treeContainer = document.getElementById('content-tree-container');
    const editorForm = document.getElementById('node-editor-form');
    const editorEmptyState = document.getElementById('editor-empty-state');
    const nodeTypeInput = document.getElementById('node-type');
    const ytGroup = document.getElementById('youtube-url-group');
    const ytInput = document.getElementById('node-youtube-url');
    const editorTitle = document.getElementById('editor-title');
    
    // Buttons
    const btnAddRoot = document.getElementById('btn-add-root-node');
    const btnAddChild = document.getElementById('btn-add-child');
    const btnDelete = document.getElementById('btn-delete-node');
    const btnCancel = document.getElementById('btn-cancel-edit');

    let currentCourseId = null;
    let selectedNodeId = null;
    let treeData = [];

    // ── Persist expand/collapse state across re-renders ──
    // Stores node IDs that the user has explicitly expanded.
    // By default all nodes are collapsed (not in this set).
    const expandedNodes = new Set();

    if (!courseSelect) return;

    $('#builder-course-select').on('change', function(e) {
        currentCourseId = e.target.value;
        if (currentCourseId) {
            workspace.style.display = 'flex';
            expandedNodes.clear(); // reset when switching course
            loadTree();
        }
    });

    $('#node-type').on('change', function(e) {
        if (e.target.value === 'class') {
            document.getElementById('class-mode-group').style.display = 'block';
            ytGroup.style.display = 'block';
            document.getElementById('attachment-section').style.display = 'block';
            ytInput.required = true;
        } else {
            document.getElementById('class-mode-group').style.display = 'none';
            ytGroup.style.display = 'none';
            document.getElementById('attachment-section').style.display = 'none';
            ytInput.required = false;
        }
    });

    btnAddRoot.addEventListener('click', () => {
        openEditor({ isRoot: true });
    });

    btnAddChild.addEventListener('click', () => {
        if (!selectedNodeId) return;
        openEditor({ parentId: selectedNodeId });
    });

    btnCancel.addEventListener('click', () => {
        closeEditor();
    });

    btnDelete.addEventListener('click', () => {
        if (!selectedNodeId) return;
        if (confirm('Are you sure you want to delete this node and ALL its children?')) {
            deleteNode(selectedNodeId);
        }
    });

    editorForm.addEventListener('submit', (e) => {
        e.preventDefault();
        saveNode();
    });

    function loadTree() {
        treeContainer.innerHTML = '<div style="padding:1rem;color:var(--text-secondary);">Loading tree...</div>';
        fetch(`/api/builder/tree/${currentCourseId}/`)
            .then(r => r.json())
            .then(data => {
                treeData = data.tree || [];
                renderTree();
            })
            .catch(() => {
                treeContainer.innerHTML = '<div style="color:red;padding:1rem;">Failed to load tree.</div>';
            });
    }

    function renderTree() {
        treeContainer.innerHTML = '';
        if (treeData.length === 0) {
            treeContainer.innerHTML = `
                <div style="padding:2.5rem 1rem;text-align:center;">
                    <i class="ri-folder-add-line" style="font-size:2.5rem;color:var(--border-color);display:block;margin-bottom:0.75rem;"></i>
                    <p style="color:var(--text-secondary);margin-bottom:0.5rem;">No content exists yet.</p>
                    <p style="color:var(--text-tertiary);font-size:0.85rem;">Click <strong>"Root Node"</strong> above to start building.</p>
                </div>`;
            return;
        }
        
        const ul = document.createElement('ul');
        ul.className = 'builder-tree-root';
        
        treeData.forEach(node => ul.appendChild(createTreeNode(node, 0)));
        treeContainer.appendChild(ul);
    }

    // ── Helper: find the path (breadcrumb) from root to a given node ──
    function findNodePath(nodes, targetId, path) {
        for (const node of nodes) {
            const currentPath = [...path, node];
            if (node.id == targetId) return currentPath;
            if (node.children && node.children.length > 0) {
                const found = findNodePath(node.children, targetId, currentPath);
                if (found) return found;
            }
        }
        return null;
    }

    function createTreeNode(node, depth) {
        const li = document.createElement('li');
        li.className = 'builder-tree-item';
        
        const isSelected = selectedNodeId == node.id;
        const isCollapsed = !expandedNodes.has(node.id);
        const hasChildren = node.children && node.children.length > 0;

        // Node row container
        const div = document.createElement('div');
        div.className = 'builder-tree-row' + (isSelected ? ' selected' : '');
        div.style.paddingLeft = `${depth * 1.25 + 0.5}rem`;

        // Expand/Collapse toggle
        const expandBtn = document.createElement('button');
        expandBtn.className = 'tree-expand-btn';
        expandBtn.type = 'button';
        
        let childrenUl = null;
        if (hasChildren) {
            expandBtn.innerHTML = isCollapsed
                ? '<i class="ri-arrow-right-s-line"></i>'
                : '<i class="ri-arrow-down-s-line"></i>';
            
            childrenUl = document.createElement('ul');
            childrenUl.className = 'builder-tree-children';
            if (isCollapsed) {
                childrenUl.style.display = 'none';
            }
            node.children.forEach(child => childrenUl.appendChild(createTreeNode(child, depth + 1)));
            
            expandBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (expandedNodes.has(node.id)) {
                    expandedNodes.delete(node.id);
                    childrenUl.style.display = 'none';
                    expandBtn.innerHTML = '<i class="ri-arrow-right-s-line"></i>';
                } else {
                    expandedNodes.add(node.id);
                    childrenUl.style.display = 'block';
                    expandBtn.innerHTML = '<i class="ri-arrow-down-s-line"></i>';
                }
            });
        } else {
            expandBtn.innerHTML = '<i class="ri-circle-fill" style="font-size:0.3rem;"></i>';
            expandBtn.style.cursor = 'default';
        }

        // Type icon
        const typeIcon = document.createElement('i');
        typeIcon.className = 'tree-type-icon';
        if (node.node_type === 'subject') {
            typeIcon.classList.add('ri-folder-2-fill');
            typeIcon.style.color = '#3b82f6';
        } else if (node.node_type === 'topic') {
            typeIcon.classList.add('ri-folder-open-fill');
            typeIcon.style.color = '#8b5cf6';
        } else {
            typeIcon.classList.add('ri-video-fill');
            typeIcon.style.color = '#ef4444';
        }

        // Title
        const titleSpan = document.createElement('span');
        titleSpan.className = 'tree-node-title';
        titleSpan.textContent = node.title;

        // Children count badge
        const countBadge = document.createElement('span');
        if (hasChildren) {
            countBadge.className = 'tree-child-count';
            countBadge.textContent = node.children.length;
        }

        // Quick actions (visible on hover)
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'tree-quick-actions';

        if (node.node_type !== 'class') {
            const addChildBtn = document.createElement('button');
            addChildBtn.type = 'button';
            addChildBtn.className = 'tree-action-btn add';
            addChildBtn.title = 'Add child node';
            addChildBtn.innerHTML = '<i class="ri-add-line"></i>';
            addChildBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                selectedNodeId = node.id;
                openEditor({ parentId: node.id });
            });
            actionsDiv.appendChild(addChildBtn);
        }

        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.className = 'tree-action-btn delete';
        deleteBtn.title = 'Delete node';
        deleteBtn.innerHTML = '<i class="ri-delete-bin-6-line"></i>';
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (confirm(`Delete "${node.title}" and all its children?`)) {
                deleteNode(node.id);
            }
        });
        actionsDiv.appendChild(deleteBtn);

        div.appendChild(expandBtn);
        div.appendChild(typeIcon);
        div.appendChild(titleSpan);
        if (hasChildren) div.appendChild(countBadge);
        div.appendChild(actionsDiv);

        div.addEventListener('click', () => {
            selectNode(node);
        });

        li.appendChild(div);
        if (childrenUl) li.appendChild(childrenUl);
        return li;
    }

    function selectNode(node) {
        // ── Update selection highlight WITHOUT full re-render ──
        // Remove old selection
        const prevSelected = treeContainer.querySelector('.builder-tree-row.selected');
        if (prevSelected) prevSelected.classList.remove('selected');

        selectedNodeId = node.id;

        // Find and highlight the newly selected row
        const allRows = treeContainer.querySelectorAll('.builder-tree-row');
        allRows.forEach(row => {
            // Identify by matching the data we store
            // We set a data attribute for reliable lookups
        });

        // Since we need data-id on rows for this approach, let's use a targeted re-render
        // that preserves collapse state (which we now track in collapsedNodes)
        renderTree();
        
        editorEmptyState.style.display = 'none';
        editorForm.style.display = 'block';

        // Show breadcrumb path
        const path = findNodePath(treeData, node.id, []);
        let breadcrumb = '';
        if (path && path.length > 1) {
            breadcrumb = path.map(n => n.title).join(' › ');
            editorTitle.innerHTML = `<span class="editor-breadcrumb">${escapeHtml(breadcrumb)}</span>Editing: <strong>${escapeHtml(node.title)}</strong>`;
        } else {
            editorTitle.innerHTML = `Editing: <strong>${escapeHtml(node.title)}</strong>`;
        }

        document.getElementById('node-id').value = node.id;
        document.getElementById('node-parent-id').value = node.parent_id || '';
        document.getElementById('node-title').value = node.title;
        document.getElementById('node-type').value = node.node_type;
        $('#node-type').trigger('change.select2');
        $('#node-class-mode').trigger('change.select2');
        
        document.getElementById('node-order').value = node.order;
        document.getElementById('node-description').value = node.description || '';
        
        if (node.node_type === 'class') {
            document.getElementById('class-mode-group').style.display = 'block';
            ytGroup.style.display = 'block';
            document.getElementById('attachment-section').style.display = 'block';
            ytInput.value = node.youtube_url || '';
            ytInput.required = true;
            document.getElementById('node-class-mode').value = node.status === 'live' ? 'live' : 'recorded';
            $('#node-class-mode').trigger('change.select2');
        } else {
            document.getElementById('class-mode-group').style.display = 'none';
            ytGroup.style.display = 'none';
            document.getElementById('attachment-section').style.display = 'none';
            ytInput.value = '';
            ytInput.required = false;
        }

        btnDelete.style.display = 'inline-block';
        btnAddChild.style.display = 'inline-block';
    }

    function openEditor({ isRoot = false, parentId = null }) {
        selectedNodeId = null;
        renderTree(); // remove highlight (collapse state preserved)
        
        editorEmptyState.style.display = 'none';
        editorForm.style.display = 'block';
        editorForm.reset();
        document.getElementById('attachments-container').innerHTML = ''; // Clear prior attachments
        
        document.getElementById('node-id').value = '';
        document.getElementById('node-parent-id').value = parentId || '';
        document.getElementById('node-order').value = '1';
        
        if (parentId) {
            // Show breadcrumb for parent
            const path = findNodePath(treeData, parentId, []);
            if (path) {
                const breadcrumb = path.map(n => n.title).join(' › ');
                editorTitle.innerHTML = `<span class="editor-breadcrumb">${escapeHtml(breadcrumb)}</span>Add Child Node`;
            } else {
                editorTitle.textContent = 'Add Child Node';
            }
            // Default to topic/class based on context could be predicted, but let's just default to class
            document.getElementById('node-type').value = 'class';
            $('#node-type').trigger('change.select2');
            
            document.getElementById('class-mode-group').style.display = 'block';
            ytGroup.style.display = 'block';
            document.getElementById('attachment-section').style.display = 'block';
            ytInput.required = true;

            // Auto-expand the parent node so the user can see where they're adding
            expandedNodes.add(parentId);
            renderTree();
        } else if (isRoot) {
            editorTitle.textContent = 'Add Root Node';
            document.getElementById('node-type').value = 'subject';
            $('#node-type').trigger('change.select2');
            
            document.getElementById('class-mode-group').style.display = 'none';
            ytGroup.style.display = 'none';
            document.getElementById('attachment-section').style.display = 'none';
            ytInput.required = false;
        }

        btnDelete.style.display = 'none';
        btnAddChild.style.display = 'none';
    }

    function closeEditor() {
        selectedNodeId = null;
        renderTree(); // collapse state preserved
        editorEmptyState.style.display = 'block';
        editorForm.style.display = 'none';
    }

    function saveNode() {
        let formData = new FormData(editorForm);
        formData.append('course_id', currentCourseId);
        
        // Ensure files have unique names so python can parse them
        const attachmentRows = document.querySelectorAll('.attachment-row input[type="file"]');
        attachmentRows.forEach((input, index) => {
            if (input.files.length > 0) {
                // Change the name before submitting or append manually
                formData.append(`attachment_file_${index}`, input.files[0]);
            }
        });
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

        // Show saving state
        const saveBtn = document.getElementById('btn-save-node');
        const saveBtnText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="ri-loader-4-line" style="animation:spin 1s linear infinite;"></i> Saving...';

        fetch('/api/builder/node/save/', {
            method: 'POST',
            headers: {
                // Do NOT set Content-Type header when sending FormData! Browser handles multipart.
                'X-CSRFToken': csrfToken
            },
            body: formData
        })
        .then(r => r.json())
        .then(res => {
            saveBtn.disabled = false;
            saveBtn.innerHTML = saveBtnText;
            if (res.success) {
                showToast(res.message);
                loadTree();
                closeEditor();
            } else {
                alert('Error: ' + res.message);
            }
        })
        .catch(() => {
            saveBtn.disabled = false;
            saveBtn.innerHTML = saveBtnText;
            alert('Network error occurred.');
        });
    }

    function deleteNode(nodeId) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        fetch(`/api/builder/node/${nodeId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                showToast(res.message);
                expandedNodes.delete(nodeId); // Clean up
                loadTree();
                closeEditor();
            } else {
                alert('Error: ' + res.message);
            }
        });
    }
});


// ─── Import Modal Logic ─────────────────────────────────────────────────────
function initImportModal() {
    // ── DOM refs ──────────────────────────────────────────────────────────────
    const modal          = document.getElementById('import-modal');
    const btnOpen        = document.getElementById('btn-import-content');
    const btnClose       = document.getElementById('btn-close-import-modal');
    const btnCancel      = document.getElementById('btn-cancel-import');
    const btnConfirm     = document.getElementById('btn-confirm-import');
    const btnConfirmLbl  = document.getElementById('btn-confirm-import-label');
    const courseSelect   = document.getElementById('import-course-select');
    const step2          = document.getElementById('import-step2');
    const treeContainer  = document.getElementById('import-tree-container');
    const treeLoading    = document.getElementById('import-tree-loading');
    const badge          = document.getElementById('import-selected-badge');
    const badgeLabel     = document.getElementById('import-selected-label');
    const destInfo       = document.getElementById('import-destination-info');
    const destLabel      = document.getElementById('import-destination-label');

    if (!modal || !btnOpen) return;  // Not on content-builder page

    // ── State ─────────────────────────────────────────────────────────────────
    let selectedImportNodeId   = null;
    let selectedImportNodeTitle = null;

    // ── Helpers ───────────────────────────────────────────────────────────────
    function getCsrf() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    function getBuilderCourseId() {
        return document.getElementById('builder-course-select')?.value || null;
    }

    function getSelectedNodeId() {
        // Read from the hidden form field (set by selectNode() in main builder)
        return document.getElementById('node-id')?.value || null;
    }

    function getSelectedNodeTitle() {
        const titleEl = document.getElementById('editor-title');
        if (!titleEl) return '';
        const raw = titleEl.textContent || '';
        return raw.replace(/^Editing:\s*/i, '').trim();
    }

    // ── Open Modal ────────────────────────────────────────────────────────────
    function openModal() {
        // Require a course to be selected in the builder first
        if (!getBuilderCourseId()) {
            showToast('Please select a course in the Content Builder first.');
            return;
        }

        // Reset state
        selectedImportNodeId    = null;
        selectedImportNodeTitle = null;
        step2.style.display     = 'none';
        badge.style.display     = 'none';
        destInfo.style.display  = 'none';
        btnConfirm.disabled     = true;
        btnConfirmLbl.textContent = 'Confirm Import';
        treeContainer.innerHTML = '';
        if (treeLoading) treeLoading.style.display = 'block';

        // Show modal
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Load courses list
        courseSelect.innerHTML = '<option value="" disabled selected>Loading\u2026</option>';
        fetch('/api/builder/import/courses/')
            .then(r => r.json())
            .then(data => {
                courseSelect.innerHTML = '<option value="" disabled selected>Choose a course\u2026</option>';
                data.courses.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.textContent = c.title;
                    courseSelect.appendChild(opt);
                });
                // NOTE: Do NOT re-init Select2 on this dropdown - it fights with the
                // native change listener inside the modal. The base_teacher.html already
                // applied Select2 to all selects on page load; the dynamically populated
                // options are updated fine via plain HTML. We destroy any existing
                // Select2 instance here so the native listener governs it.
                if (window.$ && $.fn.select2) {
                    try { $(courseSelect).select2('destroy'); } catch(e) {}
                }
            })
            .catch(() => {
                courseSelect.innerHTML = '<option disabled>Failed to load courses</option>';
            });


        // Update destination label
        updateDestinationLabel();
    }

    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = '';
        selectedImportNodeId    = null;
        selectedImportNodeTitle = null;
    }

    // ── Update destination info bar ───────────────────────────────────────────
    function updateDestinationLabel() {
        const parentNodeId    = getSelectedNodeId();
        const parentNodeTitle = getSelectedNodeTitle();

        if (parentNodeId) {
            destLabel.textContent = `Will be imported as a child of: "${parentNodeTitle}"`;
        } else {
            destLabel.textContent = 'Will be imported as a root node of the current course.';
        }
    }

    // ── Load source tree ──────────────────────────────────────────────────────
    function loadImportTree(courseId) {
        step2.style.display = 'block';
        treeContainer.innerHTML = '';
        if (treeLoading) {
            treeLoading.style.display = 'block';
            treeContainer.appendChild(treeLoading);
        }

        fetch(`/api/builder/tree/${courseId}/`)
            .then(r => r.json())
            .then(data => {
                treeContainer.innerHTML = '';
                const tree = data.tree || [];
                if (tree.length === 0) {
                    treeContainer.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--text-secondary);">This course has no content yet.</div>';
                    return;
                }
                const ul = document.createElement('ul');
                ul.style.cssText = 'list-style:none; padding:0; margin:0;';
                tree.forEach(node => ul.appendChild(createImportTreeNode(node, 0)));
                treeContainer.appendChild(ul);
            })
            .catch(() => {
                treeContainer.innerHTML = '<div style="padding:1rem;color:#ef4444;">Failed to load tree.</div>';
            });
    }

    // ── Build a read-only tree node (mirrors main builder's createTreeNode) ────
    function createImportTreeNode(node, depth) {
        const li = document.createElement('li');
        li.style.margin = '0';

        const div = document.createElement('div');
        div.style.cssText = `
            padding: 0.45rem 0.5rem 0.45rem ${depth * 1.5 + 0.5}rem;
            display: flex; align-items: center; gap: 0.5rem;
            cursor: pointer; border-bottom: 1px solid var(--border-color);
            transition: background 0.15s;
            border-left: 4px solid transparent;
        `;

        // Highlight selected
        if (selectedImportNodeId == node.id) {
            div.style.background    = '#eef2ff';
            div.style.borderLeft    = '4px solid #A1BC98';
        } else {
            div.addEventListener('mouseenter', () => div.style.background = '#f8fafc');
            div.addEventListener('mouseleave', () => { if (selectedImportNodeId != node.id) div.style.background = 'transparent'; });
        }

        // Expand icon
        const expandIcon = document.createElement('i');
        expandIcon.style.cssText = 'width:20px; text-align:center; color:var(--text-secondary);';

        let childrenUl = null;
        if (node.children && node.children.length > 0) {
            expandIcon.className = 'ri-arrow-down-s-line';
            expandIcon.style.cursor = 'pointer';
            childrenUl = document.createElement('ul');
            childrenUl.style.cssText = 'list-style:none; padding:0; margin:0;';
            node.children.forEach(child => childrenUl.appendChild(createImportTreeNode(child, depth + 1)));

            expandIcon.addEventListener('click', e => {
                e.stopPropagation();
                if (childrenUl.style.display === 'none') {
                    childrenUl.style.display = 'block';
                    expandIcon.className = 'ri-arrow-down-s-line';
                } else {
                    childrenUl.style.display = 'none';
                    expandIcon.className = 'ri-arrow-right-s-line';
                }
            });
        } else {
            expandIcon.className = 'ri-checkbox-blank-circle-fill';
            expandIcon.style.fontSize = '0.4rem';
        }

        // Type icon
        const typeIcon = document.createElement('i');
        if (node.node_type === 'subject')      { typeIcon.className = 'ri-folder-2-fill';   typeIcon.style.color = '#3b82f6'; }
        else if (node.node_type === 'topic')   { typeIcon.className = 'ri-folder-open-fill'; typeIcon.style.color = '#3b82f6'; }
        else                                    { typeIcon.className = 'ri-video-fill';       typeIcon.style.color = '#ef4444'; }

        // Count badge (show child count as hint)
        const childCount = countDescendants(node);
        const countBadge = document.createElement('span');
        if (childCount > 0) {
            countBadge.textContent = `+${childCount}`;
            countBadge.style.cssText = 'font-size:0.7rem; background:#e8f0e6; color:#778873; border-radius:10px; padding:1px 6px; margin-left:auto; flex-shrink:0;';
        }

        // Title
        const titleSpan = document.createElement('span');
        titleSpan.textContent = node.title;
        titleSpan.style.cssText = 'font-weight:500; color:var(--text-primary); flex:1;';

        div.appendChild(expandIcon);
        div.appendChild(typeIcon);
        div.appendChild(titleSpan);
        if (childCount > 0) div.appendChild(countBadge);

        div.addEventListener('click', () => selectImportNode(node));

        li.appendChild(div);
        if (childrenUl) li.appendChild(childrenUl);
        return li;
    }

    function countDescendants(node) {
        if (!node.children || node.children.length === 0) return 0;
        return node.children.reduce((sum, c) => sum + 1 + countDescendants(c), 0);
    }

    // ── Select a node in the import tree ──────────────────────────────────────
    function selectImportNode(node) {
        selectedImportNodeId    = node.id;
        selectedImportNodeTitle = node.title;

        // Rebuild tree to refresh highlights
        const courseId = courseSelect.value;
        if (courseId) loadImportTree(courseId);

        // Show badge
        const childCount = countDescendants(node);
        badge.style.display    = 'flex';
        badgeLabel.textContent = `"${node.title}" selected` +
            (childCount > 0 ? ` - will also import ${childCount} child node${childCount === 1 ? '' : 's'}` : '');

        // Show destination info
        updateDestinationLabel();
        destInfo.style.display = 'block';

        // Enable confirm
        btnConfirm.disabled = false;
    }

    // ── Perform the import ────────────────────────────────────────────────────
    function confirmImport() {
        if (!selectedImportNodeId) return;

        const targetCourseId  = getBuilderCourseId();
        const targetParentId  = getSelectedNodeId() || '';

        if (!targetCourseId) {
            showToast('No target course selected. Please select a course in the builder first.');
            return;
        }

        // Loading state
        btnConfirm.disabled       = true;
        btnConfirmLbl.textContent = 'Importing\u2026';

        const formData = new FormData();
        formData.append('source_node_id',  selectedImportNodeId);
        formData.append('target_parent_id', targetParentId);
        formData.append('target_course_id', targetCourseId);

        fetch('/api/builder/import/node/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf() },
            body: formData,
        })
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                showToast(res.message);
                closeModal();
                // Reload the main builder tree
                const builderCourseSelect = document.getElementById('builder-course-select');
                if (builderCourseSelect && builderCourseSelect.value) {
                    // Trigger the builder reload by dispatching a change event (the builder listens via jQuery)
                    $(builderCourseSelect).trigger('change');
                }
            } else {
                showToast('\u26a0 ' + res.message);
                btnConfirm.disabled       = false;
                btnConfirmLbl.textContent = 'Confirm Import';
            }
        })
        .catch(() => {
            showToast('Network error during import.');
            btnConfirm.disabled       = false;
            btnConfirmLbl.textContent = 'Confirm Import';
        });
    }

    // ── Event listeners ───────────────────────────────────────────────────────
    btnOpen.addEventListener('click', openModal);
    btnClose.addEventListener('click', closeModal);
    btnCancel.addEventListener('click', closeModal);
    btnConfirm.addEventListener('click', confirmImport);

    // Close on backdrop click
    modal.addEventListener('click', e => {
        if (e.target === modal) closeModal();
    });

    // Close on Escape
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && modal.style.display === 'flex') closeModal();
    });

    // Course dropdown change → load source tree
    courseSelect.addEventListener('change', e => {
        selectedImportNodeId    = null;
        selectedImportNodeTitle = null;
        badge.style.display    = 'none';
        destInfo.style.display = 'none';
        btnConfirm.disabled    = true;
        loadImportTree(e.target.value);
    });
}

