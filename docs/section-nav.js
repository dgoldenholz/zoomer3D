(() => {
  const header = document.querySelector('.site-header');
  if (!header) return;

  // Keep anchor destinations below the ribbon as fonts or viewport size change.
  const updateOffset = () => {
    document.documentElement.style.setProperty('--ribbon-height', `${Math.ceil(header.getBoundingClientRect().height)}px`);
  };
  updateOffset();
  if ('ResizeObserver' in window) {
    new ResizeObserver(updateOffset).observe(header);
  } else {
    window.addEventListener('resize', updateOffset, { passive: true });
  }
})();
