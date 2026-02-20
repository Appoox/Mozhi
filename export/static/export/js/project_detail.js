// Export JSON Logic
const exportJsonBtn = document.getElementById('exportJsonBtn');
const exportModal = document.getElementById('exportModal');
const exportStatusText = document.getElementById('exportStatusText');
const exportProgressBar = document.getElementById('exportProgressBar');
const exportProgressCount = document.getElementById('exportProgressCount');
const closeExportModalBtn = document.getElementById('closeExportModalBtn');

if (exportJsonBtn) {
    exportJsonBtn.onclick = async () => {
        // Reset and open modal
        exportStatusText.textContent = 'Preparing export...';
        exportProgressBar.style.width = '0%';
        exportProgressBar.className = 'progress-bar';
        exportProgressCount.textContent = '';
        closeExportModalBtn.style.display = 'none';
        exportModal.style.display = 'block';
        exportJsonBtn.disabled = true;

        try {
            const response = await fetch(window.exportJsonUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': window.csrfToken }
            });

            if (!response.ok) throw new Error(`Server error: ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let total = 0;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const msg = JSON.parse(line);
                        if (msg.type === 'init') {
                            total = msg.total;
                            exportStatusText.textContent = `Exporting ${total} transcripts...`;
                            exportProgressCount.textContent = `0 / ${total}`;
                        } else if (msg.type === 'progress') {
                            const pct = total > 0 ? (msg.current / total) * 100 : 0;
                            exportProgressBar.style.width = `${pct}%`;
                            exportProgressCount.textContent = `${msg.current} / ${total}`;
                        } else if (msg.type === 'success') {
                            exportProgressBar.style.width = '100%';
                            exportProgressBar.classList.add('success');
                            exportStatusText.textContent = `✓ ${msg.message}`;
                            exportProgressCount.textContent = `${total} / ${total}`;
                        } else if (msg.type === 'error') {
                            exportProgressBar.classList.add('error');
                            exportStatusText.textContent = `✗ Error: ${msg.error}`;
                        }
                    } catch (e) {
                        console.error('Parse error:', e, line);
                    }
                }
            }
        } catch (err) {
            exportProgressBar.classList.add('error');
            exportStatusText.textContent = `✗ Failed: ${err.message}`;
        } finally {
            exportJsonBtn.disabled = false;
            closeExportModalBtn.style.display = 'inline-block';
        }
    };
}

closeExportModalBtn.onclick = () => {
    exportModal.style.display = 'none';
};


// ── Transcript Deletion Logic ──────────────────────────────────────────────

const deleteTranscriptModal = document.getElementById('deleteTranscriptModal');
const deleteAudioFileCheckbox = document.getElementById('deleteAudioFileCheckbox');
const cancelDeleteTranscriptBtn = document.getElementById('cancelDeleteTranscriptBtn');
const confirmDeleteTranscriptBtn = document.getElementById('confirmDeleteTranscriptBtn');

let transcriptToDeleteId = null;

document.querySelectorAll('.delete-transcript-btn').forEach(btn => {
    btn.onclick = () => {
        transcriptToDeleteId = btn.getAttribute('data-id');
        deleteAudioFileCheckbox.checked = false;
        deleteTranscriptModal.style.display = 'block';
    };
});

cancelDeleteTranscriptBtn.onclick = () => {
    deleteTranscriptModal.style.display = 'none';
};

confirmDeleteTranscriptBtn.onclick = async () => {
    if (!transcriptToDeleteId) return;

    confirmDeleteTranscriptBtn.disabled = true;
    confirmDeleteTranscriptBtn.textContent = 'Deleting...';

    const formData = new FormData();
    formData.append('delete_files', deleteAudioFileCheckbox.checked);
    formData.append('csrfmiddlewaretoken', window.csrfToken);

    try {
        const response = await fetch(`/transcripts/${transcriptToDeleteId}/delete/`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.status === 'success') {
            location.reload();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Failed to delete transcript.');
    } finally {
        confirmDeleteTranscriptBtn.disabled = false;
        confirmDeleteTranscriptBtn.textContent = 'Confirm Delete';
        deleteTranscriptModal.style.display = 'none';
    }
};


// ── Recording Logic ────────────────────────────────────────────────────────

const recordingModal = document.getElementById('recordingModal');
const recordBtn = document.getElementById('recordBtn');
const closeRecording = document.getElementById('closeRecording');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const saveUI = document.getElementById('saveUI');
const recordUI = document.getElementById('recordUI');
const audioPlayback = document.getElementById('audioPlayback');
const timerDisplay = document.getElementById('timer');
const recordState = document.getElementById('recordState');
const saveRecordBtn = document.getElementById('saveRecordBtn');
const resetBtn = document.getElementById('resetBtn');
const recordedTranscript = document.getElementById('recordedTranscript');

let audioContext;
let processor;
let input;
let leftChannel = [];
let recordingLength = 0;
let targetSampleRate = window.sampleRate;
let timerInterval;
let startTime;

recordBtn.onclick = () => {
    recordingModal.style.display = 'block';
    resetRecording();
};

closeRecording.onclick = () => {
    recordingModal.style.display = 'none';
    stopRecordingInternal();
};

function updateTimer() {
    const now = Date.now();
    const diff = now - startTime;
    const totalSeconds = Math.floor(diff / 1000);
    const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const s = (totalSeconds % 60).toString().padStart(2, '0');
    timerDisplay.textContent = `${m}:${s}`;
}

function resetRecording() {
    leftChannel = [];
    recordingLength = 0;
    saveUI.style.display = 'none';
    recordUI.style.display = 'block';
    startBtn.style.display = 'block';
    stopBtn.style.display = 'none';
    recordState.innerHTML = '<p>Click "Start" to begin recording.</p>';
    timerDisplay.textContent = '00:00';
    recordedTranscript.value = '';
}

resetBtn.onclick = resetRecording;

function stopRecordingInternal() {
    if (processor) {
        processor.disconnect();
        input.disconnect();
        if (audioContext && audioContext.state !== 'closed') {
            audioContext.close();
        }
        processor = null;
        input = null;
    }
    clearInterval(timerInterval);
}

startBtn.onclick = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        input = audioContext.createMediaStreamSource(stream);
        processor = audioContext.createScriptProcessor(4096, 1, 1);

        processor.onaudioprocess = (e) => {
            const chunk = e.inputBuffer.getChannelData(0);
            leftChannel.push(new Float32Array(chunk));
            recordingLength += chunk.length;
        };

        input.connect(processor);
        processor.connect(audioContext.destination);

        startTime = Date.now();
        timerInterval = setInterval(updateTimer, 100);

        startBtn.style.display = 'none';
        stopBtn.style.display = 'block';
        recordState.innerHTML = '<span class="record-indicator"></span><strong>Recording...</strong>';
    } catch (err) {
        alert("Could not access microphone: " + err);
        console.error(err);
    }
};

stopBtn.onclick = () => {
    const hardwareSampleRate = audioContext.sampleRate;
    stopRecordingInternal();

    const samples = new Float32Array(recordingLength);
    let offset = 0;
    for (let i = 0; i < leftChannel.length; i++) {
        samples.set(leftChannel[i], offset);
        offset += leftChannel[i].length;
    }

    let finalSamples = samples;
    if (hardwareSampleRate !== targetSampleRate) {
        console.log(`Resampling from ${hardwareSampleRate} Hz to ${targetSampleRate} Hz`);
        finalSamples = resample(samples, hardwareSampleRate, targetSampleRate);
    }

    const wavBuffer = encodeWav(finalSamples, targetSampleRate);
    const audioBlob = new Blob([wavBuffer], { type: 'audio/wav' });

    console.log("Recording stopped. WAV size:", audioBlob.size, "at", targetSampleRate, "Hz");

    const audioUrl = URL.createObjectURL(audioBlob);
    audioPlayback.src = audioUrl;

    recordUI.style.display = 'none';
    saveUI.style.display = 'block';
};

function resample(samples, fromRate, toRate) {
    const ratio = fromRate / toRate;
    const newLength = Math.round(samples.length / ratio);
    const result = new Float32Array(newLength);
    for (let i = 0; i < newLength; i++) {
        result[i] = samples[Math.floor(i * ratio)];
    }
    return result;
}

function encodeWav(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    writeString(view, 0, 'RIFF');
    view.setUint32(4, 32 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');

    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);

    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    let pcmOffset = 44;
    for (let i = 0; i < samples.length; i++, pcmOffset += 2) {
        let s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(pcmOffset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return buffer;
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

saveRecordBtn.onclick = async () => {
    if (!recordedTranscript.value.trim()) {
        alert("Please enter a transcript.");
        return;
    }

    saveRecordBtn.disabled = true;
    saveRecordBtn.textContent = "Saving...";

    const audioBlob = await fetch(audioPlayback.src).then(r => r.blob());

    const formData = new FormData();
    formData.append('audio', audioBlob, 'record.wav');
    formData.append('transcript', recordedTranscript.value);
    formData.append('project_id', window.projectId);
    formData.append('csrfmiddlewaretoken', window.csrfToken);

    try {
        const response = await fetch(window.saveRecordUrl, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.status === 'success') {
            location.reload();
        } else {
            console.error("Server error:", data.error);
            alert("Error: " + data.error);
        }
    } catch (err) {
        console.error("AJAX error:", err);
        alert("Failed to save recording. Check console for details.");
    } finally {
        saveRecordBtn.disabled = false;
        saveRecordBtn.textContent = "Save to Project";
    }
};

window.onclick = (event) => {
    if (event.target == recordingModal) {
        recordingModal.style.display = 'none';
        stopRecordingInternal();
    } else if (event.target == deleteTranscriptModal) {
        deleteTranscriptModal.style.display = 'none';
    } else if (event.target == exportModal) {
        exportModal.style.display = 'none';
    }
};

// ── Shared helpers ────────────────────────────────────────────────────
function formatTime(s) {
    const m = Math.floor(s / 60);
    return m + ':' + String(Math.floor(s % 60)).padStart(2, '0');
}

function wirePlayPause(playBtn, isPlayingFn, toggleFn) {
    const iconPlay  = playBtn.querySelector('.icon-play');
    const iconPause = playBtn.querySelector('.icon-pause');
    playBtn.addEventListener('click', toggleFn);
    return function syncIcons(playing) {
        iconPlay.style.display  = playing ? 'none'  : 'block';
        iconPause.style.display = playing ? 'block' : 'none';
    };
}

// ── Canvas Fallback Player ────────────────────────────────────────────
// Uses Web Audio API (decodeAudioData) + HTMLAudioElement — zero CDN.
function initFallbackPlayer(id, src) {
    const wrapper    = document.getElementById('waveform-' + id);
    const playBtn    = document.querySelector('.play-pause-btn[data-id="' + id + '"]');
    const currentEl  = document.getElementById('current-' + id);
    const totalEl    = document.getElementById('total-' + id);

    // Canvas setup
    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'width:100%;height:64px;cursor:pointer;display:block;';
    wrapper.appendChild(canvas);

    const WAVE   = '#b0bec5';
    const PROG   = '#1a1a2e';
    const CURSOR = '#139b06';
    let peaks    = [];
    let duration = 0;

    function drawWaveform(progress) {
        const dpr = window.devicePixelRatio || 1;
        const W   = canvas.clientWidth;
        const H   = canvas.clientHeight;
        canvas.width  = W * dpr;
        canvas.height = H * dpr;
        const ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);

        if (!peaks.length) return;

        const barW   = 2;
        const gap    = 1.5;
        const step   = barW + gap;
        const bars   = Math.floor(W / step);
        const mid    = H / 2;
        const cursor = Math.floor(progress * W);

        for (let i = 0; i < bars; i++) {
            const idx  = Math.floor(i / bars * peaks.length);
            const barH = Math.max(2, peaks[idx] * (H * 0.9));
            const x    = i * step;
            ctx.fillStyle = x < cursor ? PROG : WAVE;
            ctx.beginPath();
            ctx.roundRect(x, mid - barH / 2, barW, barH, 1);
            ctx.fill();
        }

        // Cursor line
        if (progress > 0 && progress < 1) {
            ctx.fillStyle = CURSOR;
            ctx.fillRect(cursor, 0, 2, H);
        }
    }

    // Decode audio and build peak data
    fetch(src)
        .then(r => r.arrayBuffer())
        .then(buf => new (window.AudioContext || window.webkitAudioContext)().decodeAudioData(buf))
        .then(decoded => {
            duration = decoded.duration;
            totalEl.textContent = formatTime(duration);

            const raw      = decoded.getChannelData(0);
            const samples  = 800; // resolution
            const chunk    = Math.floor(raw.length / samples);
            peaks = Array.from({ length: samples }, (_, i) => {
                let max = 0;
                for (let j = 0; j < chunk; j++) max = Math.max(max, Math.abs(raw[i * chunk + j]));
                return max;
            });

            // Normalise
            const maxPeak = Math.max(...peaks, 0.001);
            peaks = peaks.map(p => p / maxPeak);

            drawWaveform(0);
        })
        .catch(() => drawWaveform(0));

    // HTMLAudioElement for playback
    const audio    = new Audio(src);
    let   rafId    = null;
    const syncIcons = wirePlayPause(playBtn, () => !audio.paused, () => audio.paused ? audio.play() : audio.pause());

    function tick() {
        if (duration > 0) {
            const prog = audio.currentTime / duration;
            currentEl.textContent = formatTime(audio.currentTime);
            drawWaveform(prog);
        }
        if (!audio.paused) rafId = requestAnimationFrame(tick);
    }

    audio.addEventListener('play',   () => { syncIcons(true);  rafId = requestAnimationFrame(tick); });
    audio.addEventListener('pause',  () => { syncIcons(false); cancelAnimationFrame(rafId); });
    audio.addEventListener('ended',  () => { syncIcons(false); cancelAnimationFrame(rafId); drawWaveform(0); currentEl.textContent = '0:00'; });

    // Seek on canvas click
    canvas.addEventListener('click', e => {
        if (!duration) return;
        const ratio = e.offsetX / canvas.clientWidth;
        audio.currentTime = ratio * duration;
        drawWaveform(ratio);
        currentEl.textContent = formatTime(audio.currentTime);
    });

    // Redraw on resize
    window.addEventListener('resize', () => drawWaveform(duration ? audio.currentTime / duration : 0));
}

// ── WaveSurfer Player ─────────────────────────────────────────────────
function initWaveSurferPlayer(id, src) {
    const container  = document.getElementById('waveform-' + id);
    const playBtn    = document.querySelector('.play-pause-btn[data-id="' + id + '"]');
    const currentEl  = document.getElementById('current-' + id);
    const totalEl    = document.getElementById('total-' + id);
    const syncIcons  = wirePlayPause(playBtn, null, () => ws.playPause());

    const ws = WaveSurfer.create({
        container:     container,
        waveColor:     '#b0bec5',
        progressColor: '#1a1a2e',
        cursorColor:   '#139b06',
        cursorWidth:   2,
        height:        64,
        barWidth:      2,
        barGap:        1.5,
        barRadius:     2,
        normalize:     true,
        url:           src,
    });

    ws.on('ready',        () => totalEl.textContent   = formatTime(ws.getDuration()));
    ws.on('audioprocess', () => currentEl.textContent = formatTime(ws.getCurrentTime()));
    ws.on('seeking',      () => currentEl.textContent = formatTime(ws.getCurrentTime()));
    ws.on('play',         () => syncIcons(true));
    ws.on('pause',        () => syncIcons(false));
    ws.on('finish',       () => syncIcons(false));
}

// ── Init all players ──────────────────────────────────────────────────
const useWaveSurfer = !window.waveSurferFailed && typeof WaveSurfer !== 'undefined';

document.querySelectorAll('.audio-src').forEach(function (el) {
    const id  = el.dataset.id;
    const src = el.dataset.src;
    useWaveSurfer ? initWaveSurferPlayer(id, src) : initFallbackPlayer(id, src);
});