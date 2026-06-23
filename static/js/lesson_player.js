/* script.js */
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initComments();
});

// --- YouTube API & Custom Player Logic ---

// 1. Load the YouTube IFrame Player API asynchronously.
const tag = document.createElement('script');
tag.src = "https://www.youtube.com/iframe_api";
const firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

let player;
let progressInterval;
let isDraggingProgress = false;
let isDraggingVolume = false;

// 2. This function creates an <iframe> (and YouTube player) after the API code downloads.
window.onYouTubeIframeAPIReady = function () {
    player = new YT.Player('yt-player', {
        height: '100%',
        width: '100%',
        // Put your unlisted YouTube video ID here:
        videoId: 'mLA4cC57muk', // Our example video ID
        playerVars: {
            'playsinline': 1,
            'controls': 0, // Hide YouTube controls
            'disablekb': 1, // Disable YouTube keyboard controls
            'fs': 0, // Disable YouTube fullscreen button
            'rel': 0, // Don't show related videos
            'modestbranding': 1, // Minimal YouTube branding
            'iv_load_policy': 3 // Hide annotations
        },
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange
        }
    });
};

function onPlayerReady(event) {
    initCustomControls();
    updateTimeDisplay();
}

function onPlayerStateChange(event) {
    const videoContainer = document.getElementById('custom-video-container');
    const playIcon = document.getElementById('play-icon');

    // Remove all states
    videoContainer.classList.remove('paused', 'playing', 'buffering', 'ended');

    if (event.data == YT.PlayerState.PLAYING) {
        videoContainer.classList.add('playing');
        playIcon.className = 'fas fa-pause';

        // Start updating progress
        clearInterval(progressInterval);
        progressInterval = setInterval(updateProgressBar, 100);

    } else if (event.data == YT.PlayerState.PAUSED || event.data == YT.PlayerState.UNSTARTED) {
        videoContainer.classList.add('paused');
        playIcon.className = 'fas fa-play';
        clearInterval(progressInterval);

    } else if (event.data == YT.PlayerState.BUFFERING) {
        videoContainer.classList.add('buffering');
        clearInterval(progressInterval);

    } else if (event.data == YT.PlayerState.ENDED) {
        videoContainer.classList.add('ended');
        playIcon.className = 'fas fa-redo';
        clearInterval(progressInterval);
    }
}

function initCustomControls() {
    const videoContainer = document.getElementById('custom-video-container');
    const overlay = document.getElementById('video-overlay');
    const playPauseBtn = document.getElementById('play-pause-btn');

    // Play / Pause toggling
    const togglePlay = () => {
        if (!player || !player.getPlayerState) return;
        const state = player.getPlayerState();
        if (state === YT.PlayerState.PLAYING) {
            player.pauseVideo();
        } else {
            player.playVideo();
        }
    };

    overlay.addEventListener('click', togglePlay);
    playPauseBtn.addEventListener('click', togglePlay);

    // Volume Control
    const muteBtn = document.getElementById('mute-btn');
    const volumeIcon = document.getElementById('volume-icon');
    const volumeWrapper = document.getElementById('volume-slider-wrapper');
    const volumeFilled = document.getElementById('volume-filled');

    let lastVolume = 100;

    const updateVolumeUI = (vol) => {
        volumeFilled.style.width = `${vol}%`;
        if (vol === 0) volumeIcon.className = 'fas fa-volume-mute';
        else if (vol < 50) volumeIcon.className = 'fas fa-volume-down';
        else volumeIcon.className = 'fas fa-volume-up';
    };

    muteBtn.addEventListener('click', () => {
        if (player.isMuted() || player.getVolume() === 0) {
            player.unMute();
            player.setVolume(lastVolume);
            updateVolumeUI(lastVolume);
        } else {
            lastVolume = player.getVolume();
            player.setVolume(0);
            updateVolumeUI(0);
        }
    });

    // Volume Slider dragging
    const setVolumeFromMouse = (e) => {
        const rect = volumeWrapper.getBoundingClientRect();
        let pos = (e.clientX - rect.left) / rect.width;
        pos = Math.max(0, Math.min(1, pos));
        const newVol = Math.round(pos * 100);
        player.setVolume(newVol);
        if (newVol > 0) player.unMute();
        updateVolumeUI(newVol);
    };

    volumeWrapper.addEventListener('mousedown', (e) => {
        isDraggingVolume = true;
        setVolumeFromMouse(e);
    });

    document.addEventListener('mousemove', (e) => {
        if (isDraggingVolume) setVolumeFromMouse(e);
    });

    document.addEventListener('mouseup', () => {
        isDraggingVolume = false;
    });

    // Init volume UI
    setTimeout(() => {
        if (player && player.getVolume) {
            const initialVol = player.getVolume();
            updateVolumeUI(initialVol);
        }
    }, 500);

    // Progress Bar
    const progressContainer = document.getElementById('progress-container');

    const seekFromMouse = (e) => {
        const rect = progressContainer.getBoundingClientRect();
        let pos = (e.clientX - rect.left) / rect.width;
        pos = Math.max(0, Math.min(1, pos));
        const duration = player.getDuration();
        if (duration) {
            player.seekTo(pos * duration, true);
            updateProgressBar(pos);
        }
    };

    progressContainer.addEventListener('mousedown', (e) => {
        isDraggingProgress = true;
        clearInterval(progressInterval);
        seekFromMouse(e);
    });

    document.addEventListener('mousemove', (e) => {
        if (isDraggingProgress) {
            const rect = progressContainer.getBoundingClientRect();
            let pos = (e.clientX - rect.left) / rect.width;
            pos = Math.max(0, Math.min(1, pos));
            // Just update UI visually while dragging, don't spam API
            document.getElementById('progress-filled').style.width = `${pos * 100}%`;
            document.getElementById('progress-thumb').style.left = `${pos * 100}%`;
        }
    });

    document.addEventListener('mouseup', (e) => {
        if (isDraggingProgress) {
            isDraggingProgress = false;
            seekFromMouse(e); // Final seek
            if (player.getPlayerState() === YT.PlayerState.PLAYING) {
                progressInterval = setInterval(updateProgressBar, 100);
            }
        }
    });

    // Speed Menu
    const speedBtn = document.getElementById('speed-btn');
    const speedMenu = document.getElementById('speed-menu');
    const speedOptions = document.querySelectorAll('.speed-option');

    speedBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        speedMenu.classList.toggle('show');
    });

    document.addEventListener('click', () => {
        speedMenu.classList.remove('show');
    });

    speedOptions.forEach(opt => {
        opt.addEventListener('click', (e) => {
            const speed = parseFloat(e.target.getAttribute('data-speed'));
            player.setPlaybackRate(speed);

            // Update UI
            speedOptions.forEach(o => o.classList.remove('active'));
            e.target.classList.add('active');
            speedBtn.textContent = e.target.textContent === 'Normal' ? '1x' : e.target.textContent;
        });
    });

    // Fullscreen
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    fullscreenBtn.addEventListener('click', () => {
        if (!document.fullscreenElement) {
            videoContainer.requestFullscreen().catch(err => {
                console.error(`Error attempting to enable fullscreen: ${err.message}`);
            });
        } else {
            document.exitFullscreen();
        }
    });

    document.addEventListener('fullscreenchange', () => {
        if (document.fullscreenElement) {
            videoContainer.classList.add('fullscreen-mode');
            fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i>';
        } else {
            videoContainer.classList.remove('fullscreen-mode');
            fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Block shortcuts if user is typing a comment
        if (document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'INPUT') return;

        // Only run shortcuts if video container is visible in viewport roughly
        const rect = videoContainer.getBoundingClientRect();
        if (rect.bottom < 0 || rect.top > window.innerHeight) return;

        switch (e.key.toLowerCase()) {
            case ' ':
            case 'k':
                e.preventDefault();
                togglePlay();
                break;
            case 'j':
                player.seekTo(player.getCurrentTime() - 10, true);
                break;
            case 'l':
                player.seekTo(player.getCurrentTime() + 10, true);
                break;
            case 'arrowleft':
                player.seekTo(player.getCurrentTime() - 5, true);
                break;
            case 'arrowright':
                player.seekTo(player.getCurrentTime() + 5, true);
                break;
            case 'arrowup':
                e.preventDefault();
                let volUp = Math.min(100, player.getVolume() + 5);
                player.setVolume(volUp);
                if (volUp > 0) player.unMute();
                updateVolumeUI(volUp);
                break;
            case 'arrowdown':
                e.preventDefault();
                let volDown = Math.max(0, player.getVolume() - 5);
                player.setVolume(volDown);
                if (volDown === 0) player.mute();
                updateVolumeUI(volDown);
                break;
            case 'm':
                muteBtn.click();
                break;
            case 'f':
                fullscreenBtn.click();
                break;
            case '>':
                if (e.shiftKey) {
                    const currentRate = player.getPlaybackRate();
                    const availableRates = player.getAvailablePlaybackRates();
                    const idx = availableRates.indexOf(currentRate);
                    if (idx < availableRates.length - 1) {
                        const newRate = availableRates[idx + 1];
                        player.setPlaybackRate(newRate);
                        updateSpeedUI(newRate);
                    }
                }
                break;
            case '<':
                if (e.shiftKey) {
                    const currentRate = player.getPlaybackRate();
                    const availableRates = player.getAvailablePlaybackRates();
                    const idx = availableRates.indexOf(currentRate);
                    if (idx > 0) {
                        const newRate = availableRates[idx - 1];
                        player.setPlaybackRate(newRate);
                        updateSpeedUI(newRate);
                    }
                }
                break;
        }
    });
}

function updateSpeedUI(rate) {
    const speedBtn = document.getElementById('speed-btn');
    const speedOptions = document.querySelectorAll('.speed-option');
    speedOptions.forEach(opt => {
        opt.classList.remove('active');
        if (parseFloat(opt.getAttribute('data-speed')) === rate) {
            opt.classList.add('active');
            speedBtn.textContent = opt.textContent === 'Normal' ? '1x' : opt.textContent;
        }
    });
}

function updateProgressBar(forcedPos = null) {
    if (!player || !player.getDuration) return;

    let pos = forcedPos;
    if (pos === null) {
        const duration = player.getDuration();
        const current = player.getCurrentTime();
        if (duration > 0) {
            pos = current / duration;
        } else {
            pos = 0;
        }
    }

    // Visual update
    document.getElementById('progress-filled').style.width = `${pos * 100}%`;
    document.getElementById('progress-thumb').style.left = `${pos * 100}%`;

    updateTimeDisplay();
}

function updateTimeDisplay() {
    if (!player || !player.getDuration) return;

    let duration = 0;
    try {
        duration = player.getDuration() || 0;
    } catch (e) { }

    let current = 0;
    try {
        current = player.getCurrentTime() || 0;
    } catch (e) { }

    document.getElementById('current-time').textContent = formatTime(current);
    document.getElementById('total-time').textContent = formatTime(duration);
}

function formatTime(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}:${sec < 10 ? '0' : ''}${sec}`;
}


// --- Original Application Logic ---

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');

            const tabId = btn.getAttribute('data-tab');
            document.getElementById(`tab-${tabId}`).classList.add('active');
        });
    });
}

function initComments() {
    const commentForm = document.getElementById('comment-form');
    const commentInput = document.getElementById('comment-input');
    const commentsContainer = document.getElementById('comments-container');
    const commentCountElement = document.getElementById('comment-count');

    if (!commentForm) return;

    let commentCount = 12; // Static init count

    commentForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const text = commentInput.value.trim();
        if (!text) return;

        const newComment = document.createElement('div');
        newComment.className = 'comment-item';

        newComment.innerHTML = `
            <img src="https://ui-avatars.com/api/?name=You&background=778873&color=fff" alt="User" class="avatar-small">
            <div class="comment-content">
                <div class="comment-header">
                    <span class="comment-author">You</span>
                    <span class="comment-role badge">Student</span>
                    <span class="comment-time">Just now</span>
                </div>
                <p class="comment-text">${escapeHTML(text)}</p>
                <div class="comment-actions">
                    <button class="action-btn"><i class="far fa-thumbs-up"></i> 0</button>
                    <button class="action-btn"><i class="far fa-comment"></i> Reply</button>
                </div>
            </div>
        `;

        const pinnedComment = commentsContainer.querySelector('.pinned');
        if (pinnedComment) {
            pinnedComment.insertAdjacentElement('afterend', newComment);
        } else {
            commentsContainer.prepend(newComment);
        }

        commentCount++;
        commentCountElement.textContent = commentCount;
        commentInput.value = '';
        newComment.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });

    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g,
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag])
        );
    }
}
