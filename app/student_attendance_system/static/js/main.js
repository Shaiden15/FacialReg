// Main JavaScript file for the application

// Function to preview image before upload
function previewImage(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            const preview = document.getElementById('avatar-preview');
            if (preview) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
        }
        
        reader.readAsDataURL(input.files[0]);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add active class to current nav item
    var current = location.pathname;
    document.querySelectorAll('.nav-link').forEach(function(link) {
        if(link.getAttribute('href') === current) {
            link.classList.add('active');
            link.setAttribute('aria-current', 'page');
        }
    });
});
