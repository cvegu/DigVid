// Estado de la aplicación
const appState = {
    audioFileId: null,
    coverFileId: null,
    audioDuration: 0,
    metadata: {
        artist: '',
        title: ''
    },
    mode: 'single', // 'single' o 'batch'
    batchSongs: [],  // Array de canciones para modo batch
    waveform: null,  // Datos del waveform
    waveformCanvas: null,
    waveformCtx: null,
    isDragging: false,
    dragType: null, // 'left', 'right', 'selection'
    audioPlayer: null
};

// Elementos del DOM - Modo Individual
const audioUploadArea = document.getElementById('audioUploadArea');
const audioFileInput = document.getElementById('audioFile');
const audioInfo = document.getElementById('audioInfo');
const audioFilename = document.getElementById('audioFilename');
const audioDurationSpan = document.getElementById('audioDuration');

const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');
const step4 = document.getElementById('step4');
const step5 = document.getElementById('step5');

const artistInput = document.getElementById('artist');
const titleInput = document.getElementById('title');
const coverPreview = document.getElementById('coverPreview');
const coverFileInput = document.getElementById('coverFile');
const uploadCoverBtn = document.getElementById('uploadCoverBtn');
const removeCoverBtn = document.getElementById('removeCoverBtn');

const startTimeInput = document.getElementById('startTime');
const endTimeInput = document.getElementById('endTime');
const videoDurationSpan = document.getElementById('videoDuration');

// Elementos del waveform
const waveformCanvas = document.getElementById('waveform');
const waveformContainer = document.getElementById('waveformContainer');
const waveformSelection = document.getElementById('waveformSelection');
const selectionHandleLeft = document.getElementById('selectionHandleLeft');
const selectionHandleRight = document.getElementById('selectionHandleRight');
const selectionInfo = document.getElementById('selectionInfo');
const playPauseBtn = document.getElementById('playPauseBtn');
const currentTimeSpan = document.getElementById('currentTime');
const totalTimeSpan = document.getElementById('totalTime');

const generateBtn = document.getElementById('generateBtn');
const generateStatus = document.getElementById('generateStatus');
const downloadLink = document.getElementById('downloadLink');
const newVideoBtn = document.getElementById('newVideoBtn');

// Elementos del DOM - Modo Batch
const singleMode = document.getElementById('singleMode');
const batchMode = document.getElementById('batchMode');
const singleModeBtn = document.getElementById('singleModeBtn');
const batchModeBtn = document.getElementById('batchModeBtn');

const batchUploadArea = document.getElementById('batchUploadArea');
const batchAudioFiles = document.getElementById('batchAudioFiles');
const batchFilesList = document.getElementById('batchFilesList');
const batchStep1 = document.getElementById('batchStep1');
const batchStep2 = document.getElementById('batchStep2');
const batchStep3 = document.getElementById('batchStep3');
const batchStep4 = document.getElementById('batchStep4');
const folderNameInput = document.getElementById('folderName');
const batchStartTimeInput = document.getElementById('batchStartTime');
const batchEndTimeInput = document.getElementById('batchEndTime');
const batchSongsConfig = document.getElementById('batchSongsConfig');
const batchGenerateBtn = document.getElementById('batchGenerateBtn');
const batchProgress = document.getElementById('batchProgress');
const progressBarFill = document.getElementById('progressBarFill');
const progressText = document.getElementById('progressText');
const batchStatus = document.getElementById('batchStatus');
const batchResults = document.getElementById('batchResults');
const batchResultText = document.getElementById('batchResultText');
const batchDownloadZip = document.getElementById('batchDownloadZip');
const newBatchBtn = document.getElementById('newBatchBtn');

// Event Listeners - Modo selector
singleModeBtn.addEventListener('click', () => switchMode('single'));
batchModeBtn.addEventListener('click', () => switchMode('batch'));

// Event Listeners - Modo Individual
audioUploadArea.addEventListener('click', () => audioFileInput.click());
audioUploadArea.addEventListener('dragover', handleDragOver);
audioUploadArea.addEventListener('dragleave', handleDragLeave);
audioUploadArea.addEventListener('drop', handleDrop);
audioFileInput.addEventListener('change', handleAudioFileSelect);

uploadCoverBtn.addEventListener('click', () => coverFileInput.click());
coverFileInput.addEventListener('change', handleCoverFileSelect);
removeCoverBtn.addEventListener('click', removeCover);

startTimeInput.addEventListener('input', updateVideoDuration);
endTimeInput.addEventListener('input', updateVideoDuration);

// Event listeners para waveform
if (waveformCanvas) {
    const ctx = waveformCanvas.getContext('2d');
    appState.waveformCanvas = waveformCanvas;
    appState.waveformCtx = ctx;
    
    // Event listeners para selección visual (en el contenedor para mejor detección)
    if (waveformContainer) {
        waveformContainer.addEventListener('mousedown', handleWaveformMouseDown);
        document.addEventListener('mousemove', handleWaveformMouseMove);
        document.addEventListener('mouseup', handleWaveformMouseUp);
    }
    
    if (selectionHandleLeft) {
        selectionHandleLeft.addEventListener('mousedown', (e) => {
            e.stopPropagation();
            appState.isDragging = true;
            appState.dragType = 'left';
        });
    }
    
    if (selectionHandleRight) {
        selectionHandleRight.addEventListener('mousedown', (e) => {
            e.stopPropagation();
            appState.isDragging = true;
            appState.dragType = 'right';
        });
    }
}

if (playPauseBtn) {
    playPauseBtn.addEventListener('click', toggleAudioPlayback);
}

generateBtn.addEventListener('click', generateVideo);
newVideoBtn.addEventListener('click', resetApp);

// Event Listeners - Modo Batch
batchUploadArea.addEventListener('click', () => batchAudioFiles.click());
batchUploadArea.addEventListener('dragover', handleBatchDragOver);
batchUploadArea.addEventListener('dragleave', handleBatchDragLeave);
batchUploadArea.addEventListener('drop', handleBatchDrop);
batchAudioFiles.addEventListener('change', handleBatchAudioFilesSelect);

batchGenerateBtn.addEventListener('click', generateBatchVideos);
newBatchBtn.addEventListener('click', resetBatchApp);

// Cambiar modo
function switchMode(mode) {
    appState.mode = mode;
    
    if (mode === 'single') {
        singleModeBtn.classList.add('active');
        batchModeBtn.classList.remove('active');
        singleMode.style.display = 'block';
        batchMode.style.display = 'none';
        resetApp();
    } else {
        singleModeBtn.classList.remove('active');
        batchModeBtn.classList.add('active');
        singleMode.style.display = 'none';
        batchMode.style.display = 'block';
        resetBatchApp();
    }
}

// Funciones de drag and drop - Modo Individual
function handleDragOver(e) {
    e.preventDefault();
    audioUploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    audioUploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    audioUploadArea.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith('audio/')) {
        handleAudioFile(files[0]);
    }
}

function handleAudioFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleAudioFile(file);
    }
}

// Manejar archivo de audio - Modo Individual
async function handleAudioFile(file) {
    try {
        showStatus(generateStatus, 'Subiendo archivo...', 'info');
        
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload/audio', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error subiendo archivo');
        }
        
        const data = await response.json();
        appState.audioFileId = data.file_id;
        appState.audioDuration = data.metadata.duration || 0;
        appState.metadata.artist = data.metadata.artist || '';
        appState.metadata.title = data.metadata.title || '';
        appState.coverFileId = data.cover_file_id || null;
        
        // Mostrar información
        audioFilename.textContent = data.filename;
        audioInfo.style.display = 'block';
        audioDurationSpan.textContent = formatTime(appState.audioDuration);
        
        // Llenar metadata
        artistInput.value = appState.metadata.artist;
        titleInput.value = appState.metadata.title;
        
        // Mostrar portada si existe
        if (appState.coverFileId) {
            await loadCoverPreview(appState.coverFileId);
        }
        
        // Configurar tiempos por defecto (30 segundos)
        endTimeInput.max = appState.audioDuration;
        const defaultDuration = Math.min(30, appState.audioDuration);
        startTimeInput.value = 0;
        startTimeInput.max = appState.audioDuration;
        endTimeInput.value = Math.round(defaultDuration); // Sin decimales
        
        // Cargar y mostrar waveform
        await loadWaveform(appState.audioFileId);
        
        // Configurar reproductor de audio
        setupAudioPlayer(appState.audioFileId);
        
        updateVideoDuration();
        
        // Mostrar siguientes pasos
        step2.style.display = 'block';
        step3.style.display = 'block';
        step4.style.display = 'block';
        
        hideStatus(generateStatus);
        
    } catch (error) {
        showStatus(generateStatus, `Error: ${error.message}`, 'error');
        console.error(error);
    }
}

// Manejar archivo de portada
async function handleCoverFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        await uploadCover(file);
    }
}

async function uploadCover(file) {
    try {
        showStatus(generateStatus, 'Subiendo portada...', 'info');
        
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload/cover', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error subiendo portada');
        }
        
        const data = await response.json();
        appState.coverFileId = data.cover_file_id;
        
        await loadCoverPreview(appState.coverFileId);
        removeCoverBtn.style.display = 'block';
        hideStatus(generateStatus);
        
    } catch (error) {
        showStatus(generateStatus, `Error: ${error.message}`, 'error');
        console.error(error);
    }
}

async function loadCoverPreview(coverFileId) {
    try {
        const imageUrl = `/api/cover/${coverFileId}`;
        const img = document.createElement('img');
        img.src = imageUrl;
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'cover';
        img.onerror = () => {
            coverPreview.innerHTML = '<p>Error cargando portada</p>';
        };
        
        coverPreview.innerHTML = '';
        coverPreview.appendChild(img);
        
    } catch (error) {
        console.error('Error cargando portada:', error);
        coverPreview.innerHTML = '<p>Error cargando portada</p>';
    }
}

function removeCover() {
    appState.coverFileId = null;
    coverPreview.innerHTML = '<p>No hay portada disponible</p>';
    removeCoverBtn.style.display = 'none';
    coverFileInput.value = '';
}

// Actualizar duración del video
function updateVideoDuration() {
    const startTime = parseFloat(startTimeInput.value) || 0;
    const endTime = parseFloat(endTimeInput.value) || 0;
    const duration = Math.max(0, endTime - startTime);
    videoDurationSpan.textContent = formatTime(duration);
    
    // Si el reproductor de audio está activo, verificar que esté dentro del rango
    if (appState.audioPlayer && !appState.audioPlayer.paused) {
        const currentTime = appState.audioPlayer.currentTime;
        // Si está fuera del rango seleccionado, ajustar o pausar
        if (currentTime < startTime || currentTime >= endTime) {
            appState.audioPlayer.currentTime = startTime;
        }
    }
    
    // Sincronizar waveform si existe (solo si no estamos arrastrando)
    if (appState.waveform && waveformSelection && !appState.isDragging) {
        updateWaveformSelection(startTime, endTime, false); // false = no actualizar inputs
    }
}

// Formatear tiempo
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Generar video - Modo Individual
async function generateVideo() {
    try {
        if (!appState.audioFileId) {
            throw new Error('Por favor sube un archivo de audio');
        }
        
        const artist = artistInput.value.trim() || 'Unknown Artist';
        const title = titleInput.value.trim() || 'Unknown Title';
        const startTime = Math.round(parseFloat(startTimeInput.value) || 0); // Sin decimales
        const endTime = Math.round(parseFloat(endTimeInput.value) || 0); // Sin decimales
        
        if (endTime <= startTime) {
            throw new Error('El tiempo final debe ser mayor que el tiempo inicial');
        }
        
        if (endTime > appState.audioDuration) {
            throw new Error(`El tiempo final no puede exceder la duración del audio (${formatTime(appState.audioDuration)})`);
        }
        
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner"></span> Generando video...';
        showStatus(generateStatus, 'Generando video. Esto puede tomar unos minutos...', 'info');
        
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                audio_file_id: appState.audioFileId,
                artist: artist,
                title: title,
                start_time: startTime,
                end_time: endTime,
                cover_file_id: appState.coverFileId
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error generando video');
        }
        
        const data = await response.json();
        
        showStatus(generateStatus, '¡Video generado exitosamente!', 'success');
        downloadLink.href = `/api/download/${data.video_id}`;
        downloadLink.download = data.video_id;
        
        step4.style.display = 'none';
        step5.style.display = 'block';
        
        generateBtn.disabled = false;
        generateBtn.innerHTML = '🎬 Generar Video';
        
    } catch (error) {
        showStatus(generateStatus, `Error: ${error.message}`, 'error');
        generateBtn.disabled = false;
        generateBtn.innerHTML = '🎬 Generar Video';
        console.error(error);
    }
}

// Resetear aplicación - Modo Individual
function resetApp() {
    appState.audioFileId = null;
    appState.coverFileId = null;
    appState.audioDuration = 0;
    appState.metadata = { artist: '', title: '' };
    appState.waveform = null;
    appState.isDragging = false;
    appState.dragType = null;
    
    // Detener y limpiar reproductor de audio
    if (appState.audioPlayer) {
        appState.audioPlayer.pause();
        appState.audioPlayer.src = '';
        appState.audioPlayer = null;
    }
    
    audioFileInput.value = '';
    audioInfo.style.display = 'none';
    artistInput.value = '';
    titleInput.value = '';
    coverPreview.innerHTML = '<p>No hay portada disponible</p>';
    removeCoverBtn.style.display = 'none';
    coverFileInput.value = '';
    startTimeInput.value = 0;
    endTimeInput.value = 30;
    
    // Limpiar waveform
    if (appState.waveformCtx && appState.waveformCanvas) {
        appState.waveformCtx.clearRect(0, 0, appState.waveformCanvas.width, appState.waveformCanvas.height);
    }
    if (waveformSelection) {
        waveformSelection.style.width = '0%';
        waveformSelection.style.left = '0%';
    }
    if (totalTimeSpan) {
        totalTimeSpan.textContent = '0:00';
    }
    if (currentTimeSpan) {
        currentTimeSpan.textContent = '0:00';
    }
    if (playPauseBtn) {
        playPauseBtn.textContent = '▶️ Reproducir';
    }
    
    step2.style.display = 'none';
    step3.style.display = 'none';
    step4.style.display = 'none';
    step5.style.display = 'none';
    
    hideStatus(generateStatus);
}

// ========== MODO BATCH ==========

// Funciones de drag and drop - Modo Batch
function handleBatchDragOver(e) {
    e.preventDefault();
    batchUploadArea.classList.add('dragover');
}

function handleBatchDragLeave(e) {
    e.preventDefault();
    batchUploadArea.classList.remove('dragover');
}

function handleBatchDrop(e) {
    e.preventDefault();
    batchUploadArea.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('audio/'));
    if (files.length > 0) {
        handleBatchAudioFiles(files);
    }
}

function handleBatchAudioFilesSelect(e) {
    const files = Array.from(e.target.files).filter(f => f.type.startsWith('audio/'));
    if (files.length > 0) {
        handleBatchAudioFiles(files);
    }
}

// Manejar múltiples archivos de audio - Modo Batch
async function handleBatchAudioFiles(files) {
    // Limitar a 10 archivos
    const filesToProcess = files.slice(0, 10);
    if (files.length > 10) {
        alert(`Solo se procesarán los primeros 10 archivos. Se ignoraron ${files.length - 10} archivos.`);
    }
    
    // Limpiar lista anterior
    appState.batchSongs = [];
    batchFilesList.innerHTML = '';
    batchFilesList.style.display = 'none';
    
    // Procesar cada archivo
    for (const file of filesToProcess) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/api/upload/audio', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                console.error(`Error subiendo ${file.name}:`, error);
                continue;
            }
            
            const data = await response.json();
            
            // Agregar a la lista de canciones
            appState.batchSongs.push({
                file_id: data.file_id,
                filename: data.filename,
                metadata: data.metadata,
                cover_file_id: data.cover_file_id || null,
                artist: data.metadata.artist || '',
                title: data.metadata.title || '',
                duration: data.metadata.duration || 0,
                start_time: 0,
                end_time: Math.min(30, data.metadata.duration || 30)
            });
            
        } catch (error) {
            console.error(`Error procesando ${file.name}:`, error);
        }
    }
    
    // Mostrar lista de archivos
    if (appState.batchSongs.length > 0) {
        displayBatchFilesList();
        batchStep2.style.display = 'block';
        renderBatchSongsConfig();
    }
}

// Mostrar lista de archivos batch
function displayBatchFilesList() {
    batchFilesList.innerHTML = '';
    batchFilesList.style.display = 'block';
    
    appState.batchSongs.forEach((song, index) => {
        const item = document.createElement('div');
        item.className = 'batch-file-item';
        item.innerHTML = `
            <div class="batch-file-info">
                <strong>${song.filename}</strong>
                <span>${song.metadata.artist || 'Sin artista'} - ${song.metadata.title || 'Sin título'}</span>
                <span>Duración: ${formatTime(song.duration)}</span>
            </div>
            <button type="button" class="batch-file-remove" onclick="removeBatchSong(${index})">✕ Eliminar</button>
        `;
        batchFilesList.appendChild(item);
    });
}

// Eliminar canción del batch
function removeBatchSong(index) {
    appState.batchSongs.splice(index, 1);
    if (appState.batchSongs.length === 0) {
        batchFilesList.style.display = 'none';
        batchStep2.style.display = 'none';
    } else {
        displayBatchFilesList();
        renderBatchSongsConfig();
    }
}

// Renderizar configuración de canciones batch
function renderBatchSongsConfig() {
    batchSongsConfig.innerHTML = '';
    
    appState.batchSongs.forEach((song, index) => {
        const configDiv = document.createElement('div');
        configDiv.className = 'batch-song-config';
        configDiv.innerHTML = `
            <h3>Canción ${index + 1}: ${song.filename}</h3>
            <div class="form-group">
                <label>Artista</label>
                <input type="text" class="batch-artist" data-index="${index}" 
                       value="${song.artist}" placeholder="Nombre del artista">
            </div>
            <div class="form-group">
                <label>Título</label>
                <input type="text" class="batch-title" data-index="${index}" 
                       value="${song.title}" placeholder="Título de la canción">
            </div>
            <div class="form-group">
                <label>Portada del Álbum</label>
                <div class="cover-section">
                    <div class="batch-cover-preview" data-index="${index}" style="width: 150px; height: 150px; border: 2px dashed #e0e0e0; border-radius: 10px; display: flex; align-items: center; justify-content: center; background: #f8f9ff; overflow: hidden;">
                        ${song.cover_file_id ? `<img src="/api/cover/${song.cover_file_id}" style="width: 100%; height: 100%; object-fit: cover;">` : '<p style="color: #999; font-size: 12px; text-align: center; padding: 10px;">Sin portada</p>'}
                    </div>
                    <div class="cover-actions">
                        <input type="file" class="batch-cover-file" data-index="${index}" accept="image/*" style="display: none;">
                        <button type="button" class="btn btn-secondary batch-upload-cover" data-index="${index}">
                            ${song.cover_file_id ? 'Cambiar Portada' : 'Subir Portada'}
                        </button>
                    </div>
                </div>
            </div>
            <div class="form-group">
                <label>Segmento de Audio (Duración: ${formatTime(song.duration)})</label>
                <div class="time-inputs">
                    <div class="time-input-group">
                        <label>Desde (segundos)</label>
                        <input type="number" class="batch-start-time" data-index="${index}" 
                               min="0" step="1" value="${Math.round(song.start_time)}" max="${song.duration}">
                    </div>
                    <div class="time-input-group">
                        <label>Hasta (segundos)</label>
                        <input type="number" class="batch-end-time" data-index="${index}" 
                               min="0" step="1" value="${Math.round(song.end_time)}" max="${song.duration}">
                    </div>
                </div>
            </div>
        `;
        batchSongsConfig.appendChild(configDiv);
        
        // Event listeners para esta canción
        const artistInput = configDiv.querySelector('.batch-artist');
        const titleInput = configDiv.querySelector('.batch-title');
        const startTimeInput = configDiv.querySelector('.batch-start-time');
        const endTimeInput = configDiv.querySelector('.batch-end-time');
        const coverFileInput = configDiv.querySelector('.batch-cover-file');
        const uploadCoverBtn = configDiv.querySelector('.batch-upload-cover');
        const coverPreview = configDiv.querySelector('.batch-cover-preview');
        
        artistInput.addEventListener('input', (e) => {
            const idx = parseInt(e.target.dataset.index);
            appState.batchSongs[idx].artist = e.target.value;
        });
        
        titleInput.addEventListener('input', (e) => {
            const idx = parseInt(e.target.dataset.index);
            appState.batchSongs[idx].title = e.target.value;
        });
        
        startTimeInput.addEventListener('input', (e) => {
            const idx = parseInt(e.target.dataset.index);
            appState.batchSongs[idx].start_time = Math.round(parseFloat(e.target.value) || 0); // Sin decimales
        });
        
        endTimeInput.addEventListener('input', (e) => {
            const idx = parseInt(e.target.dataset.index);
            appState.batchSongs[idx].end_time = Math.round(parseFloat(e.target.value) || 0); // Sin decimales
        });
        
        uploadCoverBtn.addEventListener('click', () => coverFileInput.click());
        coverFileInput.addEventListener('change', async (e) => {
            const idx = parseInt(e.target.dataset.index);
            const file = e.target.files[0];
            if (file) {
                await uploadBatchCover(file, idx, coverPreview);
            }
        });
    });
    
    batchStep3.style.display = 'block';
}

// Subir portada para una canción del batch
async function uploadBatchCover(file, index, coverPreviewElement) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload/cover', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error subiendo portada');
        }
        
        const data = await response.json();
        appState.batchSongs[index].cover_file_id = data.cover_file_id;
        
        // Actualizar preview
        const img = document.createElement('img');
        img.src = `/api/cover/${data.cover_file_id}`;
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'cover';
        coverPreviewElement.innerHTML = '';
        coverPreviewElement.appendChild(img);
        
    } catch (error) {
        console.error('Error subiendo portada:', error);
        alert(`Error subiendo portada: ${error.message}`);
    }
}

// Generar videos en batch
async function generateBatchVideos() {
    try {
        if (appState.batchSongs.length === 0) {
            throw new Error('No hay canciones para procesar');
        }
        
        const folderName = folderNameInput.value.trim() || `Playlist_${new Date().toISOString().split('T')[0]}`;
        const defaultStartTime = Math.round(parseFloat(batchStartTimeInput.value) || 0); // Sin decimales
        const defaultEndTime = Math.round(parseFloat(batchEndTimeInput.value) || 30); // Sin decimales
        
        // Preparar datos para enviar
        const songs = appState.batchSongs.map(song => ({
            audio_file_id: song.file_id,
            artist: song.artist || 'Unknown Artist',
            title: song.title || 'Unknown Title',
            start_time: song.start_time >= 0 ? Math.round(song.start_time) : defaultStartTime,
            end_time: song.end_time > song.start_time ? Math.round(song.end_time) : defaultEndTime,
            cover_file_id: song.cover_file_id
        }));
        
        // Validar tiempos
        for (let i = 0; i < songs.length; i++) {
            const song = songs[i];
            if (song.end_time <= song.start_time) {
                throw new Error(`Canción ${i + 1}: El tiempo final debe ser mayor que el tiempo inicial`);
            }
            const originalSong = appState.batchSongs[i];
            if (song.end_time > originalSong.duration) {
                throw new Error(`Canción ${i + 1}: El tiempo final excede la duración del audio (${formatTime(originalSong.duration)})`);
            }
        }
        
        // Mostrar progreso
        batchGenerateBtn.disabled = true;
        batchGenerateBtn.innerHTML = '<span class="spinner"></span> Generando videos...';
        batchProgress.style.display = 'block';
        batchStatus.innerHTML = '';
        progressBarFill.style.width = '0%';
        progressText.textContent = 'Iniciando procesamiento...';
        
        // Llamar a la API
        const response = await fetch('/api/batch/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                songs: songs,
                folder_name: folderName,
                start_time: defaultStartTime,
                end_time: defaultEndTime
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Error generando videos');
        }
        
        const data = await response.json();
        
        // Mostrar resultados
        progressBarFill.style.width = '100%';
        progressText.textContent = `Completado: ${data.processed}/${data.total} videos generados`;
        
        // Mostrar estado de cada canción
        data.processed_songs.forEach(song => {
            const statusItem = document.createElement('div');
            statusItem.className = 'batch-status-item success';
            statusItem.textContent = `✓ ${song.artist} - ${song.title}`;
            batchStatus.appendChild(statusItem);
        });
        
        data.errors_list.forEach(error => {
            const statusItem = document.createElement('div');
            statusItem.className = 'batch-status-item error';
            statusItem.textContent = `✗ ${error.artist || 'Unknown'} - ${error.title || 'Unknown'}: ${error.error}`;
            batchStatus.appendChild(statusItem);
        });
        
        // Mostrar resultados finales
        batchStep3.style.display = 'none';
        batchStep4.style.display = 'block';
        
        batchResultText.textContent = `Se generaron ${data.processed} de ${data.total} videos exitosamente.`;
        
        // Mostrar lista de videos generados
        batchResults.innerHTML = '';
        data.processed_songs.forEach(song => {
            const resultItem = document.createElement('div');
            resultItem.className = 'batch-result-item';
            resultItem.innerHTML = `
                <strong>${song.artist} - ${song.title}</strong><br>
                <a href="/api/batch/download/${data.folder_name}/${encodeURIComponent(song.filename)}" 
                   class="btn btn-secondary" style="margin-top: 10px; display: inline-block;">
                    ⬇️ Descargar
                </a>
            `;
            batchResults.appendChild(resultItem);
        });
        
        // Mostrar botón de descarga ZIP
        if (data.processed > 0) {
            batchDownloadZip.href = `/api/batch/download-zip/${data.folder_name}`;
            batchDownloadZip.download = `${data.folder_name}.zip`;
            batchDownloadZip.style.display = 'block';
        }
        
        batchGenerateBtn.disabled = false;
        batchGenerateBtn.innerHTML = '🎬 Generar Todos los Videos';
        
    } catch (error) {
        progressText.textContent = `Error: ${error.message}`;
        const statusItem = document.createElement('div');
        statusItem.className = 'batch-status-item error';
        statusItem.textContent = `Error: ${error.message}`;
        batchStatus.appendChild(statusItem);
        batchGenerateBtn.disabled = false;
        batchGenerateBtn.innerHTML = '🎬 Generar Todos los Videos';
        console.error(error);
    }
}

// Resetear aplicación batch
function resetBatchApp() {
    appState.batchSongs = [];
    batchFilesList.innerHTML = '';
    batchFilesList.style.display = 'none';
    batchSongsConfig.innerHTML = '';
    folderNameInput.value = '';
    batchStartTimeInput.value = 0;
    batchEndTimeInput.value = 30;
    batchProgress.style.display = 'none';
    batchStatus.innerHTML = '';
    batchResults.innerHTML = '';
    batchDownloadZip.style.display = 'none';
    
    batchStep2.style.display = 'none';
    batchStep3.style.display = 'none';
    batchStep4.style.display = 'none';
    
    batchAudioFiles.value = '';
}

// Cargar y dibujar waveform
async function loadWaveform(fileId) {
    try {
        const response = await fetch(`/api/waveform/${fileId}`);
        if (!response.ok) {
            console.error('Error cargando waveform');
            return;
        }
        
        const data = await response.json();
        appState.waveform = data.waveform;
        
        // Dibujar waveform
        drawWaveform();
        
        // Actualizar selección inicial (30 segundos desde el inicio por defecto)
        const defaultStart = 0;
        const defaultEnd = Math.min(30, appState.audioDuration);
        updateWaveformSelection(defaultStart, defaultEnd);
        
    } catch (error) {
        console.error('Error cargando waveform:', error);
    }
}

// Dibujar waveform en el canvas
function drawWaveform() {
    if (!appState.waveformCtx || !appState.waveform) {
        return;
    }
    
    const ctx = appState.waveformCtx;
    const canvas = appState.waveformCanvas;
    const width = canvas.width;
    const height = canvas.height;
    
    // Limpiar canvas con fondo negro
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, width, height);
    
    // Dibujar waveform con estilo minimalista
    const waveform = appState.waveform;
    const barWidth = width / waveform.length;
    const centerY = height / 2;
    
    // Color simple y elegante (blanco/gris)
    ctx.fillStyle = '#ffffff';
    
    waveform.forEach((amplitude, index) => {
        const x = index * barWidth;
        const barHeight = amplitude * (height * 0.8);
        const y = centerY - barHeight / 2;
        
        // Opacidad basada en amplitud para efecto más sutil
        const opacity = Math.min(0.3 + amplitude * 0.7, 1.0);
        ctx.fillStyle = `rgba(255, 255, 255, ${opacity})`;
        
        ctx.fillRect(x, y, Math.max(1, barWidth - 1), barHeight);
    });
    
    // Resetear fillStyle
    ctx.fillStyle = '#ffffff';
}

// Actualizar selección visual en el waveform
function updateWaveformSelection(startTime, endTime, updateInputs = true) {
    if (!waveformSelection || !appState.audioDuration || appState.audioDuration === 0) {
        return;
    }
    
    const canvas = appState.waveformCanvas;
    if (!canvas) return;
    
    const startPercent = Math.max(0, Math.min(100, (startTime / appState.audioDuration) * 100));
    const endPercent = Math.max(0, Math.min(100, (endTime / appState.audioDuration) * 100));
    const selectionWidth = Math.max(0, endPercent - startPercent);
    
    waveformSelection.style.left = `${startPercent}%`;
    waveformSelection.style.width = `${selectionWidth}%`;
    waveformSelection.style.display = 'block';
    
    // Actualizar info de selección
    const duration = endTime - startTime;
    if (selectionInfo) {
        selectionInfo.textContent = `${Math.round(duration)}s`;
    }
    
    // Sincronizar inputs solo si se solicita
    if (updateInputs) {
        if (startTimeInput) startTimeInput.value = Math.round(startTime); // Sin decimales
        if (endTimeInput) endTimeInput.value = Math.round(endTime); // Sin decimales
        
        // Actualizar duración visual directamente
        if (videoDurationSpan) {
            videoDurationSpan.textContent = formatTime(duration);
        }
    }
}

// Manejar eventos del mouse en el waveform
function handleWaveformMouseDown(e) {
    if (!appState.waveform || !appState.audioDuration || !waveformContainer) return;
    
    e.preventDefault();
    const rect = waveformContainer.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percent = Math.max(0, Math.min(100, (x / rect.width) * 100));
    const time = (percent / 100) * appState.audioDuration;
    
    const startTime = parseFloat(startTimeInput.value) || 0;
    const endTime = parseFloat(endTimeInput.value) || 30;
    
    // Determinar qué se está arrastrando
    const selectionLeftPercent = (startTime / appState.audioDuration) * 100;
    const selectionRightPercent = (endTime / appState.audioDuration) * 100;
    const selectionLeft = (selectionLeftPercent / 100) * rect.width;
    const selectionRight = (selectionRightPercent / 100) * rect.width;
    const handleWidth = 15;
    
    // Verificar si estamos cerca de los handles
    if (Math.abs(x - selectionLeft) < handleWidth) {
        appState.isDragging = true;
        appState.dragType = 'left';
        e.stopPropagation();
    } else if (Math.abs(x - selectionRight) < handleWidth) {
        appState.isDragging = true;
        appState.dragType = 'right';
        e.stopPropagation();
    } else if (x >= selectionLeft && x <= selectionRight) {
        // Arrastrar toda la selección
        appState.isDragging = true;
        appState.dragType = 'selection';
        appState.dragOffset = time - startTime;
        e.stopPropagation();
    } else {
        // Mover la selección al hacer clic (centrar en el punto clickeado)
        const duration = endTime - startTime;
        const newStart = Math.max(0, Math.min(time - duration / 2, appState.audioDuration - duration));
        const newEnd = Math.min(newStart + duration, appState.audioDuration);
        updateWaveformSelection(newStart, newEnd);
    }
}

function handleWaveformMouseMove(e) {
    if (!appState.isDragging || !appState.waveform || !appState.audioDuration || !waveformContainer) return;
    
    e.preventDefault();
    const rect = waveformContainer.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const percent = (x / rect.width) * 100;
    const time = Math.max(0, Math.min((percent / 100) * appState.audioDuration, appState.audioDuration));
    
    let startTime = parseFloat(startTimeInput.value) || 0;
    let endTime = parseFloat(endTimeInput.value) || 30;
    const duration = endTime - startTime;
    
    if (appState.dragType === 'left') {
        startTime = Math.max(0, Math.min(time, endTime - 0.5));
        updateWaveformSelection(startTime, endTime);
    } else if (appState.dragType === 'right') {
        endTime = Math.max(startTime + 0.5, Math.min(time, appState.audioDuration));
        updateWaveformSelection(startTime, endTime);
    } else if (appState.dragType === 'selection') {
        const newStart = Math.max(0, Math.min(time - appState.dragOffset, appState.audioDuration - duration));
        const newEnd = Math.min(newStart + duration, appState.audioDuration);
        updateWaveformSelection(newStart, newEnd);
    }
}

function handleWaveformMouseUp(e) {
    if (appState.isDragging) {
        appState.isDragging = false;
        appState.dragType = null;
        appState.dragOffset = 0;
    }
}

// Configurar reproductor de audio
function setupAudioPlayer(audioFileId) {
    // Crear o obtener elemento de audio
    let audioElement = document.getElementById('audioPlayer');
    if (!audioElement) {
        audioElement = document.createElement('audio');
        audioElement.id = 'audioPlayer';
        audioElement.style.display = 'none';
        document.body.appendChild(audioElement);
    }
    
    // Configurar fuente del audio - codificar el nombre del archivo por si tiene caracteres especiales
    const encodedFileId = encodeURIComponent(audioFileId);
    audioElement.src = `/api/audio/${encodedFileId}`;
    audioElement.preload = 'metadata';
    
    // Guardar referencia en el estado
    appState.audioPlayer = audioElement;
    
    // Event listeners para actualizar UI
    audioElement.addEventListener('loadedmetadata', () => {
        if (totalTimeSpan) {
            totalTimeSpan.textContent = formatTime(audioElement.duration);
        }
    });
    
    audioElement.addEventListener('error', (e) => {
        console.error('Error cargando audio:', e);
        console.error('Audio src:', audioElement.src);
        console.error('Audio error code:', audioElement.error?.code);
        console.error('Audio error message:', audioElement.error?.message);
    });
    
    audioElement.addEventListener('timeupdate', () => {
        if (currentTimeSpan) {
            currentTimeSpan.textContent = formatTime(audioElement.currentTime);
        }
        
        // Obtener los tiempos seleccionados (sin decimales)
        const startTime = Math.round(parseFloat(startTimeInput.value) || 0);
        const endTime = Math.round(parseFloat(endTimeInput.value) || 30);
        
        // Si el audio alcanza o supera el tiempo final seleccionado, pausar y reiniciar
        if (audioElement.currentTime >= endTime) {
            audioElement.pause();
            audioElement.currentTime = startTime;
            if (playPauseBtn) {
                playPauseBtn.textContent = '▶️ Reproducir';
            }
        }
        
        // Si el audio está antes del tiempo de inicio, saltar al inicio
        if (audioElement.currentTime < startTime) {
            audioElement.currentTime = startTime;
        }
    });
    
    audioElement.addEventListener('ended', () => {
        if (playPauseBtn) {
            playPauseBtn.textContent = '▶️ Reproducir';
        }
        // Reiniciar al inicio de la selección
        const startTime = Math.round(parseFloat(startTimeInput.value) || 0);
        audioElement.currentTime = startTime;
    });
    
    audioElement.addEventListener('pause', () => {
        if (playPauseBtn && !audioElement.ended) {
            playPauseBtn.textContent = '▶️ Reproducir';
        }
    });
    
    audioElement.addEventListener('play', () => {
        if (playPauseBtn) {
            playPauseBtn.textContent = '⏸️ Pausar';
        }
    });
}

// Toggle reproducción de audio
function toggleAudioPlayback() {
    if (!appState.audioPlayer) {
        console.error('Reproductor de audio no está configurado');
        return;
    }
    
    const audio = appState.audioPlayer;
    const startTime = Math.round(parseFloat(startTimeInput.value) || 0); // Sin decimales
    const endTime = Math.round(parseFloat(endTimeInput.value) || 30); // Sin decimales
    
    if (audio.paused) {
        // Siempre iniciar desde el tiempo de inicio seleccionado
        audio.currentTime = startTime;
        audio.play().catch(error => {
            console.error('Error reproduciendo audio:', error);
            console.error('Audio src:', audio.src);
            console.error('Audio file ID:', appState.audioFileId);
            // Mostrar error más específico
            const errorMsg = error.message || 'Error desconocido';
            alert(`Error reproduciendo audio: ${errorMsg}\n\nArchivo: ${appState.audioFileId}\n\nAsegúrate de que el archivo sea válido y que el servidor esté funcionando correctamente.`);
        });
    } else {
        // Pausar reproducción
        audio.pause();
    }
}

// Utilidades de UI
function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status-message ${type}`;
    element.style.display = 'block';
}

function hideStatus(element) {
    element.style.display = 'none';
}
