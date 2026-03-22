// ========== MAIN JS ==========

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', () => {
    const flashContainer = document.getElementById('flashContainer');
    if (flashContainer) {
        setTimeout(() => {
            flashContainer.querySelectorAll('.flash-message').forEach((msg, i) => {
                setTimeout(() => {
                    msg.style.transition = 'all 0.4s ease';
                    msg.style.opacity = '0';
                    msg.style.transform = 'translateX(100%)';
                    setTimeout(() => msg.remove(), 400);
                }, i * 200);
            });
        }, 4000);
    }

    // Animate stat counters on landing page
    animateCounters();

    // Intersection observer for fade-in animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationDelay = '0.1s';
                entry.target.classList.add('animate-fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.feature-card, .step-card, .insight-card').forEach(el => {
        observer.observe(el);
    });
});

// Counter Animation
function animateCounters() {
    document.querySelectorAll('[data-count]').forEach(counter => {
        const target = parseInt(counter.dataset.count);
        const duration = 2000;
        const step = target / (duration / 16);
        let current = 0;

        const update = () => {
            current += step;
            if (current >= target) {
                counter.textContent = target.toLocaleString();
                return;
            }
            counter.textContent = Math.floor(current).toLocaleString();
            requestAnimationFrame(update);
        };

        // Start when visible
        const obs = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                update();
                obs.disconnect();
            }
        });
        obs.observe(counter);
    });
}

// Password Toggle
function togglePassword(fieldId, btn) {
    const field = document.getElementById(fieldId);
    const icon = btn.querySelector('i');
    if (field.type === 'password') {
        field.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        field.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.querySelector(link.getAttribute('href'));
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
});
