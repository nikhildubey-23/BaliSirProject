// Consolidated JavaScript file - All scripts from individual JS files

// Typing animation script
document.addEventListener('DOMContentLoaded', () => {
  const typingTextElement = document.getElementById('faith-typing');
  const text = "The faith that Fuels us\n50,000+\nHappy customers\nand still counting..";
  let index = 0;

  function type() {
    if (index < text.length) {
      typingTextElement.innerText += text.charAt(index);
      index++;
      setTimeout(type, 100); // typing speed in ms
    } else {
      // After typing, convert \n to <br> and add highlight
      typingTextElement.innerHTML = typingTextElement.innerText.replace(/\n/g, '<br>').replace('Fuels us', '<span class="faith-highlight">Fuels us</span>');
    }
  }

  // Clear the text initially
  typingTextElement.innerText = '';
  type();
});

// Testimonials and FAQ scripts
document.addEventListener('DOMContentLoaded', () => {
  const testimonials = [
    {
      name: "Naveen Chandrakar",
      text: "“Mujhe insurance ke terms sunke hamesha confusion hota tha. ’Bima with Bali’ ne sab itna aasan bana diya jaise koi dost samjha raha ho chai ke saath. Mazaa aa gaya!\""
    },
    {
      name: "Ashok Kumar",
      text: "“Finally koi mila jo insurance boring way mein nahi, fun aur relatable tareeke se samjhata hai! Bali ki baatein simple aur clear hoti hain. Ab apna policy choose karna easy lagta hai.”"
    },
    {
      name: "Smitha Tiwari",
      text: "“Have customers review you and share what they had to say.”"
    },
    {
      name: "Rahul Dhruw",
      text: "Customer care wale bahut helpful the. Unhone patience se health insurance ka renewal process samjhaya. Main kaafi satisfied hoon"
    }
  ];

  let currentIndex = 0;

  const nameEl = document.getElementById('testimonial-name');
  const textEl = document.getElementById('testimonial-text');
  const dots = document.querySelectorAll('.dot');

  function fadeOutIn(element, newText) {
    element.style.opacity = 0;
    setTimeout(() => {
      element.textContent = newText;
      element.style.opacity = 1;
    }, 500);
  }

  function updateTestimonial(index) {
    currentIndex = index;
    fadeOutIn(nameEl, testimonials[index].name);
    fadeOutIn(textEl, testimonials[index].text);
    dots.forEach(dot => dot.classList.remove('active'));
    dots[index].classList.add('active');
  }

  document.getElementById('arrow-left').addEventListener('click', () => {
    let newIndex = currentIndex - 1;
    if (newIndex < 0) newIndex = testimonials.length - 1;
    updateTestimonial(newIndex);
  });

  document.getElementById('arrow-right').addEventListener('click', () => {
    let newIndex = currentIndex + 1;
    if (newIndex >= testimonials.length) newIndex = 0;
    updateTestimonial(newIndex);
  });

  dots.forEach(dot => {
    dot.addEventListener('click', (e) => {
      const index = parseInt(e.target.getAttribute('data-index'));
      updateTestimonial(index);
    });
  });

  // Set initial testimonial
  updateTestimonial(currentIndex);

  // Auto slide change every 2 seconds
  setInterval(() => {
    let newIndex = currentIndex + 1;
    if (newIndex >= testimonials.length) newIndex = 0;
    updateTestimonial(newIndex);
  }, 2000);
});

document.querySelectorAll('.faq-question').forEach(question => {
  question.addEventListener('click', () => {
    const currentlyActive = document.querySelector('.faq-answer.show');
    if (currentlyActive && currentlyActive !== question.nextElementSibling) {
      currentlyActive.classList.remove('show');
      currentlyActive.style.maxHeight = null;
    }
    const answer = question.nextElementSibling;
    if (answer.classList.contains('show')) {
      answer.classList.remove('show');
      answer.style.maxHeight = null;
    } else {
      answer.classList.add('show');
      answer.style.maxHeight = answer.scrollHeight + "px";
    }
  });
});
