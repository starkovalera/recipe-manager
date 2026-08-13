const phone = document.querySelector(".phone");
const scrollArea = phone.querySelector(".editor-scroll");
const sections = [...phone.querySelectorAll(".accordion-section")];
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

function scrollHeaderIntoPlace(section, behavior = reducedMotion.matches ? "auto" : "smooth", block = "start") {
  requestAnimationFrame(() => {
    const header = section.querySelector(".section-toggle");
    const centerOffset = block === "center" ? (scrollArea.clientHeight - header.offsetHeight) / 2 : 0;
    scrollArea.scrollTo({ top: Math.max(0, section.offsetTop - centerOffset), behavior });
  });
}

function setExpanded(target, shouldExpand, options = {}) {
  sections.forEach((section) => {
    const expanded = section === target && shouldExpand;
    section.classList.toggle("is-expanded", expanded);
    const toggle = section.querySelector(".section-toggle");
    toggle.setAttribute("aria-expanded", String(expanded));
    section.querySelector(".section-panel").hidden = !expanded;
    section.querySelector(".chevron").textContent = expanded ? "⌃" : "⌄";
    section.querySelector(".state-label").textContent = expanded ? "Editing" : "";
  });
  if (target && options.scroll !== false) scrollHeaderIntoPlace(target, options.behavior, shouldExpand ? "start" : "center");
}

sections.forEach((section) => {
  section.querySelector(".section-toggle").addEventListener("click", () => {
    const isExpanded = section.classList.contains("is-expanded");
    setExpanded(section, !isExpanded);
  });
});

function closeLayers() {
  phone.querySelectorAll(".bottom-sheet, .popover, .scrim").forEach((element) => { element.hidden = true; });
  phone.querySelectorAll("[aria-expanded]").forEach((element) => {
    if (!element.classList.contains("section-toggle")) element.setAttribute("aria-expanded", "false");
  });
}

phone.querySelector(".mode-trigger").addEventListener("click", (event) => {
  closeLayers();
  phone.querySelector(".scrim").hidden = false;
  phone.querySelector(".mode-sheet").hidden = false;
  event.currentTarget.setAttribute("aria-expanded", "true");
});
phone.querySelector(".more-trigger").addEventListener("click", (event) => {
  const menu = phone.querySelector(".more-menu");
  const willOpen = menu.hidden;
  closeLayers();
  menu.hidden = !willOpen;
  event.currentTarget.setAttribute("aria-expanded", String(willOpen));
});
phone.querySelectorAll(".sheet-close, .scrim").forEach((element) => element.addEventListener("click", closeLayers));

document.querySelectorAll("[data-scenario]").forEach((button) => {
  button.addEventListener("click", () => {
    const scenario = button.dataset.scenario;
    if (scenario === "overview") {
      const current = sections.find((section) => section.classList.contains("is-expanded")) || sections[0];
      setExpanded(current, false, { behavior: "auto" });
      return;
    }
    const sectionName = scenario === "default" ? "basics" : scenario.replace("deep-", "");
    const section = sections.find((candidate) => candidate.dataset.section === sectionName);
    setExpanded(section, true, { behavior: "auto" });
    if (scenario.startsWith("deep-")) {
      requestAnimationFrame(() => requestAnimationFrame(() => {
        const rows = section.querySelectorAll("li");
        const targetRow = rows[Math.max(0, rows.length - 3)];
        const rowTopInViewport = targetRow.getBoundingClientRect().top - scrollArea.getBoundingClientRect().top;
        scrollArea.scrollTop += rowTopInViewport - 110;
      }));
    }
  });
});
