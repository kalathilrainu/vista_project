// kiosk.js

document.addEventListener('DOMContentLoaded', function () {
    console.log('Kiosk JS Loaded');

    // Auto-print logic for token page
    if (window.location.pathname.includes('/token/') && window.location.pathname.includes('/print/')) {
        // Optional: uncomment to auto print
        // window.print();

        // Auto-redirect after some time?
        setTimeout(() => {
            // window.location.href = "/visit/kiosk/"; 
        }, 30000);
    }

    // Animate buttons on touch
    const buttons = document.querySelectorAll('.btn, .card');
    buttons.forEach(btn => {
        btn.addEventListener('touchstart', function () {
            this.style.transform = 'scale(0.95)';
        });
        btn.addEventListener('touchend', function () {
            this.style.transform = 'scale(1)';
        });
    });
});
