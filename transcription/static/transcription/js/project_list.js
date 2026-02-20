const deleteModal = document.getElementById('deleteModal');
const createModal = document.getElementById('createModal');
const openCreateModalBtn = document.getElementById('openCreateModalBtn');
const cancelCreateBtn = document.getElementById('cancelCreateBtn');

const projectNameDisplay = document.getElementById('projectNameDisplay');
const deleteFilesCheckbox = document.getElementById('deleteFilesCheckbox');
const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
// Add these variables at the top
const importModal = document.getElementById('importModal');
const openImportModalBtn = document.getElementById('openImportModalBtn');
const cancelImportBtn = document.getElementById('cancelImportBtn');

let projectToDelete = null;

// Create Modal Logic
if (openCreateModalBtn) {
    openCreateModalBtn.onclick = () => {
        createModal.style.display = 'block';
    };
}

if (cancelCreateBtn) {
    cancelCreateBtn.onclick = () => {
        createModal.style.display = 'none';
    };
}

// Delete Modal Logic
document.querySelectorAll('.delete-project-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();

        projectToDelete = {
            id: btn.getAttribute('data-id'),
            name: btn.getAttribute('data-name')
        };

        projectNameDisplay.textContent = projectToDelete.name;
        deleteFilesCheckbox.checked = false;
        deleteModal.style.display = 'block';
    });
});

cancelDeleteBtn.onclick = () => {
    deleteModal.style.display = 'none';
};

window.onclick = (event) => {
    if (event.target == deleteModal) {
        deleteModal.style.display = 'none';
    } else if (event.target == createModal) {
        createModal.style.display = 'none';
    }
};

confirmDeleteBtn.onclick = async () => {
    if (!projectToDelete) return;

    confirmDeleteBtn.disabled = true;
    confirmDeleteBtn.textContent = 'Deleting...';

    const formData = new FormData();
    formData.append('delete_files', deleteFilesCheckbox.checked);
    formData.append('csrfmiddlewaretoken', window.csrfToken);

    try {
        const response = await fetch(`/projects/${projectToDelete.id}/delete/`, {
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
        alert('Failed to delete project.');
    } finally {
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.textContent = 'Confirm Delete';
        deleteModal.style.display = 'none';
    }
};


// Add to Modal Logic
if (openImportModalBtn) {
    openImportModalBtn.onclick = () => {
        importModal.style.display = 'block';
    };
}

if (cancelImportBtn) {
    cancelImportBtn.onclick = () => {
        importModal.style.display = 'none';
    };
}

// Update the global window.onclick to close the import modal
window.onclick = (event) => {
    if (event.target == deleteModal) {
        deleteModal.style.display = 'none';
    } else if (event.target == createModal) {
        createModal.style.display = 'none';
    } else if (event.target == importModal) {
        importModal.style.display = 'none';
    }
};
const importProjectForm = document.getElementById('importProjectForm');
const importStatusText = document.getElementById('importStatusText');
const importProgressBar = document.getElementById('importProgressBar');
const closeImportModalBtn = document.getElementById('closeImportModalBtn');

if (importProjectForm) {
    importProjectForm.onsubmit = async (e) => {
        e.preventDefault();

        // UI Transitions
        document.getElementById('importInitialBody').style.display = 'none';
        document.getElementById('importProgressBody').style.display = 'block';
        document.getElementById('startImportBtn').style.display = 'none';
        document.getElementById('cancelImportBtn').style.display = 'none';

        const formData = new FormData(importProjectForm);
        const url = importProjectForm.getAttribute('action');

        try {
            importStatusText.textContent = "Validating and importing...";

            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            // Check if the response is actually JSON before parsing
            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error("Server returned an invalid response (likely an HTML error). Check Django logs.");
            }

            const result = await response.json();

            if (response.ok && result.status === 'success') {
                importProgressBar.style.width = '100%';
                importStatusText.textContent = "Import Complete!";
                closeImportModalBtn.style.display = 'block';
                setTimeout(() => location.reload(), 1000);
            } else {
                throw new Error(result.error || "Import failed");
            }
        } catch (error) {
            importStatusText.textContent = error.message;
            importStatusText.style.color = "#c0392b";
            closeImportModalBtn.style.display = 'block';
            closeImportModalBtn.textContent = "Close";
        }
    };
}