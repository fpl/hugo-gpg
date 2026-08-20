(function () {
  "use strict";
  var KEY = "gpg-theme";
  var STATES = ["auto", "light", "dark"];
  var LABELS = { auto: "automatico", light: "chiaro", dark: "scuro" };
  var btn = document.getElementById("theme-toggle");
  if (!btn) return;

  function getPref() {
    try {
      var v = localStorage.getItem(KEY);
      return STATES.indexOf(v) !== -1 ? v : "auto";
    } catch (e) {
      return "auto";
    }
  }

  function apply(pref) {
    if (pref === "light" || pref === "dark") {
      document.documentElement.setAttribute("data-theme", pref);
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    btn.setAttribute("data-mode", pref);
    btn.setAttribute("aria-label", "Tema: " + LABELS[pref] + ". Clicca per cambiare.");
  }

  apply(getPref());

  btn.addEventListener("click", function () {
    var next = STATES[(STATES.indexOf(getPref()) + 1) % STATES.length];
    try {
      localStorage.setItem(KEY, next);
    } catch (e) {}
    apply(next);
  });
})();
