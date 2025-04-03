//5sec alert
document.addEventListener("DOMContentLoaded", function () {
    setTimeout(function () {
        let messages = document.querySelectorAll('.messages');
        messages.forEach((message) => {
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 100); 
        });
    }, 5000);
});

