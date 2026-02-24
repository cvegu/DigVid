/**
 * Sonivo — Frontend Application Logic
 * Handles file upload, metadata editing, waveform visualization, 
 * audio preview, and video generation for both single and batch modes.
 */

// ============================================================
// State
// ============================================================

const state = {
    mode: 'single', // 'single' | 'batch'
    single: {
        fileId: null,
        filePath: null,
        duration: 0,
        startSec: 0,
        endSec: 30,
        coverPath: null,
        customCoverFile: null,
        peaks: [],
        audioContext: null,
        audioBuffer: null,
        sourceNode: null,
        isPlaying: false,
    },
    batch: {
        tracks: [], // { fileId, filePath, artist, title, album, duration, coverUrl, coverPath, startSec, endSec, peaks }
        playingIdx: -1, // index of currently playing track, -1 if none
        playCheckInterval: null,
    },
};

// ============================================================
// DOM References
// ============================================================

const $ = (id) => document.getElementById(id);

// Tabs
const tabSingle = $('tab-single');
const tabBatch = $('tab-batch');
const singleMode = $('single-mode');
const batchMode = $('batch-mode');

// Single mode elements
const dropZoneSingle = $('drop-zone-single');
const fileInputSingle = $('file-input-single');
const uploadZoneSingle = $('upload-zone-single');
const editorSingle = $('editor-single');
const coverImgSingle = $('cover-img-single');
const coverInputSingle = $('cover-input-single');
const titleSingle = $('title-single');
const artistSingle = $('artist-single');
const albumSingle = $('album-single');
const durationSingle = $('duration-single');
const waveformCanvas = $('waveform-canvas-single');
const waveformContainer = $('waveform-container-single');
const selectionOverlay = $('selection-overlay-single');
const handleLeft = $('handle-left-single');
const handleRight = $('handle-right-single');
const startTimeInput = $('start-time-single');
const endTimeInput = $('end-time-single');
const segmentDuration = $('segment-duration-single');
const playBtn = $('play-btn-single');
const audioPlayer = $('audio-player-single');
const generateBtnSingle = $('generate-btn-single');
const progressSingle = $('progress-single');
const progressTextSingle = $('progress-text-single');
const progressFillSingle = $('progress-fill-single');
const resultSingle = $('result-single');
const resultVideoSingle = $('result-video-single');
const downloadLinkSingle = $('download-link-single');
const newVideoBtnSingle = $('new-video-btn-single');

// Batch mode elements
const dropZoneBatch = $('drop-zone-batch');
const fileInputBatch = $('file-input-batch');
const uploadZoneBatch = $('upload-zone-batch');
const batchTracksContainer = $('batch-tracks');
const batchActions = $('batch-actions');
const generateBtnBatch = $('generate-btn-batch');
const progressBatch = $('progress-batch');
const batchProgressTitle = $('batch-progress-title');
const batchProgressText = $('batch-progress-text');
const progressFillBatch = $('progress-fill-batch');
const resultBatch = $('result-batch');
const batchResultsList = $('batch-results-list');
const downloadZipBatch = $('download-zip-batch');
const newBatchBtn = $('new-batch-btn');


// ============================================================
// Tab Switching
// ============================================================

tabSingle.addEventListener('click', () => switchMode('single'));
tabBatch.addEventListener('click', () => switchMode('batch'));

function switchMode(mode) {
    state.mode = mode;
    tabSingle.classList.toggle('active', mode === 'single');
    tabBatch.classList.toggle('active', mode === 'batch');
    singleMode.classList.toggle('active', mode === 'single');
    batchMode.classList.toggle('active', mode === 'batch');
}

// ============================================================
// Single Mode — Upload
// ============================================================

// Drag & drop
setupDropZone(dropZoneSingle, (files) => {
    if (files.length > 0) uploadSingleFile(files[0]);
});

fileInputSingle.addEventListener('change', (e) => {
    if (e.target.files.length > 0) uploadSingleFile(e.target.files[0]);
});

async function uploadSingleFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    uploadZoneSingle.querySelector('.upload-area h3').textContent = 'Uploading...';

    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Upload failed');
        }
        const data = await res.json();

        // Store state
        state.single.fileId = data.file_id;
        state.single.filePath = data.filepath;
        state.single.duration = data.duration;
        state.single.coverPath = data.cover_path;
        state.single.endSec = Math.min(30, data.duration);

        // Populate editor
        titleSingle.value = data.title;
        artistSingle.value = data.artist;
        albumSingle.value = data.album;
        durationSingle.value = formatTime(data.duration);
        endTimeInput.value = state.single.endSec.toFixed(1);
        endTimeInput.max = data.duration;
        startTimeInput.max = data.duration;
        updateSegmentDuration();

        // Cover
        if (data.cover_url) {
            coverImgSingle.src = data.cover_url;
            coverImgSingle.style.display = 'block';
        } else {
            coverImgSingle.style.display = 'none';
        }

        // Setup audio player
        audioPlayer.src = `/api/preview-audio/${data.file_id}`;

        // Show editor, hide upload
        uploadZoneSingle.classList.add('hidden');
        editorSingle.classList.remove('hidden');
        resultSingle.classList.add('hidden');
        progressSingle.classList.add('hidden');

        // Load waveform
        loadWaveform(data.file_id);

    } catch (err) {
        alert('Error uploading file: ' + err.message);
        uploadZoneSingle.querySelector('.upload-area h3').textContent = 'Drag your audio file here';
    }
}

// Cover change
coverInputSingle.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        const file = e.target.files[0];
        state.single.customCoverFile = file;
        const url = URL.createObjectURL(file);
        coverImgSingle.src = url;
    }
});

// ============================================================
// Waveform
// ============================================================

async function loadWaveform(fileId) {
    try {
        const res = await fetch(`/api/waveform/${fileId}`);
        const data = await res.json();
        state.single.peaks = data.peaks;
        drawWaveform();
        updateSelection();
    } catch (err) {
        console.error('Waveform error:', err);
    }
}

function drawWaveform() {
    const canvas = waveformCanvas;
    const ctx = canvas.getContext('2d');
    const peaks = state.single.peaks;

    // Set canvas resolution
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    ctx.scale(2, 2);

    const w = rect.width;
    const h = rect.height;
    const barWidth = w / peaks.length;
    const centerY = h / 2;

    ctx.clearRect(0, 0, w, h);

    // Draw bars
    peaks.forEach((peak, i) => {
        const barHeight = Math.max(2, peak * centerY * 0.85);
        const x = i * barWidth;

        // Light bar on dark glass
        const lightness = 70 + (i / peaks.length) * 15;
        ctx.fillStyle = `hsla(0, 0%, ${lightness}%, 0.7)`;

        // Top half
        ctx.fillRect(x, centerY - barHeight, barWidth - 0.5, barHeight);
        // Bottom half (mirrored, slightly shorter)
        ctx.fillRect(x, centerY, barWidth - 0.5, barHeight * 0.7);
    });

    // Center line
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(w, centerY);
    ctx.stroke();
}

function updateSelection() {
    const duration = state.single.duration;
    if (duration <= 0) return;

    const container = waveformContainer;
    const containerWidth = container.offsetWidth;

    const startPct = (state.single.startSec / duration) * 100;
    const endPct = (state.single.endSec / duration) * 100;

    selectionOverlay.style.left = startPct + '%';
    selectionOverlay.style.width = (endPct - startPct) + '%';

    handleLeft.style.left = startPct + '%';
    handleRight.style.left = endPct + '%';
}

function updateSegmentDuration() {
    const dur = state.single.endSec - state.single.startSec;
    segmentDuration.textContent = dur.toFixed(1) + 's';
}

// Time inputs
startTimeInput.addEventListener('input', (e) => {
    let val = parseFloat(e.target.value) || 0;
    val = Math.max(0, Math.min(val, state.single.endSec - 1));
    state.single.startSec = val;
    updateSelection();
    updateSegmentDuration();
});

endTimeInput.addEventListener('input', (e) => {
    let val = parseFloat(e.target.value) || 0;
    val = Math.max(state.single.startSec + 1, Math.min(val, state.single.duration));
    state.single.endSec = val;
    updateSelection();
    updateSegmentDuration();
});

// Handle dragging
let dragging = null;

handleLeft.addEventListener('mousedown', (e) => { dragging = 'left'; e.preventDefault(); });
handleRight.addEventListener('mousedown', (e) => { dragging = 'right'; e.preventDefault(); });

// Also support clicking on the waveform to set position
waveformContainer.addEventListener('mousedown', (e) => {
    if (e.target === handleLeft || e.target === handleRight) return;

    const rect = waveformContainer.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    const time = pct * state.single.duration;

    // Determine which handle is closer
    const distToStart = Math.abs(time - state.single.startSec);
    const distToEnd = Math.abs(time - state.single.endSec);

    if (distToStart < distToEnd) {
        dragging = 'left';
    } else {
        dragging = 'right';
    }

    updateDragPosition(e.clientX);
});

document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    updateDragPosition(e.clientX);
});

document.addEventListener('mouseup', () => {
    dragging = null;
});

function updateDragPosition(clientX) {
    const rect = waveformContainer.getBoundingClientRect();
    let pct = (clientX - rect.left) / rect.width;
    pct = Math.max(0, Math.min(1, pct));
    const time = pct * state.single.duration;

    if (dragging === 'left') {
        state.single.startSec = Math.min(time, state.single.endSec - 1);
        startTimeInput.value = state.single.startSec.toFixed(1);
    } else if (dragging === 'right') {
        state.single.endSec = Math.max(time, state.single.startSec + 1);
        endTimeInput.value = state.single.endSec.toFixed(1);
    }

    updateSelection();
    updateSegmentDuration();
}

// ============================================================
// Audio Preview
// ============================================================

playBtn.addEventListener('click', () => {
    if (state.single.isPlaying) {
        stopAudio();
    } else {
        playAudio();
    }
});

function playAudio() {
    const audio = audioPlayer;
    audio.currentTime = state.single.startSec;
    audio.play();
    state.single.isPlaying = true;
    playBtn.textContent = '⏸ Stop';

    // Stop at end time
    const checkEnd = setInterval(() => {
        if (audio.currentTime >= state.single.endSec || audio.paused) {
            stopAudio();
            clearInterval(checkEnd);
        }
    }, 100);
}

function stopAudio() {
    audioPlayer.pause();
    state.single.isPlaying = false;
    playBtn.textContent = '▶ Play segment';
}

// ============================================================
// Single Mode — Generate Video
// ============================================================

generateBtnSingle.addEventListener('click', generateSingleVideo);

async function generateSingleVideo() {
    const formData = new FormData();
    formData.append('file_id', state.single.fileId);
    formData.append('artist', artistSingle.value);
    formData.append('title', titleSingle.value);
    formData.append('start_sec', state.single.startSec);
    formData.append('end_sec', state.single.endSec);

    if (state.single.coverPath) {
        formData.append('cover_path', state.single.coverPath);
    }
    if (state.single.customCoverFile) {
        formData.append('cover_file', state.single.customCoverFile);
    }

    // Show progress
    editorSingle.classList.add('hidden');
    progressSingle.classList.remove('hidden');
    resultSingle.classList.add('hidden');
    progressFillSingle.style.width = '0%';
    progressTextSingle.textContent = 'Starting generation...';

    try {
        // Start generation — returns immediately with job_id
        const startRes = await fetch('/api/generate', { method: 'POST', body: formData });
        if (!startRes.ok) {
            const err = await startRes.json();
            throw new Error(err.detail || 'Generation failed');
        }
        const { job_id } = await startRes.json();

        // Poll progress until done
        const result = await pollProgress(job_id);

        if (result.status === 'error') {
            throw new Error(result.result?.error || 'Generation failed');
        }

        // Show result
        progressSingle.classList.add('hidden');
        resultSingle.classList.remove('hidden');
        resultVideoSingle.src = result.result.download_url;
        downloadLinkSingle.href = result.result.download_url;
        downloadLinkSingle.download = result.result.filename;

    } catch (err) {
        alert('Error generating video: ' + err.message);
        progressSingle.classList.add('hidden');
        editorSingle.classList.remove('hidden');
    }
}

function pollProgress(jobId) {
    return new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/progress/${jobId}`);
                const data = await res.json();

                if (data.progress >= 0) {
                    progressFillSingle.style.width = data.progress + '%';
                    progressTextSingle.textContent = `Rendering... ${data.progress}%`;
                }

                if (data.status === 'done' || data.status === 'error') {
                    clearInterval(interval);
                    resolve(data);
                }
            } catch (e) {
                // Network error, keep trying
            }
        }, 500);
    });
}

newVideoBtnSingle.addEventListener('click', () => {
    resultSingle.classList.add('hidden');
    uploadZoneSingle.classList.remove('hidden');
    uploadZoneSingle.querySelector('.upload-area h3').textContent = 'Drag your audio file here';
    state.single.fileId = null;
    state.single.customCoverFile = null;
    fileInputSingle.value = '';
});

// ============================================================
// Batch Mode — Upload
// ============================================================

setupDropZone(dropZoneBatch, (files) => {
    uploadBatchFiles(files);
});

fileInputBatch.addEventListener('change', (e) => {
    if (e.target.files.length > 0) uploadBatchFiles(e.target.files);
});

async function uploadBatchFiles(files) {
    const fileArr = Array.from(files).slice(0, 10 - state.batch.tracks.length);

    for (const file of fileArr) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            if (!res.ok) continue;
            const data = await res.json();

            state.batch.tracks.push({
                fileId: data.file_id,
                filePath: data.filepath,
                artist: data.artist,
                title: data.title,
                album: data.album,
                duration: data.duration,
                coverUrl: data.cover_url,
                coverPath: data.cover_path,
                startSec: 0,
                endSec: Math.min(30, data.duration),
                peaks: [],
            });

            // Load waveform for this track
            loadBatchWaveform(state.batch.tracks.length - 1, data.file_id);
        } catch (err) {
            console.error('Batch upload error:', err);
        }
    }

    renderBatchTracks();

    if (state.batch.tracks.length > 0) {
        batchActions.classList.remove('hidden');
    }
}

async function loadBatchWaveform(trackIdx, fileId) {
    try {
        const res = await fetch(`/api/waveform/${fileId}`);
        const data = await res.json();
        if (trackIdx < state.batch.tracks.length) {
            state.batch.tracks[trackIdx].peaks = data.peaks;
            drawBatchWaveform(trackIdx);
            updateBatchSelection(trackIdx);
        }
    } catch (err) {
        console.error('Batch waveform error:', err);
    }
}

function renderBatchTracks() {
    batchTracksContainer.innerHTML = '';

    state.batch.tracks.forEach((track, idx) => {
        const card = document.createElement('div');
        card.className = 'batch-track-card';
        card.dataset.idx = idx;
        card.innerHTML = `
            <div class="batch-track-header">
                <img class="batch-track-cover" src="${track.coverUrl || ''}" 
                     alt="Cover" onerror="this.style.display='none'">
                <div class="batch-track-info">
                    <div class="batch-track-title">${escapeHtml(track.title)}</div>
                    <div class="batch-track-artist">${escapeHtml(track.artist)}</div>
                </div>
                <div class="batch-track-duration">${formatTime(track.duration)}</div>
                <button class="batch-track-remove" data-idx="${idx}" title="Remove">✕</button>
            </div>
            <div class="batch-track-waveform-section">
                <div class="batch-waveform-container" data-idx="${idx}">
                    <canvas data-idx="${idx}" width="800" height="80"></canvas>
                    <div class="selection-overlay" data-idx="${idx}"></div>
                    <div class="handle handle-left" data-idx="${idx}" data-handle="left"></div>
                    <div class="handle handle-right" data-idx="${idx}" data-handle="right"></div>
                </div>
                <div class="batch-track-time-row">
                    <div class="time-input">
                        <label>Start</label>
                        <input type="number" data-idx="${idx}" data-field="start" 
                               value="${track.startSec.toFixed(1)}" min="0" max="${track.duration}" step="0.1">
                    </div>
                    <button class="btn btn-secondary batch-play-btn" data-idx="${idx}">
                        ${state.batch.playingIdx === idx ? '⏸ Stop' : '▶ Play'}
                    </button>
                    <div class="time-display" data-idx="${idx}">${(track.endSec - track.startSec).toFixed(1)}s</div>
                    <div class="time-input">
                        <label>End</label>
                        <input type="number" data-idx="${idx}" data-field="end" 
                               value="${track.endSec.toFixed(1)}" min="0" max="${track.duration}" step="0.1">
                    </div>
                </div>
            </div>
        `;
        batchTracksContainer.appendChild(card);

        // Draw waveform if peaks are loaded
        if (track.peaks.length > 0) {
            drawBatchWaveform(idx);
            updateBatchSelection(idx);
        }
    });

    // Event: Remove buttons
    batchTracksContainer.querySelectorAll('.batch-track-remove').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.idx);
            state.batch.tracks.splice(idx, 1);
            renderBatchTracks();
            if (state.batch.tracks.length === 0) {
                batchActions.classList.add('hidden');
            }
        });
    });

    // Event: Time inputs
    batchTracksContainer.querySelectorAll('.batch-track-time-row input').forEach((input) => {
        input.addEventListener('input', (e) => {
            const idx = parseInt(e.target.dataset.idx);
            const field = e.target.dataset.field;
            const track = state.batch.tracks[idx];
            let val = parseFloat(e.target.value) || 0;

            if (field === 'start') {
                val = Math.max(0, Math.min(val, track.endSec - 1));
                track.startSec = val;
            } else {
                val = Math.max(track.startSec + 1, Math.min(val, track.duration));
                track.endSec = val;
            }

            updateBatchSelection(idx);
            const durDisplay = batchTracksContainer.querySelector(`.time-display[data-idx="${idx}"]`);
            if (durDisplay) durDisplay.textContent = (track.endSec - track.startSec).toFixed(1) + 's';
        });
    });

    // Event: Play buttons
    batchTracksContainer.querySelectorAll('.batch-play-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.idx);
            toggleBatchPlay(idx);
        });
    });

    // Event: Handle dragging for each track
    batchTracksContainer.querySelectorAll('.batch-waveform-container').forEach((container) => {
        const idx = parseInt(container.dataset.idx);
        let draggingHandle = null;

        const onMouseDown = (e) => {
            if (e.target.dataset.handle) {
                draggingHandle = e.target.dataset.handle;
                e.preventDefault();
            } else if (e.target.tagName === 'CANVAS') {
                // Click on waveform — determine closest handle
                const rect = container.getBoundingClientRect();
                const pct = (e.clientX - rect.left) / rect.width;
                const time = pct * state.batch.tracks[idx].duration;
                const distStart = Math.abs(time - state.batch.tracks[idx].startSec);
                const distEnd = Math.abs(time - state.batch.tracks[idx].endSec);
                draggingHandle = distStart < distEnd ? 'left' : 'right';
                updateBatchDrag(idx, container, e.clientX, draggingHandle);
            }
        };

        const onMouseMove = (e) => {
            if (!draggingHandle) return;
            updateBatchDrag(idx, container, e.clientX, draggingHandle);
        };

        const onMouseUp = () => { draggingHandle = null; };

        container.addEventListener('mousedown', onMouseDown);
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    });
}

function updateBatchDrag(idx, container, clientX, handle) {
    const rect = container.getBoundingClientRect();
    let pct = (clientX - rect.left) / rect.width;
    pct = Math.max(0, Math.min(1, pct));
    const track = state.batch.tracks[idx];
    const time = pct * track.duration;

    if (handle === 'left') {
        track.startSec = Math.min(time, track.endSec - 1);
        const startInput = batchTracksContainer.querySelector(`input[data-idx="${idx}"][data-field="start"]`);
        if (startInput) startInput.value = track.startSec.toFixed(1);
    } else {
        track.endSec = Math.max(time, track.startSec + 1);
        const endInput = batchTracksContainer.querySelector(`input[data-idx="${idx}"][data-field="end"]`);
        if (endInput) endInput.value = track.endSec.toFixed(1);
    }

    updateBatchSelection(idx);
    const durDisplay = batchTracksContainer.querySelector(`.time-display[data-idx="${idx}"]`);
    if (durDisplay) durDisplay.textContent = (track.endSec - track.startSec).toFixed(1) + 's';
}

function drawBatchWaveform(idx) {
    const canvas = batchTracksContainer.querySelector(`canvas[data-idx="${idx}"]`);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const peaks = state.batch.tracks[idx].peaks;
    if (!peaks.length) return;

    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    ctx.scale(2, 2);

    const w = rect.width;
    const h = rect.height;
    const barWidth = w / peaks.length;
    const centerY = h / 2;

    ctx.clearRect(0, 0, w, h);

    peaks.forEach((peak, i) => {
        const barHeight = Math.max(1, peak * centerY * 0.85);
        const x = i * barWidth;
        const lightness = 70 + (i / peaks.length) * 15;
        ctx.fillStyle = `hsla(0, 0%, ${lightness}%, 0.7)`;
        ctx.fillRect(x, centerY - barHeight, barWidth - 0.5, barHeight);
        ctx.fillRect(x, centerY, barWidth - 0.5, barHeight * 0.7);
    });

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(w, centerY);
    ctx.stroke();
}

function updateBatchSelection(idx) {
    const track = state.batch.tracks[idx];
    if (!track || track.duration <= 0) return;

    const overlay = batchTracksContainer.querySelector(`.selection-overlay[data-idx="${idx}"]`);
    const handleL = batchTracksContainer.querySelector(`.handle-left[data-idx="${idx}"]`);
    const handleR = batchTracksContainer.querySelector(`.handle-right[data-idx="${idx}"]`);

    if (!overlay) return;

    const startPct = (track.startSec / track.duration) * 100;
    const endPct = (track.endSec / track.duration) * 100;

    overlay.style.left = startPct + '%';
    overlay.style.width = (endPct - startPct) + '%';

    if (handleL) handleL.style.left = startPct + '%';
    if (handleR) handleR.style.left = endPct + '%';
}

// Shared audio element for batch playback
const batchAudio = new Audio();

function toggleBatchPlay(idx) {
    if (state.batch.playingIdx === idx) {
        // Already playing this track — stop it
        stopBatchPlay();
    } else {
        // Stop any current playback first
        if (state.batch.playingIdx >= 0) stopBatchPlay();

        const track = state.batch.tracks[idx];
        if (!track) return;

        state.batch.playingIdx = idx;

        // Update button text
        const btn = batchTracksContainer.querySelector(`.batch-play-btn[data-idx="${idx}"]`);
        if (btn) btn.textContent = '⏸ Stop';

        const audioUrl = `/api/preview-audio/${track.fileId}`;

        const startPlayback = () => {
            batchAudio.currentTime = track.startSec;
            batchAudio.play().catch(err => console.error('Batch play error:', err));

            // Poll to stop at endSec
            state.batch.playCheckInterval = setInterval(() => {
                if (batchAudio.currentTime >= track.endSec || batchAudio.paused) {
                    stopBatchPlay();
                }
            }, 100);
        };

        if (batchAudio.src && batchAudio.src.endsWith(audioUrl)) {
            // Same source — just seek and play
            startPlayback();
        } else {
            batchAudio.src = audioUrl;
            batchAudio.addEventListener('loadeddata', startPlayback, { once: true });
            batchAudio.load();
        }
    }
}

function stopBatchPlay() {
    batchAudio.pause();
    if (state.batch.playCheckInterval) {
        clearInterval(state.batch.playCheckInterval);
        state.batch.playCheckInterval = null;
    }
    // Reset button text of the playing track
    if (state.batch.playingIdx >= 0) {
        const btn = batchTracksContainer.querySelector(`.batch-play-btn[data-idx="${state.batch.playingIdx}"]`);
        if (btn) btn.textContent = '▶ Play';
    }
    state.batch.playingIdx = -1;
}

// ============================================================
// Batch Mode — Generate
// ============================================================

generateBtnBatch.addEventListener('click', generateBatchVideos);

async function generateBatchVideos() {
    const tracks = state.batch.tracks.map((t) => ({
        file_id: t.fileId,
        artist: t.artist,
        title: t.title,
        cover_path: t.coverPath,
        start_sec: t.startSec,
        end_sec: t.endSec,
    }));

    // Show progress
    batchActions.classList.add('hidden');
    uploadZoneBatch.classList.add('hidden');
    batchTracksContainer.innerHTML = '';
    progressBatch.classList.remove('hidden');
    resultBatch.classList.add('hidden');
    progressFillBatch.style.width = '10%';
    batchProgressText.textContent = `Processing ${tracks.length} tracks...`;

    const formData = new FormData();
    formData.append('data', JSON.stringify(tracks));

    try {
        const res = await fetch('/api/batch/generate', { method: 'POST', body: formData });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Batch generation failed');
        }

        const data = await res.json();

        // Show results
        progressBatch.classList.add('hidden');
        resultBatch.classList.remove('hidden');

        batchResultsList.innerHTML = '';
        data.results.forEach((r) => {
            const item = document.createElement('div');
            item.className = 'batch-result-item';
            item.innerHTML = `
                <span class="batch-result-name">${escapeHtml(r.filename)}</span>
                <span class="batch-result-status ${r.status}">${r.status === 'success' ? '✅' : '❌'}</span>
                ${r.download_url ? `<a class="batch-result-download" href="${r.download_url}" download>Download</a>` : ''}
            `;
            batchResultsList.appendChild(item);
        });

        if (data.zip_url) {
            downloadZipBatch.href = data.zip_url;
            downloadZipBatch.hidden = false;
        }

    } catch (err) {
        alert('Batch error: ' + err.message);
        progressBatch.classList.add('hidden');
        batchActions.classList.remove('hidden');
        uploadZoneBatch.classList.remove('hidden');
        renderBatchTracks();
    }
}

newBatchBtn.addEventListener('click', () => {
    state.batch.tracks = [];
    resultBatch.classList.add('hidden');
    uploadZoneBatch.classList.remove('hidden');
    batchTracksContainer.innerHTML = '';
    downloadZipBatch.hidden = true;
    fileInputBatch.value = '';
});

// ============================================================
// Utilities
// ============================================================

function setupDropZone(zone, onFiles) {
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('drag-over');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        onFiles(e.dataTransfer.files);
    });

    // Click to upload on the whole zone
    zone.addEventListener('click', (e) => {
        // Don't trigger if clicking the button (it has its own handler)
        if (e.target.tagName === 'BUTTON') return;
        const input = zone.querySelector('input[type="file"]');
        if (input) input.click();
    });
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Resize handler for waveform
window.addEventListener('resize', () => {
    if (state.single.peaks.length > 0) {
        drawWaveform();
        updateSelection();
    }
});
