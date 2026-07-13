// Upload Dropzone & Form Handler
document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('resume_file');
    const filePreview = document.getElementById('file-preview');
    const fileNameEl = document.getElementById('file-preview-name');
    const fileSizeEl = document.getElementById('file-preview-size');
    const removeBtn = document.getElementById('remove-file-btn');
    const uploadForm = document.getElementById('upload-form');
    const submitBtn = document.getElementById('submit-btn');

    if (!dropzone || !fileInput) return;

    // Dragover & Dragleave
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    // Handle Drop
    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateFilePreview(files[0]);
        }
    });

    // Handle File Pick
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            updateFilePreview(fileInput.files[0]);
        }
    });

    // Remove File
    removeBtn.addEventListener('click', () => {
        fileInput.value = '';
        filePreview.style.display = 'none';
        dropzone.style.display = 'block';
    });

    function updateFilePreview(file) {
        fileNameEl.textContent = file.name;
        fileSizeEl.textContent = formatBytes(file.size);
        dropzone.style.display = 'none';
        filePreview.style.display = 'flex';
    }

    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    // Submit Loading State
    uploadForm.addEventListener('submit', () => {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Analyzing Resume... Please Wait`;
    });
});
