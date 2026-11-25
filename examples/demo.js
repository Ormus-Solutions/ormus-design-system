// Reveal on scroll: adds .is-revealed to each .fusion-reveal when it enters
// the viewport. Without this script (or with reduced motion) the content
// stays visible, because fusion.css hides it only when scripting is enabled.
(function () {
  var items = document.querySelectorAll(".fusion-reveal");
  if (!("IntersectionObserver" in window)) {
    items.forEach(function (el) { el.classList.add("is-revealed"); });
    return;
  }
  var seen = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-revealed");
        seen.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });
  items.forEach(function (el) { seen.observe(el); });
})();
