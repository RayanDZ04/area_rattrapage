const form = document.getElementById("login-form");

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const payload = Object.fromEntries(data.entries());
  console.log("Login payload:", payload);
  alert("UI uniquement pour l'instant. Backend bientôt.");
});
