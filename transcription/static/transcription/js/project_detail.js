// Transcript Deletion Logic
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

// Recording Logic
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

        // Initialize context with hardware default to avoid NotSupportedError
        audioContext = new (window.AudioContext || window.webkitAudioContext)();

        input = audioContext.createMediaStreamSource(stream);
        // 4096 buffer size
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

    // Flatten the chunks
    const samples = new Float32Array(recordingLength);
    let offset = 0;
    for (let i = 0; i < leftChannel.length; i++) {
        samples.set(leftChannel[i], offset);
        offset += leftChannel[i].length;
    }

    // Resample to target if necessary
    let finalSamples = samples;
    if (hardwareSampleRate !== targetSampleRate) {
        console.log(`Resampling from ${hardwareSampleRate} Hz to ${targetSampleRate} Hz`);
        finalSamples = resample(samples, hardwareSampleRate, targetSampleRate);
    }

    // Encode to WAV
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

    // RIFF chunk descriptor
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 32 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');

    // FMT sub-chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // Subchunk1Size
    view.setUint16(20, 1, true); // AudioFormat (PCM)
    view.setUint16(22, 1, true); // NumChannels
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); // ByteRate
    view.setUint16(32, 2, true); // BlockAlign
    view.setUint16(34, 16, true); // BitsPerSample

    // Data sub-chunk
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // PCM samples
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

    // Send the blob currently in playback
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
    }
};
