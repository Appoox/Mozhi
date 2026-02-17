// Export JSON Logic
const exportJsonBtn = document.getElementById('exportJsonBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const loadingText = document.getElementById('loadingText');
const progressCounter = document.getElementById('progressCounter');

if (exportJsonBtn) {
    exportJsonBtn.onclick = async () => {
        exportJsonBtn.disabled = true;
        loadingOverlay.style.display = 'flex';
        loadingText.textContent = 'Exporting... Please wait';
        progressCounter.textContent = '';

        try {
            const response = await fetch(window.exportJsonUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.csrfToken
                }
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep partial line in buffer

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        if (data.type === 'init') {
                            progressCounter.textContent = `0 / ${data.total}`;
                            window.totalToExport = data.total;
                        } else if (data.type === 'progress') {
                            progressCounter.textContent = `${data.current} / ${window.totalToExport}`;
                        } else if (data.type === 'success') {
                            alert("Success: " + data.message);
                        } else if (data.type === 'error') {
                            alert("Error: " + data.error);
                        }
                    } catch (e) {
                        console.error("Parse error:", e, line);
                    }
                }
            }
        } catch (err) {
            console.error("Export error:", err);
            alert("Failed to export JSON. Check console for details.");
        } finally {
            exportJsonBtn.disabled = false;
            loadingOverlay.style.display = 'none';
        }
    };
}

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
        const response = await fetch(`/export/transcripts/${transcriptToDeleteId}/delete/`, {
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

window.onclick = (event) => {
    if (event.target == deleteTranscriptModal) {
        deleteTranscriptModal.style.display = 'none';
    }
};
