/**
 * Lesson Player JS - adapted for Django LMS
 * Integrates YouTube IFrame API with custom controls + AJAX live comments
 */

// --- YouTube Player Setup ---
let player;
let playerReady = false;
let isDragging = false;
let progressInterval;
let lastCommentTimestamp = null;
let commentPollInterval;

function onYouTubeIframeAPIReady() {
    const videoId = extractVideoId(LESSON_EMBED_URL);
    if (!videoId) return;

    player = new YT.Player('yt-player', {
        videoId: videoId,
        playerVars: {
            controls: 0,
            disablekb: 1,
            modestbranding: 1,
            rel: 0,
            showinfo: 0,
            fs: 0,
        },
        events: {
            onReady: onPlayerReady,
            onStateChange: onPlayerStateChange,
        }
    });
}

function extractVideoId(url) {
    const patterns = [
        /[?&]v=([^&#]+)/,
        /youtube\.com\/embed\/([^/?]+)/,
        /youtu\.be\/([^/?]+)/,
    ];
    for (const p of patterns) {
        const m = url.match(p);
        if (m) return m[1];
    }
    return null;
}

function onPlayerReady(event) {
    playerReady = true;
    const videoContainer = document.getElementById('custom-video-container');
    const totalTimeEl = document.getElementById('total-time');

    // Set total duration
    const duration = player.getDuration();
    totalTimeEl.textContent = formatTime(duration);

    // Volume fill init
    updateVolumeFill(player.getVolume());

    // Mark as paused by default
    videoContainer.classList.add('paused');

    // Start progress tracking
    progressInterval = setInterval(updateProgress, 500);
}

function onPlayerStateChange(event) {
    const videoContainer = document.getElementById('custom-video-container');
    const playIcon = document.getElementById('play-icon');

    if (event.data === YT.PlayerState.PLAYING) {
        videoContainer.classList.remove('paused', 'ended', 'buffering');
        playIcon.classList.replace('fa-play', 'fa-pause');
    } else if (event.data === YT.PlayerState.PAUSED) {
        videoContainer.classList.add('paused');
        videoContainer.classList.remove('ended', 'buffering');
        playIcon.classList.replace('fa-pause', 'fa-play');
    } else if (event.data === YT.PlayerState.ENDED) {
        videoContainer.classList.add('ended', 'paused');
        playIcon.classList.replace('fa-pause', 'fa-play');
    } else if (event.data === YT.PlayerState.BUFFERING) {
        videoContainer.classList.add('buffering');
        videoContainer.classList.remove('paused');
    }
}

let estimatedLiveEdge = null;
let lastRealTime = null;

function updateProgress() {
    if (!playerReady) return;
    const current = player.getCurrentTime();
    let duration = player.getDuration();
    let pct = 0;

    if (typeof IS_LIVE !== 'undefined' && IS_LIVE) {
        const now = Date.now() / 1000;
        
        if (estimatedLiveEdge === null) {
            estimatedLiveEdge = current;
        } else {
            if (current > estimatedLiveEdge) {
                estimatedLiveEdge = current;
            } else if (lastRealTime !== null) {
                estimatedLiveEdge += (now - lastRealTime);
            }
        }
        lastRealTime = now;
        
        pct = estimatedLiveEdge > 0 ? (current / estimatedLiveEdge) * 100 : 0;
        if (pct > 100) pct = 100;
        
        document.getElementById('total-time').textContent = formatTime(estimatedLiveEdge);
        
        const syncBtn = document.getElementById('live-sync-btn');
        if (syncBtn) {
            if (estimatedLiveEdge - current <= 15) {
                syncBtn.classList.add('active');
            } else {
                syncBtn.classList.remove('active');
            }
        }
    } else {
        pct = duration > 0 ? (current / duration) * 100 : 0;
        document.getElementById('total-time').textContent = formatTime(duration);
    }

    document.getElementById('progress-filled').style.width = pct + '%';
    document.getElementById('progress-thumb').style.left = pct + '%';
    document.getElementById('current-time').textContent = formatTime(current);
}

function syncToLive() {
    if (!playerReady) return;
    // Seeking to a very large number forces YouTube API to jump to the actual live edge
    player.seekTo(999999, true);
    if (player.getPlayerState() !== YT.PlayerState.PLAYING) {
        player.playVideo();
    }
}

function formatTime(secs) {
    secs = Math.floor(secs || 0);
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) {
        return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
    return `${m}:${String(s).padStart(2, '0')}`;
}

// --- Controls Setup ---
document.addEventListener('DOMContentLoaded', () => {
    // Overlay click → play/pause
    document.getElementById('video-overlay').addEventListener('click', togglePlay);
    document.getElementById('play-pause-btn').addEventListener('click', togglePlay);

    // Mute
    document.getElementById('mute-btn').addEventListener('click', () => {
        if (!playerReady) return;
        if (player.isMuted()) {
            player.unMute();
            document.getElementById('volume-icon').className = 'fas fa-volume-up';
        } else {
            player.mute();
            document.getElementById('volume-icon').className = 'fas fa-volume-mute';
        }
    });

    // Volume slider click
    const volumeWrapper = document.getElementById('volume-slider-wrapper');
    volumeWrapper.addEventListener('click', e => {
        if (!playerReady) return;
        const rect = volumeWrapper.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        const vol = Math.max(0, Math.min(100, Math.round(pct * 100)));
        player.setVolume(vol);
        if (vol > 0) player.unMute();
        updateVolumeFill(vol);
    });

    // Progress bar click
    const progressCont = document.getElementById('progress-container');
    progressCont.addEventListener('click', e => {
        if (!playerReady) return;
        const rect = progressCont.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        let seekDuration = player.getDuration();
        if (typeof IS_LIVE !== 'undefined' && IS_LIVE && estimatedLiveEdge !== null) {
            seekDuration = estimatedLiveEdge;
        }
        player.seekTo(pct * seekDuration, true);
    });

    document.getElementById('speed-select').addEventListener('change', e => {
        if (playerReady) player.setPlaybackRate(parseFloat(e.target.value));
    });

    document.getElementById('quality-select').addEventListener('change', e => {
        if (playerReady && typeof player.setPlaybackQuality === 'function') {
            player.setPlaybackQuality(e.target.value);
        }
    });

    // Fullscreen
    document.getElementById('fullscreen-btn').addEventListener('click', () => {
        const container = document.getElementById('custom-video-container');
        if (!document.fullscreenElement) {
            container.requestFullscreen?.();
            document.getElementById('fullscreen-btn').querySelector('i').className = 'fas fa-compress';
        } else {
            document.exitFullscreen?.();
            document.getElementById('fullscreen-btn').querySelector('i').className = 'fas fa-expand';
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
        if (!playerReady) return;
        if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
        switch(e.key) {
            case ' ': case 'k': e.preventDefault(); togglePlay(); break;
            case 'f': document.getElementById('fullscreen-btn').click(); break;
            case 'm': document.getElementById('mute-btn').click(); break;
            case 'j': player.seekTo(player.getCurrentTime() - 10, true); break;
            case 'l': player.seekTo(player.getCurrentTime() + 10, true); break;
            case 'ArrowLeft': player.seekTo(player.getCurrentTime() - 5, true); break;
            case 'ArrowRight': player.seekTo(player.getCurrentTime() + 5, true); break;
            case 'ArrowUp': e.preventDefault(); player.setVolume(Math.min(100, player.getVolume() + 10)); break;
            case 'ArrowDown': e.preventDefault(); player.setVolume(Math.max(0, player.getVolume() - 10)); break;
        }
    });

    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        });
    });

    // Live comments - load history then open WebSocket
    if (IS_LIVE && LIVE_NODE_ID) {
        startCommentPolling();
    }
});

function togglePlay() {
    if (!playerReady) return;
    if (player.getPlayerState() === YT.PlayerState.PLAYING) {
        player.pauseVideo();
    } else {
        player.playVideo();
    }
}

function updateVolumeFill(vol) {
    document.getElementById('volume-filled').style.width = vol + '%';
}

// --- WebSocket Live Comments & Viewer Count ---
let liveSocket = null;
const seenCommentIds = new Set();

function startCommentPolling() {
    if (!LIVE_NODE_ID) return;

    // Step 1: Fetch all existing comments from the database
    fetch(`/live/comments/${LIVE_NODE_ID}/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(r => r.json())
    .then(data => {
        if (data.comments && data.comments.length > 0) {
            data.comments.forEach(c => {
                seenCommentIds.add(c.id);
                appendComment(c, false); // no fade-in animation for historical comments
            });
        }
    })
    .catch(err => console.error('Failed to load past comments:', err))
    .finally(() => {
        // Step 2: Open WebSocket for new real-time comments
        openLiveSocket();
    });
}

function openLiveSocket() {
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${wsScheme}://${window.location.host}/ws/live/${LIVE_NODE_ID}/`;

    liveSocket = new WebSocket(wsUrl);

    liveSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.type === 'comment') {
            // Deduplicate: skip if we already rendered this from the initial AJAX fetch
            if (data.comment.id && seenCommentIds.has(data.comment.id)) return;
            if (data.comment.id) seenCommentIds.add(data.comment.id);
            appendComment(data.comment, true);
        } else if (data.type === 'viewer_count') {
            const viewerEl = document.getElementById('live-viewer-count');
            if (viewerEl) {
                viewerEl.textContent = data.count + ' Watching';
            }
        }
    };

    liveSocket.onclose = function(e) {
        console.error('Live socket closed unexpectedly');
        if (!COMMENTS_ALLOWED) {
            const inputArea = document.querySelector('.comment-input-area');
            if (inputArea) {
                inputArea.innerHTML = `
                    <div style="width:100%; padding: 1rem; background:#fef3c7; border-radius:8px; border:1px solid #fcd34d; color:#92400e; font-size:0.875rem; display:flex; align-items:center; gap:0.5rem;">
                        <i class="fas fa-lock"></i>
                        <span>Comments are closed - this session has ended or connection lost.</span>
                    </div>`;
            }
        }
    };
}

function appendComment(comment, isNew = true) {
    const container = document.getElementById('comments-container');
    const div = document.createElement('div');
    div.className = 'comment-item' + (isNew ? ' animate-fade-in' : '');
    div.innerHTML = `
        <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(comment.author)}&background=778873&color=fff"
             alt="${comment.author}" class="avatar-small">
        <div class="comment-content">
            <div class="comment-header">
                <span class="comment-author">${comment.author}</span>
                <span class="comment-role badge">Student</span>
                <span class="comment-time">${comment.time_display}</span>
            </div>
            <p class="comment-text">${escapeHtml(comment.text)}</p>
        </div>
    `;
    container.appendChild(div);
    const countEl = document.getElementById('comment-count');
    if (countEl) countEl.textContent = parseInt(countEl.textContent || 0) + 1;
    container.scrollTop = container.scrollHeight;
}

function postComment() {
    if (!COMMENTS_ALLOWED || !liveSocket || liveSocket.readyState !== WebSocket.OPEN) return;
    const input = document.getElementById('comment-input');
    const text = input.value.trim();
    if (!text) return;

    liveSocket.send(JSON.stringify({
        'type': 'comment',
        'text': text
    }));

    input.value = '';
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

// ─────────────────────────────────────────────
// AI Assistant Javascript Logic
// ─────────────────────────────────────────────

let activeAIType = null;
let aiDataCache = {}; // Cache to hold fetched/generated data
let currentFlashcardIndex = 0;
let currentMCQIndex = 0;
let mcqUserAnswers = []; // Array to store user selections (null if not answered)
let mcqScore = { correct: 0, wrong: 0 };

document.addEventListener('DOMContentLoaded', () => {
    // Check initial status of generated AI contents for the current class
    if (typeof LIVE_NODE_ID !== 'undefined' && LIVE_NODE_ID) {
        checkAIStatus();
    }
});

function checkAIStatus() {
    fetch(`/node/${LIVE_NODE_ID}/ai/status/`)
        .then(r => r.json())
        .then(data => {
            if (data.ok && data.status) {
                Object.keys(data.status).forEach(type => {
                    const btn = document.getElementById(`btn-ai-${type}`);
                    if (btn) {
                        btn.style.borderColor = 'var(--success-color)';
                        btn.style.backgroundColor = 'rgba(16, 185, 129, 0.03)';
                        const btnText = btn.querySelector('.btn-text');
                        if (btnText) {
                            if (type === 'notes') btnText.textContent = 'Read notes';
                            if (type === 'flashcards') btnText.textContent = 'Answer flashcards';
                            if (type === 'mcqs') btnText.textContent = 'Answer MCQs';
                            if (type === 'summary') btnText.textContent = 'Read summary';
                            if (type === 'next_topics') btnText.textContent = 'View next topics';
                        }
                    }
                });
            }
        })
        .catch(err => console.error('Error checking AI status:', err));
}

function openAIModal(type) {
    activeAIType = type;
    const modal = document.getElementById('ai-modal');
    const titleEl = document.getElementById('ai-modal-title');
    const contentEl = document.getElementById('ai-modal-content');
    const loadingEl = document.getElementById('ai-modal-loading');
    const emptyEl = document.getElementById('ai-modal-empty');
    const timestampEl = document.getElementById('ai-timestamp');
    const regenBtn = document.getElementById('ai-regenerate-btn');

    // Set title
    const titles = {
        'notes': 'Class Notes',
        'flashcards': 'Interactive Flashcards',
        'mcqs': 'Board Competitive MCQs',
        'summary': 'Class Summary',
        'next_topics': 'Suggested Next Topics'
    };
    titleEl.textContent = titles[type] || 'AI Study Assistant';

    // Show modal
    modal.classList.add('active');
    
    // Reset views
    contentEl.style.display = 'none';
    loadingEl.style.display = 'none';
    emptyEl.style.display = 'none';
    regenBtn.style.display = 'none';
    timestampEl.textContent = '';

    // Check cache first
    if (aiDataCache[type]) {
        renderAIContent(type, aiDataCache[type]);
        regenBtn.style.display = 'inline-flex';
        return;
    }

    // Fetch from server
    loadingEl.style.display = 'flex';
    fetch(`/node/${LIVE_NODE_ID}/ai/${type}/`)
        .then(r => r.json())
        .then(data => {
            loadingEl.style.display = 'none';
            if (data.ok) {
                aiDataCache[type] = data;
                renderAIContent(type, data);
                regenBtn.style.display = 'inline-flex';
            } else {
                // Not generated yet
                emptyEl.style.display = 'flex';
                document.getElementById('empty-title').textContent = `${titles[type]} Not Generated`;
                document.getElementById('empty-desc').textContent = `Would you like the AI to generate custom ${titles[type].toLowerCase()} from this class's resources & attachments?`;
            }
        })
        .catch(err => {
            loadingEl.style.display = 'none';
            emptyEl.style.display = 'flex';
            document.getElementById('empty-title').textContent = 'Error Loading Content';
            document.getElementById('empty-desc').textContent = 'Could not fetch content. Please try again later.';
            console.error('Error fetching AI content:', err);
        });
}

function closeAIModal() {
    const modal = document.getElementById('ai-modal');
    modal.classList.remove('active');
    activeAIType = null;
}

function generateAIContent() {
    if (!activeAIType) return;

    const loadingEl = document.getElementById('ai-modal-loading');
    const emptyEl = document.getElementById('ai-modal-empty');
    const contentEl = document.getElementById('ai-modal-content');
    const regenBtn = document.getElementById('ai-regenerate-btn');

    emptyEl.style.display = 'none';
    contentEl.style.display = 'none';
    regenBtn.style.display = 'none';
    loadingEl.style.display = 'flex';

    // Show inline spin status on main button
    const statusSpin = document.getElementById(`status-${activeAIType}`);
    if (statusSpin) statusSpin.style.display = 'block';

    const csrf = CSRF_TOKEN || document.querySelector('[name=csrfmiddlewaretoken]')?.value || "";

    fetch(`/node/${LIVE_NODE_ID}/ai/${activeAIType}/generate/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf
        }
    })
    .then(r => r.json())
    .then(data => {
        loadingEl.style.display = 'none';
        if (statusSpin) statusSpin.style.display = 'none';

        if (data.ok) {
            aiDataCache[activeAIType] = data;
            renderAIContent(activeAIType, data);
            regenBtn.style.display = 'inline-flex';
            checkAIStatus(); // Update button status on the main page
        } else {
            emptyEl.style.display = 'flex';
            document.getElementById('empty-title').textContent = 'Generation Failed';
            document.getElementById('empty-desc').textContent = data.error || 'The AI encountered an issue generating this content.';
        }
    })
    .catch(err => {
        loadingEl.style.display = 'none';
        if (statusSpin) statusSpin.style.display = 'none';
        emptyEl.style.display = 'flex';
        document.getElementById('empty-title').textContent = 'Connection Error';
        document.getElementById('empty-desc').textContent = 'An error occurred while connecting to the server. Please try again.';
        console.error('Error generating AI content:', err);
    });
}

function renderAIContent(type, data) {
    const contentEl = document.getElementById('ai-modal-content');
    const timestampEl = document.getElementById('ai-timestamp');
    
    contentEl.innerHTML = '';
    contentEl.style.display = 'block';
    
    if (data.generated_at) {
        timestampEl.textContent = `Generated on: ${data.generated_at}`;
    } else {
        timestampEl.textContent = 'Generated just now';
    }

    if (type === 'notes' || type === 'summary') {
        const text = data.content.text || '';
        const notesDiv = document.createElement('div');
        notesDiv.className = 'ai-notes-view';
        notesDiv.innerHTML = formatSimpleMarkdown(text);
        contentEl.appendChild(notesDiv);
    } else if (type === 'flashcards') {
        currentFlashcardIndex = 0;
        renderFlashcardWidget(data.content);
    } else if (type === 'mcqs') {
        currentMCQIndex = 0;
        mcqScore = { correct: 0, wrong: 0 };
        mcqUserAnswers = new Array(data.content.length).fill(null);
        renderMCQWidget(data.content);
    } else if (type === 'next_topics') {
        renderRoadmapWidget(data.content);
    }
}

// Simple parser for standard markdown features
function formatSimpleMarkdown(text) {
    let html = escapeHtml(text);
    
    // Headings
    html = html.replace(/^### (.*?)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^# (.*?)$/gm, '<h2>$1</h2>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Unordered Lists
    let inList = false;
    const lines = html.split('\n');
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith('* ') || line.startsWith('- ')) {
            const content = line.substring(2);
            if (!inList) {
                lines[i] = '<ul><li>' + content + '</li>';
                inList = true;
            } else {
                lines[i] = '<li>' + content + '</li>';
            }
        } else {
            if (inList) {
                lines[i - 1] = lines[i - 1] + '</ul>';
                inList = false;
            }
        }
    }
    if (inList) {
        lines[lines.length - 1] = lines[lines.length - 1] + '</ul>';
    }
    html = lines.join('\n');
    
    // Paragraphs
    html = html.split('\n\n').map(p => {
        p = p.trim();
        if (p && !p.startsWith('<h') && !p.startsWith('<ul') && !p.startsWith('<li')) {
            return '<p>' + p.replace(/\n/g, '<br>') + '</p>';
        }
        return p;
    }).join('\n');
    
    return html;
}

// Interactive Flashcard Widget
function renderFlashcardWidget(cards) {
    if (!cards || !cards.length) {
        document.getElementById('ai-modal-content').innerHTML = '<p>No flashcards found.</p>';
        return;
    }

    const container = document.getElementById('ai-modal-content');
    
    const wrapper = document.createElement('div');
    wrapper.className = 'flashcard-wrapper';
    
    wrapper.innerHTML = `
        <div class="flashcard-container" onclick="toggleCardFlip()">
            <div class="flashcard" id="flashcard-element">
                <div class="flashcard-front">
                    <span class="card-label">Question</span>
                    <p class="card-text" id="card-question"></p>
                    <span class="card-hint"><i class="fas fa-sync-alt"></i> Click to reveal answer</span>
                </div>
                <div class="flashcard-back">
                    <span class="card-label">Answer</span>
                    <p class="card-text" id="card-answer"></p>
                    <span class="card-hint"><i class="fas fa-sync-alt"></i> Click to see question</span>
                </div>
            </div>
        </div>
        <div class="flashcard-controls">
            <button class="ai-outline-btn" id="btn-card-prev" onclick="changeFlashcard(-1)"><i class="fas fa-arrow-left"></i> Prev</button>
            <span class="flashcard-status-text" id="card-status-text">Card 1 of 10</span>
            <button class="ai-outline-btn" id="btn-card-next" onclick="changeFlashcard(1)">Next <i class="fas fa-arrow-right"></i></button>
        </div>
    `;
    
    container.appendChild(wrapper);
    updateFlashcardContent(cards);
}

window.toggleCardFlip = function() {
    const card = document.getElementById('flashcard-element');
    if (card) {
        card.classList.toggle('flipped');
    }
};

window.changeFlashcard = function(dir) {
    const cards = aiDataCache['flashcards'].content;
    const card = document.getElementById('flashcard-element');
    
    // Reset flipped state first
    if (card) card.classList.remove('flipped');
    
    setTimeout(() => {
        currentFlashcardIndex += dir;
        if (currentFlashcardIndex < 0) currentFlashcardIndex = cards.length - 1;
        if (currentFlashcardIndex >= cards.length) currentFlashcardIndex = 0;
        updateFlashcardContent(cards);
    }, card ? 150 : 0);
};

function updateFlashcardContent(cards) {
    const card = cards[currentFlashcardIndex];
    document.getElementById('card-question').textContent = card.question;
    document.getElementById('card-answer').textContent = card.answer;
    document.getElementById('card-status-text').textContent = `Card ${currentFlashcardIndex + 1} of ${cards.length}`;
}

// Interactive MCQ Widget
function renderMCQWidget(mcqs) {
    if (!mcqs || !mcqs.length) {
        document.getElementById('ai-modal-content').innerHTML = '<p>No MCQs found.</p>';
        return;
    }

    const container = document.getElementById('ai-modal-content');
    const mcqDiv = document.createElement('div');
    mcqDiv.className = 'mcq-container';
    
    mcqDiv.innerHTML = `
        <div class="mcq-header">
            <span class="mcq-progress" id="mcq-progress">Question 1 of 10</span>
            <span class="mcq-score" id="mcq-score">Score: 0/0</span>
        </div>
        <div class="mcq-question" id="mcq-question-text"></div>
        <div class="mcq-options" id="mcq-options-list"></div>
        <div class="mcq-explanation" id="mcq-explanation-panel" style="display: none;">
            <div class="explanation-title">Explanation</div>
            <p class="explanation-text" id="mcq-explanation-text"></p>
        </div>
        <div class="mcq-controls">
            <button class="ai-outline-btn" id="btn-mcq-prev" onclick="changeMCQ(-1)" style="margin-right: auto;"><i class="fas fa-arrow-left"></i> Prev</button>
            <button class="ai-outline-btn" id="btn-mcq-next" onclick="changeMCQ(1)">Next <i class="fas fa-arrow-right"></i></button>
        </div>
    `;
    
    container.appendChild(mcqDiv);
    updateMCQContent(mcqs);
}

window.changeMCQ = function(dir) {
    const mcqs = aiDataCache['mcqs'].content;
    currentMCQIndex += dir;
    if (currentMCQIndex < 0) currentMCQIndex = mcqs.length - 1;
    if (currentMCQIndex >= mcqs.length) currentMCQIndex = 0;
    updateMCQContent(mcqs);
};

function updateMCQContent(mcqs) {
    const q = mcqs[currentMCQIndex];
    document.getElementById('mcq-question-text').textContent = `${currentMCQIndex + 1}. ${q.question}`;
    document.getElementById('mcq-progress').textContent = `Question ${currentMCQIndex + 1} of ${mcqs.length}`;
    
    const optionsContainer = document.getElementById('mcq-options-list');
    optionsContainer.innerHTML = '';
    
    const selectedAnswerIndex = mcqUserAnswers[currentMCQIndex];
    const hasBeenAnswered = selectedAnswerIndex !== null;

    const prefixes = ['A', 'B', 'C', 'D', 'E', 'F'];
    
    q.options.forEach((optText, index) => {
        const optBtn = document.createElement('button');
        optBtn.className = 'mcq-option';
        
        optBtn.innerHTML = `
            <span class="mcq-option-prefix">${prefixes[index]}</span>
            <span class="mcq-option-text">${escapeHtml(optText)}</span>
        `;
        
        if (hasBeenAnswered) {
            optBtn.disabled = true;
            if (index === q.correct) {
                optBtn.classList.add('correct');
            } else if (index === selectedAnswerIndex) {
                optBtn.classList.add('wrong');
            }
        } else {
            optBtn.onclick = () => selectMCQOption(index);
        }
        
        optionsContainer.appendChild(optBtn);
    });

    const expPanel = document.getElementById('mcq-explanation-panel');
    if (hasBeenAnswered) {
        expPanel.style.display = 'block';
        document.getElementById('mcq-explanation-text').textContent = q.explanation || 'No explanation provided.';
    } else {
        expPanel.style.display = 'none';
    }
    
    // Update score text
    const totalAttempted = mcqUserAnswers.filter(x => x !== null).length;
    document.getElementById('mcq-score').textContent = `Score: ${mcqScore.correct}/${totalAttempted}`;
}

window.selectMCQOption = function(optionIndex) {
    const mcqs = aiDataCache['mcqs'].content;
    const q = mcqs[currentMCQIndex];
    
    mcqUserAnswers[currentMCQIndex] = optionIndex;
    
    if (optionIndex === q.correct) {
        mcqScore.correct++;
    } else {
        mcqScore.wrong++;
    }
    
    updateMCQContent(mcqs);
};

// Suggested next topics UI roadmap
function renderRoadmapWidget(topics) {
    if (!topics || !topics.length) {
        document.getElementById('ai-modal-content').innerHTML = '<p>No suggestions available.</p>';
        return;
    }

    const container = document.getElementById('ai-modal-content');
    const roadmap = document.createElement('div');
    roadmap.className = 'roadmap-container';
    
    topics.forEach((topic, index) => {
        const item = document.createElement('div');
        item.className = 'roadmap-item';
        
        item.innerHTML = `
            <div class="roadmap-node">${index + 1}</div>
            <div class="roadmap-content">
                <h4 class="roadmap-title">${escapeHtml(topic.title)}</h4>
                <p class="roadmap-reason">${escapeHtml(topic.reason)}</p>
            </div>
        `;
        
        roadmap.appendChild(item);
    });
    
    container.appendChild(roadmap);
}

