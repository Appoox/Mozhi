const deleteModal = document.getElementById('deleteModal');
const createModal = document.getElementById('createModal');
const openCreateModalBtn = document.getElementById('openCreateModalBtn');
const cancelCreateBtn = document.getElementById('cancelCreateBtn');

const projectNameDisplay = document.getElementById('projectNameDisplay');
const deleteFilesCheckbox = document.getElementById('deleteFilesCheckbox');
const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

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
