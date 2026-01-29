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

const isAuthenticated = () => Boolean(localStorage.getItem("access_token"));
const isAuth = isAuthenticated();
if (isAuth && (loginForm || registerForm)) {
  window.location.href = "index.html";
}

document.addEventListener("click", (event) => {
  const target = event.target.closest(".info-panel__cta, .info-media img, .info-media");
  if (!target) return;
  if (!isAuthenticated()) {
    event.preventDefault();
    window.location.href = "register.html";
  }
});

if (isAuth && document.body.classList.contains("home")) {
  const hero = document.querySelector(".hero");
  if (hero) {
    hero.style.display = "none";
  }
}

const authQuick = document.querySelector(".auth-quick");
if (authQuick) {
  authQuick.style.display = isAuth ? "block" : "none";
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

const appletModal = document.getElementById("applet-modal");
const appletPlus = document.querySelector(".auth-quick__plus");
const appletSteps = document.querySelectorAll(".applet-step");
const appletDots = document.querySelectorAll(".applet-dot");
let appletStepIndex = 0;
let actionService = null;
let reactionService = null;
let actionChoice = null;
let reactionChoice = null;

const filterStepByService = (stepNumber, service) => {
  const step = document.querySelector(`.applet-step[data-step="${stepNumber}"]`);
  if (!step) return;
  const cards = step.querySelectorAll(".applet-card[data-service]");
  cards.forEach((card) => {
    const matches = !service || card.dataset.service === service;
    card.hidden = false;
    card.style.display = matches ? "flex" : "none";
  });
};

const showConfig = (choiceKey) => {
  const configs = document.querySelectorAll(".applet-config");
  configs.forEach((config) => {
    config.hidden = config.dataset.config !== choiceKey;
  });
};

const updateAppletSteps = () => {
  appletSteps.forEach((step, index) => {
    step.hidden = index !== appletStepIndex;
  });
  appletDots.forEach((dot, index) => {
    dot.classList.toggle("is-active", index === appletStepIndex);
  });
  filterStepByService(2, actionService);
  filterStepByService(5, reactionService);
  if (appletStepIndex + 1 === 3) {
    showConfig(actionChoice);
  }
  if (appletStepIndex + 1 === 6) {
    showConfig(reactionChoice);
  }
  if (appletStepIndex + 1 === 7) {
    const actionLogo = document.querySelector("[data-confirm='action']");
    const reactionLogo = document.querySelector("[data-confirm='reaction']");
    if (actionLogo) {
      actionLogo.src = actionService === "agenda" ? "assets/agenda.webp" : "assets/gmail.webp";
    }
    if (reactionLogo) {
      reactionLogo.src = reactionService === "agenda" ? "assets/agenda.webp" : "assets/gmail.webp";
    }
  }
  updateNextButtonState();
};

const updateNextButtonState = () => {
  if (!appletNext) return;
  const currentStep = appletStepIndex + 1;
  let enabled = true;
  if (currentStep === 1) enabled = Boolean(actionService);
  if (currentStep === 2) enabled = Boolean(actionChoice);
  if (currentStep === 3) enabled = Boolean(actionChoice);
  if (currentStep === 4) enabled = Boolean(reactionService);
  if (currentStep === 5) enabled = Boolean(reactionChoice);
  if (currentStep === 6) enabled = Boolean(reactionChoice);
  if (currentStep === 7) enabled = true;
  appletNext.disabled = !enabled;
  appletNext.classList.toggle("is-disabled", !enabled);
};

const openAppletModal = () => {
  if (!appletModal) return;
  appletStepIndex = 0;
  actionService = null;
  reactionService = null;
  actionChoice = null;
  reactionChoice = null;
  updateAppletSteps();
  appletModal.classList.add("is-open");
  appletModal.setAttribute("aria-hidden", "false");
};

const closeAppletModal = () => {
  if (!appletModal) return;
  appletModal.classList.remove("is-open");
  appletModal.setAttribute("aria-hidden", "true");
};

if (appletPlus) {
  appletPlus.addEventListener("click", openAppletModal);
}

if (appletModal) {
  appletModal.addEventListener("click", (event) => {
    const target = event.target;
    if (target && target.getAttribute("data-applet-close") === "true") {
      closeAppletModal();
    }
    const card = target?.closest(".applet-card[data-service]");
    const step = target?.closest(".applet-step");
    if (card && step) {
      const stepNumber = Number(step.dataset.step);
      const service = card.dataset.service;
      const choice = card.dataset.choice;
      const cards = step.querySelectorAll(".applet-card");
      cards.forEach((item) => item.classList.remove("is-selected"));
      card.classList.add("is-selected");
      if (stepNumber === 1) {
        actionService = service;
        actionChoice = null;
      }
      if (stepNumber === 2) {
        actionChoice = choice || null;
      }
      if (stepNumber === 4) {
        reactionService = service;
        reactionChoice = null;
      }
      if (stepNumber === 5) {
        reactionChoice = choice || null;
      }
      updateAppletSteps();
    }
  });
}

const appletPrev = document.querySelector("[data-applet-prev='true']");
const appletNext = document.querySelector("[data-applet-next='true']");

if (appletPrev) {
  appletPrev.addEventListener("click", () => {
    appletStepIndex = Math.max(0, appletStepIndex - 1);
    updateAppletSteps();
  });
}

if (appletNext) {
  appletNext.addEventListener("click", () => {
    appletStepIndex = Math.min(appletSteps.length - 1, appletStepIndex + 1);
    updateAppletSteps();
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
