document.addEventListener('DOMContentLoaded', () => {

    // Mobile Menu Toggle
    const menuToggle = document.querySelector('.menu-toggle');
    const navList = document.querySelector('.nav-list');

    if (menuToggle && navList) {
        menuToggle.addEventListener('click', () => {
            navList.classList.toggle('active');
            const expanded = navList.classList.contains('active');
            menuToggle.setAttribute('aria-expanded', expanded);
        });
    }

    // Service Search Placeholder
    const searchBtn = document.querySelector('.btn-search');
    const searchInput = document.getElementById('serviceSearch');

    if (searchBtn && searchInput) {
        const handleSearch = () => {
            const query = searchInput.value.trim();
            if (query) {
                alert(`Search functionality for "${query}" is coming soon. Please browse the services below.`);
            }
        };

        searchBtn.addEventListener('click', handleSearch);
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleSearch();
        });
    }

    // Dropdown handling for touch devices
    const dropdowns = document.querySelectorAll('.dropdown-toggle');
    dropdowns.forEach(dropdown => {
        dropdown.addEventListener('click', (e) => {
            if (window.innerWidth < 768) {
                e.preventDefault();
                const parent = dropdown.parentElement;
                parent.classList.toggle('active');
            }
        });
    });

    // --------------------------------------------------------
    // 1. Toast Notification Initialization
    // --------------------------------------------------------
    const toastElList = document.querySelectorAll('.toast');
    const toastList = [...toastElList].map(toastEl => {
        const toast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 5000
        });
        toast.show();
        return toast;
    });

    // --------------------------------------------------------
    // 2. Global Loading State
    // --------------------------------------------------------
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function (e) {
            if (!this.checkValidity()) return;

            const submitButtons = this.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(btn => {
                // Prevent double submit if already disabled
                if (btn.classList.contains('disabled')) {
                    e.preventDefault();
                    return;
                }

                // Save original width to prevent jarring layout shift
                const width = btn.offsetWidth;
                btn.style.width = `${width}px`;

                btn.classList.add('disabled');
                // Replace text with spinner
                btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`;
            });
        });
    });

});
