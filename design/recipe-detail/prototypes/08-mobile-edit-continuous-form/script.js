const sectionNames = {
  basics: "Basics",
  ingredients: "Ingredients",
  instructions: "Instructions",
  notes: "Cooking notes",
  nutrition: "Nutrition",
};

function closeLayers(phone) {
  phone.querySelectorAll(".bottom-sheet, .popover, .scrim").forEach((element) => { element.hidden = true; });
  phone.querySelectorAll("[aria-expanded]").forEach((element) => element.setAttribute("aria-expanded", "false"));
}

function openSheet(phone, selector, trigger) {
  closeLayers(phone);
  phone.querySelector(".scrim").hidden = false;
  phone.querySelector(selector).hidden = false;
  trigger.setAttribute("aria-expanded", "true");
}

function jumpTo(phone, section) {
  const target = phone.querySelector(`[data-section="${section}"]`);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  target.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
  closeLayers(phone);
}

document.querySelectorAll(".phone").forEach((phone) => {
  const scrollArea = phone.querySelector(".editor-scroll");
  const current = phone.querySelector(".current-section");
  const sections = [...phone.querySelectorAll("[data-section]")];

  phone.querySelector(".section-trigger").addEventListener("click", (event) => openSheet(phone, ".section-sheet", event.currentTarget));
  phone.querySelector(".mode-trigger")?.addEventListener("click", (event) => openSheet(phone, ".mode-sheet", event.currentTarget));
  phone.querySelector(".more-trigger").addEventListener("click", (event) => {
    const menu = phone.querySelector(".more-menu");
    const willOpen = menu.hidden;
    closeLayers(phone);
    menu.hidden = !willOpen;
    event.currentTarget.setAttribute("aria-expanded", String(willOpen));
  });
  phone.querySelectorAll(".sheet-close, .scrim").forEach((element) => element.addEventListener("click", () => closeLayers(phone)));
  phone.querySelectorAll("[data-jump]").forEach((button) => button.addEventListener("click", () => jumpTo(phone, button.dataset.jump)));

  scrollArea.addEventListener("scroll", () => {
    const top = scrollArea.getBoundingClientRect().top + 28;
    let active = sections[0].dataset.section;
    sections.forEach((section) => {
      if (section.getBoundingClientRect().top <= top) active = section.dataset.section;
    });
    current.textContent = sectionNames[active];
  }, { passive: true });
});

document.querySelectorAll("[data-jump-all]").forEach((button) => {
  button.addEventListener("click", () => document.querySelectorAll(".phone").forEach((phone) => jumpTo(phone, button.dataset.jumpAll)));
});
