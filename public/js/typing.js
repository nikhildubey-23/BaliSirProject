const typeWriter = (elementId, text, speed) => {
  let i = 0;
  const element = document.getElementById(elementId);
  if (!element) return;
  const type = () => {
    if (i <= text.length) {
      element.innerHTML = text.substring(0, i) + '<span class="cursor">|</span>';
      i++;
      setTimeout(type, speed);
    } else {
      i = 0;
      setTimeout(type, speed);
    }
  };
  type();
};

document.addEventListener('DOMContentLoaded', () => {
  typeWriter('typing-text', 'Why Choose us.', 150);
  typeWriter('typing-service', 'Our Services', 150);
});
