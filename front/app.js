const API_URL = "http://localhost:8080";

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");

const setUserDisplay = () => {
  const firstName = localStorage.getItem("user_first_name");
  const token = localStorage.getItem("access_token");
  const userDisplay = document.querySelector(".user-display");

  if (token || firstName) {
    document.body.classList.add("is-authenticated");
  }

  if (firstName && userDisplay) {
    userDisplay.textContent = firstName;
    userDisplay.setAttribute("href", "settings.html");
  }
};

const applyAuthFromUrl = () => {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  const firstName = params.get("first_name");
  if (token) {
    localStorage.setItem("access_token", token);
  }
  if (firstName) {
    localStorage.setItem("user_first_name", firstName);
  }
  if (token || firstName) {
    window.history.replaceState({}, document.title, window.location.pathname);
  }
};

applyAuthFromUrl();
setUserDisplay();

const isAuth = Boolean(localStorage.getItem("access_token"));
if (isAuth && (loginForm || registerForm)) {
  window.location.href = "index.html";
}

if (isAuth && document.body.classList.contains("home")) {
  const hero = document.querySelector(".hero");
  if (hero) {
    hero.style.display = "none";
  }
}

const settingsForm = document.getElementById("settings-form");
if (settingsForm && !isAuth) {
  window.location.href = "login.html";
}

const loadSettings = async () => {
  if (!settingsForm || !isAuth) return;
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) return;
  const user = await response.json();
  settingsForm.elements.first_name.value = user.first_name || "";
  settingsForm.elements.last_name.value = user.last_name || "";
};

loadSettings();

if (registerForm) {
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(registerForm);
    const payload = Object.fromEntries(data.entries());

    const registerResponse = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        first_name: payload.first_name,
        last_name: payload.last_name,
        email: payload.email,
        password: payload.password,
      }),
    });

    if (!registerResponse.ok) {
      const errorText = await registerResponse.text();
      alert(`Inscription échouée: ${errorText}`);
      return;
    }

    const loginResponse = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: payload.email,
        password: payload.password,
      }),
    });

    if (!loginResponse.ok) {
      alert("Inscription OK, mais connexion échouée. Va sur la page connexion.");
      window.location.href = "login.html";
      return;
    }

    const result = await loginResponse.json();
    localStorage.setItem("access_token", result.access_token);
    localStorage.setItem("user_first_name", result.user.first_name);
    window.location.href = "index.html";
  });
}

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(loginForm);
    const payload = Object.fromEntries(data.entries());

    const response = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: payload.email,
        password: payload.password,
      }),
    });

    if (!response.ok) {
      alert("Connexion échouée");
      return;
    }

    const result = await response.json();
    localStorage.setItem("access_token", result.access_token);
    localStorage.setItem("user_first_name", result.user.first_name);
    window.location.href = "index.html";
  });
}

const logoutButton = document.getElementById("logout-button");
if (logoutButton) {
  logoutButton.addEventListener("click", () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_first_name");
    window.location.href = "index.html";
  });
}

const googleButtons = document.querySelectorAll(".google-auth");
googleButtons.forEach((button) => {
  button.addEventListener("click", () => {
    window.location.href = "http://localhost:8080/auth/google/login";
  });
});

const serviceModal = document.getElementById("service-modal");
const searchInput = document.querySelector(".top-actions .search input");
const searchBar = document.querySelector(".top-actions .search");

const openServiceModal = () => {
  if (!serviceModal) return;
  serviceModal.classList.add("is-open");
  serviceModal.setAttribute("aria-hidden", "false");
};

const closeServiceModal = () => {
  if (!serviceModal) return;
  serviceModal.classList.remove("is-open");
  serviceModal.setAttribute("aria-hidden", "true");
};

if (searchInput) {
  searchInput.addEventListener("focus", openServiceModal);
  searchInput.addEventListener("click", openServiceModal);
}

if (searchBar) {
  searchBar.addEventListener("click", openServiceModal);
}

if (serviceModal) {
  serviceModal.addEventListener("click", (event) => {
    const target = event.target;
    if (target && target.getAttribute("data-close") === "true") {
      closeServiceModal();
    }
  });
}

if (settingsForm) {
  settingsForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(settingsForm);
    const payload = Object.fromEntries(data.entries());
    const token = localStorage.getItem("access_token");

    const response = await fetch(`${API_URL}/auth/me`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        first_name: payload.first_name,
        last_name: payload.last_name,
      }),
    });

    if (!response.ok) {
      alert("Mise à jour échouée");
      return;
    }

    const user = await response.json();
    localStorage.setItem("user_first_name", user.first_name);
    setUserDisplay();
    alert("Profil mis à jour");
  });
}

const homeMediaImage = document.querySelector(".info-media img");
if (homeMediaImage) {
  const homeImages = [
    "assets/acceuil_1.png",
    "assets/acceuil_2.png",
    "assets/acceuil_2_1.png",
    "assets/acceuil_3.png",
    "assets/acceuil_4.png",
    "assets/acceuil_5.png",
    "assets/acceuil_6.png",
    "assets/acceuil_7.png",
    "assets/acceuil_8.png",
    "assets/acceuil_9.png",
    "assets/acceuil_10.png",
  ];
  let currentIndex = 0;

  setInterval(() => {
    currentIndex = (currentIndex + 1) % homeImages.length;
    homeMediaImage.src = homeImages[currentIndex];
  }, 3000);
}
