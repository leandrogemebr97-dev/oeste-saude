// Carência Page JavaScript - Refatorado para SAC

document.addEventListener('DOMContentLoaded', function() {
  // Animação de entrada para cards
  const cards = document.querySelectorAll('.carencia-card, .destaque-card');
  
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, index) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }, index * 100);
      }
    });
  }, observerOptions);

  cards.forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    observer.observe(card);
  });

  // Destaque ao clicar em tags para filtrar (visual apenas)
  const tags = document.querySelectorAll('.tag');
  tags.forEach(tag => {
    tag.addEventListener('click', function() {
      // Remove destaque de outros
      tags.forEach(t => t.style.transform = 'scale(1)');
      // Destaca o clicado
      this.style.transform = 'scale(1.1)';
      setTimeout(() => {
        this.style.transform = 'scale(1)';
      }, 200);
    });
  });

  // Tooltip para observações importantes
  const observacoes = document.querySelectorAll('.observacao');
  observacoes.forEach(obs => {
    obs.title = 'Atenção: Verifique regras específicas';
  });

  // Console log para SAC - atalhos úteis
  console.log('%c🩺 TABELA DE CARÊNCIAS - SAC OESTE SAÚDE', 'color: #1a5490; font-size: 16px; font-weight: bold;');
  console.log('%cAtalhos rápidos:', 'color: #28a745; font-weight: bold;');
  console.log('• 24h: Consultas, Exames Lab, Internações, Cirurgias, Urgência');
  console.log('• 30d: Exames de Imagem');
  console.log('• 60d: Fisioterapia, Fonoaudiologia');
  console.log('• 300d: Parto a termo');
  console.log('• 24m: Transplantes');
  console.log('%c⚠️ ACIDENTE PESSOAL = SEM CARÊNCIA', 'color: #dc3545; font-weight: bold;');
});
