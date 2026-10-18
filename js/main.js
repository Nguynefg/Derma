// Khởi tạo Lucide Icons
if (window.lucide) {
  lucide.createIcons();
}

// Chế độ Sáng / Tối (Dark / Light Mode)
const themeToggleBtn = document.getElementById('themeToggle');
const htmlElement = document.documentElement;

// Kiểm tra cấu hình đã lưu hoặc theo hệ điều hành
if (
  localStorage.getItem('theme') === 'dark' ||
  (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)
) {
  htmlElement.classList.add('dark');
} else {
  htmlElement.classList.remove('dark');
}

if (themeToggleBtn) {
  themeToggleBtn.addEventListener('click', () => {
    htmlElement.classList.toggle('dark');
    if (htmlElement.classList.contains('dark')) {
      localStorage.setItem('theme', 'dark');
    } else {
      localStorage.setItem('theme', 'light');
    }
  });
}

// Menu đóng/mở trên thiết bị di động (Mobile Menu)
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const mobileMenu = document.getElementById('mobileMenu');

if (mobileMenuBtn && mobileMenu) {
  mobileMenuBtn.addEventListener('click', () => {
    mobileMenu.classList.toggle('hidden');
  });

  // Tự động đóng menu khi bấm vào link điều hướng
  mobileMenu.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      mobileMenu.classList.add('hidden');
    });
  });
}

// Accordion Câu hỏi thường gặp (FAQ)
const faqButtons = document.querySelectorAll('.faq-btn');
faqButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    const content = btn.nextElementSibling;
    const icon = btn.querySelector('[data-lucide="chevron-down"]');
    const isHidden = content.classList.contains('hidden');

    // Đóng các mục khác
    document.querySelectorAll('.faq-content').forEach((c) => c.classList.add('hidden'));
    document
      .querySelectorAll('.faq-btn [data-lucide="chevron-down"]')
      .forEach((i) => (i.style.transform = 'rotate(0deg)'));

    // Mở mục hiện tại nếu đang ẩn
    if (isHidden) {
      content.classList.remove('hidden');
      if (icon) icon.style.transform = 'rotate(180deg)';
    }
  });
});

// Hiệu ứng bóng thanh điều hướng khi cuộn trang
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  if (navbar) {
    if (window.scrollY > 20) {
      navbar.classList.add('glass', 'shadow-sm');
    } else {
      navbar.classList.remove('glass', 'shadow-sm');
    }
  }
});
