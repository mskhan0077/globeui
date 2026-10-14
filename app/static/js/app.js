document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("config-form");
  if (!form) return;
  form.addEventListener("change", () => {
    console.log("config:", {
      island: form.island.value,
      load_kW: Number(form.load_kW.value),
    });
  });
});