document.addEventListener('DOMContentLoaded', () => {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-visible');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.slide-up').forEach(el => observer.observe(el));

    // Testimonial carousel functionality
    let currentTestimonialIndex = 0;
    const testimonials = document.querySelectorAll('.testimonial-card');
    const dots = document.querySelectorAll('.dot');
    const totalTestimonials = testimonials.length;

    function showTestimonial(index) {
        // Hide all testimonials
        testimonials.forEach((testimonial, i) => {
            testimonial.classList.remove('active', 'prev');
            if (i < index) {
                testimonial.classList.add('prev');
            }
        });

        // Remove active class from all dots
        dots.forEach(dot => dot.classList.remove('active'));

        // Show current testimonial
        testimonials[index].classList.add('active');
        dots[index].classList.add('active');
        currentTestimonialIndex = index;
    }

    // Make functions globally accessible
    window.changeTestimonial = function(direction) {
        let newIndex = currentTestimonialIndex + direction;
        
        if (newIndex < 0) {
            newIndex = totalTestimonials - 1;
        } else if (newIndex >= totalTestimonials) {
            newIndex = 0;
        }
        
        showTestimonial(newIndex);
    };

    window.currentTestimonial = function(index) {
        showTestimonial(index - 1);
    };

    // Auto-rotate testimonials every 5 seconds
    setInterval(() => {
        changeTestimonial(1);
    }, 5000);

    // Initialize first testimonial
    showTestimonial(0);
});
