const API_BASE = "http://localhost:5001/api";

const state = {
  currentWallet: null,
  walletMode: "manual",
  backendConnected: false,
  policies: [],
  ndviChart: null,
  loadingCount: 0,
  lastApiCall: null,
  lastApiResponse: null,
  selectedPolicyId: "",
  isSubmittingPolicy: false,
};

const dom = {};

document.addEventListener("DOMContentLoaded", () => {
  // Bind submit handler immediately so native form submit never navigates away.
  const registrationForm = document.getElementById("registrationForm");
  if (registrationForm) {
    registrationForm.addEventListener("submit", (event) => {
      event.preventDefault();
      event.stopPropagation();
      handleRegistration(event);
    });
  }

  initializeApp().catch((error) => {
    console.error("Initialization failed:", error);
    showToast("App failed to initialize. Please refresh the page.", "error");
  });
});

function cacheDom() {
  dom.navLinks = [...document.querySelectorAll(".nav-links a")];
  dom.navDashboard = document.getElementById("navDashboard");
  dom.navClaims = document.getElementById("navClaims");
  dom.backendStatus = document.getElementById("backendStatus");
  dom.backendStatusText = document.getElementById("backendStatusText");
  dom.backendBanner = document.getElementById("backendBanner");
  dom.retryHealthBtn = document.getElementById("retryHealthBtn");

  dom.connectWallet = document.getElementById("connectWallet");
  dom.walletBtnText = document.getElementById("walletBtnText");
  dom.metamaskStatus = document.getElementById("metamaskStatus");
  dom.autoFillWalletBtn = document.getElementById("autoFillWalletBtn");
  dom.skipWalletBtn = document.getElementById("skipWalletBtn");
  dom.walletAddress = document.getElementById("walletAddress");

  dom.getStartedBtn = document.getElementById("getStartedBtn");
  dom.homeRefreshBtn = document.getElementById("homeRefreshBtn");

  dom.registrationForm = document.getElementById("registrationForm");
  dom.formErrors = document.getElementById("formErrors");
  dom.getLocationBtn = document.getElementById("getLocationBtn");
  dom.previewWeatherBtn = document.getElementById("previewWeatherBtn");
  dom.loadDemoBtn = document.getElementById("loadDemoBtn");
  dom.createPolicyBtn = document.getElementById("createPolicyBtn");
  dom.premiumAmount = document.getElementById("premiumAmount");
  dom.coverageAmount = document.getElementById("coverageAmount");
  dom.weatherPreview = document.getElementById("weatherPreview");
  dom.weatherPreviewContent = document.getElementById("weatherPreviewContent");

  dom.policySelect = document.getElementById("policySelect");
  dom.refreshPoliciesBtn = document.getElementById("refreshPoliciesBtn");
  dom.emptyRefreshPoliciesBtn = document.getElementById(
    "emptyRefreshPoliciesBtn",
  );
  dom.policyEmptyState = document.getElementById("policyEmptyState");

  dom.totalPolicies = document.getElementById("totalPolicies");
  dom.totalClaims = document.getElementById("totalClaims");
  dom.totalPayout = document.getElementById("totalPayout");

  dom.policyStatus = document.getElementById("policyStatus");
  dom.policyInfoContent = document.getElementById("policyInfoContent");
  dom.weatherTrigger = document.getElementById("weatherTrigger");
  dom.weatherContent = document.getElementById("weatherContent");
  dom.ndviTrigger = document.getElementById("ndviTrigger");
  dom.ndviContent = document.getElementById("ndviContent");
  dom.predictionContent = document.getElementById("predictionContent");
  dom.claimEligibility = document.getElementById("claimEligibility");

  dom.claimsTableBody = document.getElementById("claimsTableBody");
  dom.refreshClaimsBtn = document.getElementById("refreshClaimsBtn");
  dom.claimPolicyId = document.getElementById("claimPolicyId");
  dom.forceEligibleClaim = document.getElementById("forceEligibleClaim");
  dom.checkEligibilityBtn = document.getElementById("checkEligibilityBtn");
  dom.processClaimBtn = document.getElementById("processClaimBtn");
  dom.claimResult = document.getElementById("claimResult");

  dom.loadingOverlay = document.getElementById("loadingOverlay");
  dom.loadingText = document.getElementById("loadingText");
  dom.toastContainer = document.getElementById("toastContainer");

  dom.successModal = document.getElementById("successModal");
  dom.successModalDetails = document.getElementById("successModalDetails");
  dom.closeSuccessModalBtn = document.getElementById("closeSuccessModalBtn");
  dom.goDashboardBtn = document.getElementById("goDashboardBtn");

  dom.debugPanel = document.getElementById("debugPanel");
  dom.debugToggleBtn = document.getElementById("debugToggleBtn");
  dom.debugApiStatus = document.getElementById("debugApiStatus");
  dom.debugPolicyCount = document.getElementById("debugPolicyCount");
  dom.debugLastCall = document.getElementById("debugLastCall");
  dom.debugLastResponse = document.getElementById("debugLastResponse");
}

async function initializeApp() {
  console.log("[init] CropInsure frontend starting");
  cacheDom();
  bindEvents();
  setupErrorBoundaries();
  updateCoverage();
  detectMetaMask();
  await performHealthCheck();
  await loadStats();
  await refreshPolicies();
  await refreshClaims();
  updateDebugPanel();
  console.log("[init] CropInsure frontend ready");
}

function bindEvents() {
  dom.navLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const section = link.dataset.section;
      if (!section) {
        return;
      }

      if ((section === "dashboard" || section === "claims") && !hasPolicies()) {
        showToast(
          "Create at least one policy to unlock this section.",
          "warning",
        );
        return;
      }

      showSection(section);
    });
  });

  dom.retryHealthBtn.addEventListener("click", async () => {
    await performHealthCheck();
  });

  dom.connectWallet.addEventListener("click", connectWallet);
  dom.autoFillWalletBtn.addEventListener("click", autoFillWallet);
  dom.skipWalletBtn.addEventListener("click", skipWallet);

  dom.getStartedBtn.addEventListener("click", () => showSection("register"));
  dom.homeRefreshBtn.addEventListener("click", async () => {
    await performHealthCheck();
    await loadStats();
    await refreshPolicies();
  });

  // Submit listener is bound earlier in DOMContentLoaded for reliability.
  dom.getLocationBtn.addEventListener("click", getCurrentLocation);
  dom.previewWeatherBtn.addEventListener("click", previewWeather);
  dom.loadDemoBtn.addEventListener("click", loadDemoData);
  dom.premiumAmount.addEventListener("input", updateCoverage);

  dom.policySelect.addEventListener("change", async () => {
    state.selectedPolicyId = dom.policySelect.value;
    if (state.selectedPolicyId) {
      await loadPolicyDashboard(state.selectedPolicyId);
    }
  });

  dom.refreshPoliciesBtn.addEventListener("click", async () => {
    await refreshPolicies({ showToastOnSuccess: true });
  });
  dom.emptyRefreshPoliciesBtn.addEventListener("click", async () => {
    await refreshPolicies({ showToastOnSuccess: true });
  });

  dom.refreshClaimsBtn.addEventListener("click", refreshClaims);
  dom.checkEligibilityBtn.addEventListener("click", checkClaimEligibility);
  dom.processClaimBtn.addEventListener("click", () => processClaim());

  dom.closeSuccessModalBtn.addEventListener("click", () =>
    toggleSuccessModal(false),
  );
  dom.goDashboardBtn.addEventListener("click", async () => {
    toggleSuccessModal(false);
    await refreshPolicies();
    showSection("dashboard");
  });

  dom.debugToggleBtn.addEventListener("click", () => {
    dom.debugPanel.classList.toggle("debug-collapsed");
  });

  document.addEventListener("click", async (event) => {
    const actionTarget = event.target.closest("[data-action]");
    if (!actionTarget) {
      return;
    }

    const action = actionTarget.dataset.action;
    if (action === "go-register") {
      showSection("register");
      return;
    }

    if (action === "pay-premium") {
      const policyId = actionTarget.dataset.policy;
      if (policyId) {
        await payPremium(policyId);
      }
      return;
    }

    if (action === "process-claim") {
      const policyId = actionTarget.dataset.policy;
      await processClaim(policyId);
      return;
    }

    if (action === "retry-dashboard") {
      const policyId = actionTarget.dataset.policy || state.selectedPolicyId;
      if (policyId) {
        await loadPolicyDashboard(policyId);
      }
    }
  });
}

function setupErrorBoundaries() {
  window.addEventListener("error", (event) => {
    console.error("[global-error]", event.error || event.message);
    showToast(
      "Unexpected error occurred. Check debug panel for details.",
      "error",
    );
  });

  window.addEventListener("unhandledrejection", (event) => {
    console.error("[unhandled-rejection]", event.reason);
    showToast("Unexpected async error occurred.", "error");
  });
}

function showSection(sectionId) {
  document.querySelectorAll(".section").forEach((section) => {
    section.classList.remove("active");
  });

  const target = document.getElementById(sectionId);
  if (target) {
    target.classList.add("active");
  }

  dom.navLinks.forEach((link) => {
    link.classList.toggle("active", link.dataset.section === sectionId);
  });
}

function hasPolicies() {
  return state.policies.length > 0;
}

function updateProtectedNavigation() {
  const enabled = hasPolicies();
  [dom.navDashboard, dom.navClaims].forEach((navLink) => {
    navLink.classList.toggle("nav-disabled", !enabled);
    navLink.setAttribute("aria-disabled", String(!enabled));
  });
}

function detectMetaMask() {
  const hasMetaMask = isMetaMaskAvailable();
  if (hasMetaMask) {
    dom.metamaskStatus.textContent =
      "MetaMask detected. You can connect and auto-fill wallet address.";
    dom.connectWallet.disabled = false;
  } else {
    dom.metamaskStatus.textContent =
      "MetaMask not detected. You can skip and continue with manual wallet entry.";
    dom.connectWallet.disabled = true;
    dom.connectWallet.title = "MetaMask not available";
  }
}

function isMetaMaskAvailable() {
  const ethereum = window.ethereum;
  if (!ethereum) {
    return false;
  }

  if (ethereum.isMetaMask) {
    return true;
  }

  if (Array.isArray(ethereum.providers)) {
    return ethereum.providers.some((provider) => provider?.isMetaMask);
  }

  return false;
}

async function connectWallet() {
  if (!isMetaMaskAvailable()) {
    showToast(
      "MetaMask is not available. You can use Skip Wallet and continue.",
      "warning",
    );
    return;
  }

  try {
    dom.connectWallet.disabled = true;
    dom.walletBtnText.textContent = "Connecting...";
    const accounts = await window.ethereum.request({
      method: "eth_requestAccounts",
    });
    const wallet = accounts?.[0];

    if (!wallet) {
      throw new Error("No wallet account returned.");
    }

    state.currentWallet = wallet;
    state.walletMode = "connected";
    dom.autoFillWalletBtn.disabled = false;
    dom.connectWallet.classList.add("connected");
    dom.walletBtnText.textContent = formatAddress(wallet);
    dom.walletAddress.value = wallet;
    dom.metamaskStatus.textContent = "Wallet connected. Address auto-filled.";
    showToast("Wallet connected successfully.", "success");
  } catch (error) {
    console.error("[wallet] connection failed:", error);
    showToast(
      "Wallet connection failed. You can continue without it.",
      "error",
    );
  } finally {
    dom.connectWallet.disabled = false;
    dom.walletBtnText.textContent = state.currentWallet
      ? formatAddress(state.currentWallet)
      : "Connect Wallet";
  }
}

function autoFillWallet() {
  if (!state.currentWallet) {
    showToast("No connected wallet found. Connect wallet first.", "warning");
    return;
  }

  dom.walletAddress.value = state.currentWallet;
  state.walletMode = "connected";
  showToast("Wallet address auto-filled.", "info");
}

function skipWallet() {
  state.walletMode = "skipped";
  dom.walletAddress.value = dom.walletAddress.value.trim();
  dom.metamaskStatus.textContent =
    "Wallet skipped. You can keep wallet blank or enter one manually.";
  showToast("Wallet step skipped.", "info");
}

function formatAddress(address) {
  if (!address || address.length < 10) {
    return address || "Wallet";
  }
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function getCurrentLocation() {
  if (!navigator.geolocation) {
    showToast("Geolocation is not supported by this browser.", "error");
    return;
  }

  showLoading("Getting your location...");
  navigator.geolocation.getCurrentPosition(
    (position) => {
      document.getElementById("latitude").value =
        position.coords.latitude.toFixed(4);
      document.getElementById("longitude").value =
        position.coords.longitude.toFixed(4);
      hideLoading();
      showToast("Location captured.", "success");
    },
    (error) => {
      hideLoading();
      console.error("[location] failed:", error);
      showToast(
        "Unable to get location. Please enter coordinates manually.",
        "warning",
      );
    },
  );
}

function loadDemoData() {
  document.getElementById("farmerName").value = "Rajesh Kumar";
  document.getElementById("farmerPhone").value = "+91 9876543210";
  document.getElementById("farmerEmail").value = "rajesh@example.com";
  document.getElementById("walletAddress").value =
    "0x742d35Cc6634C0532925a3b844Bc9e7595f8bE0E";
  document.getElementById("latitude").value = "26.8467";
  document.getElementById("longitude").value = "80.9462";
  document.getElementById("cropType").value = "wheat";
  document.getElementById("sowingDate").value = "2025-01-15";
  document.getElementById("farmArea").value = "5";
  document.getElementById("expectedYield").value = "25";
  document.getElementById("premiumAmount").value = "5000";
  updateCoverage();
  clearFormErrors();
  showToast("Demo data loaded.", "info");
}

function updateCoverage() {
  const premium = Number(dom.premiumAmount.value || 0);
  dom.coverageAmount.value = premium > 0 ? premium * 10 : "";
}

function getFormData() {
  return {
    name: document.getElementById("farmerName").value.trim(),
    phone: document.getElementById("farmerPhone").value.trim(),
    email: document.getElementById("farmerEmail").value.trim(),
    walletAddress: document.getElementById("walletAddress").value.trim(),
    latitude: Number(document.getElementById("latitude").value),
    longitude: Number(document.getElementById("longitude").value),
    cropType: document.getElementById("cropType").value,
    sowingDate: document.getElementById("sowingDate").value,
    farmArea: Number(document.getElementById("farmArea").value),
    expectedYield: Number(document.getElementById("expectedYield").value),
    premiumAmount: Number(document.getElementById("premiumAmount").value),
  };
}

function validateForm(formData) {
  const errors = [];
  clearInputErrors();

  if (!formData.name) {
    errors.push("Name is required.");
    markInputError("farmerName");
  }

  if (!/^\+?[0-9\s-]{10,15}$/.test(formData.phone)) {
    errors.push("Phone number must be valid (10-15 digits).");
    markInputError("farmerPhone");
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
    errors.push("Email address must be valid.");
    markInputError("farmerEmail");
  }

  if (
    formData.walletAddress &&
    !/^0x[a-fA-F0-9]{40}$/.test(formData.walletAddress)
  ) {
    errors.push("Wallet address must be a valid 42 character hex address.");
    markInputError("walletAddress");
  }

  if (!Number.isFinite(formData.latitude)) {
    errors.push("Latitude is required.");
    markInputError("latitude");
  }

  if (!Number.isFinite(formData.longitude)) {
    errors.push("Longitude is required.");
    markInputError("longitude");
  }

  if (!formData.cropType) {
    errors.push("Crop type is required.");
    markInputError("cropType");
  }

  if (!formData.sowingDate) {
    errors.push("Sowing date is required.");
    markInputError("sowingDate");
  }

  if (!Number.isFinite(formData.farmArea) || formData.farmArea <= 0) {
    errors.push("Farm area must be greater than 0.");
    markInputError("farmArea");
  }

  if (!Number.isFinite(formData.expectedYield) || formData.expectedYield <= 0) {
    errors.push("Expected yield must be greater than 0.");
    markInputError("expectedYield");
  }

  if (
    !Number.isFinite(formData.premiumAmount) ||
    formData.premiumAmount < 1000
  ) {
    errors.push("Premium must be at least INR 1000.");
    markInputError("premiumAmount");
  }

  return errors;
}

function markInputError(inputId) {
  const input = document.getElementById(inputId);
  if (input) {
    input.classList.add("input-error");
  }
}

function clearInputErrors() {
  dom.registrationForm
    .querySelectorAll(".input-error")
    .forEach((el) => el.classList.remove("input-error"));
}

function showFormErrors(errors) {
  if (!errors.length) {
    clearFormErrors();
    return;
  }

  dom.formErrors.innerHTML = `<ul>${errors.map((error) => `<li>${error}</li>`).join("")}</ul>`;
  dom.formErrors.classList.remove("hidden");
}

function clearFormErrors() {
  dom.formErrors.classList.add("hidden");
  dom.formErrors.innerHTML = "";
}

async function handleRegistration(event) {
  event.preventDefault();
  event.stopPropagation();

  console.log("[register] submit triggered");

  if (state.isSubmittingPolicy) {
    console.log("[register] blocked duplicate submission");
    return;
  }

  state.isSubmittingPolicy = true;
  clearFormErrors();

  const formData = getFormData();
  const errors = validateForm(formData);
  if (errors.length) {
    showFormErrors(errors);
    showToast("Please fix highlighted form errors.", "warning");
    state.isSubmittingPolicy = false;
    return;
  }

  if (!(await ensureBackendConnection())) {
    showToast(
      "Backend not connected. Please start backend and retry.",
      "error",
    );
    state.isSubmittingPolicy = false;
    return;
  }

  setButtonLoading(dom.createPolicyBtn, true, "Creating Policy...");
  console.log("[register] Creating farmer and policy", formData);

  try {
    const farmerPayload = {
      name: formData.name,
      phone: formData.phone,
      email: formData.email,
      wallet_address: formData.walletAddress || null,
    };

    const farmerResult = await apiCall("/farmers", {
      method: "POST",
      body: JSON.stringify(farmerPayload),
    });

    const policyPayload = {
      farmer_id: farmerResult.farmer.id,
      latitude: formData.latitude,
      longitude: formData.longitude,
      crop_type: formData.cropType,
      sowing_date: formData.sowingDate,
      expected_yield: formData.expectedYield,
      farm_area_acres: formData.farmArea,
      premium_amount: formData.premiumAmount,
      coverage_amount: formData.premiumAmount * 10,
    };

    const policyResult = await apiCall("/policies", {
      method: "POST",
      body: JSON.stringify(policyPayload),
    });

    console.log("[register] Policy created:", policyResult);
    showToast(
      `Policy ${policyResult.policy.policy_id} created successfully.`,
      "success",
    );

    await refreshPolicies();
    await refreshClaims();
    await loadStats();

    dom.registrationForm.reset();
    updateCoverage();
    showSuccessModal(policyResult.policy);
  } catch (error) {
    console.error("[register] failed:", error);
    showToast(getFriendlyMessage(error), "error");
  } finally {
    setButtonLoading(dom.createPolicyBtn, false, "Create Policy");
    state.isSubmittingPolicy = false;
  }
}

async function previewWeather() {
  const latitude = Number(document.getElementById("latitude").value);
  const longitude = Number(document.getElementById("longitude").value);

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    showToast("Enter valid latitude and longitude first.", "warning");
    return;
  }

  try {
    const data = await apiCall(`/weather/risk/${latitude}/${longitude}`);
    dom.weatherPreviewContent.innerHTML = `
            <div class="weather-data">
                <div class="weather-item">
                    <div class="label">Temperature</div>
                    <div class="value">${data.current_conditions?.temperature ?? "--"} C</div>
                </div>
                <div class="weather-item">
                    <div class="label">Humidity</div>
                    <div class="value">${data.current_conditions?.humidity ?? "--"}%</div>
                </div>
                <div class="weather-item">
                    <div class="label">Wind Speed</div>
                    <div class="value">${Number(data.current_conditions?.wind_speed || 0).toFixed(1)} km/h</div>
                </div>
                <div class="weather-item">
                    <div class="label">Risk Level</div>
                    <div class="value">${data.risk_level || "Unknown"}</div>
                </div>
            </div>
        `;
    dom.weatherPreview.classList.remove("hidden");
  } catch (error) {
    console.error("[weather-preview] failed:", error);
    showToast("Unable to fetch weather preview. Try again.", "error");
  }
}

async function loadStats() {
  try {
    const [policiesData, claimsData] = await Promise.all([
      apiCall("/policies", {}, { showErrorToast: false }),
      apiCall("/claims", {}, { showErrorToast: false }),
    ]);

    const totalPolicies = Number(policiesData.count || 0);
    const totalClaims = Number(claimsData.count || 0);
    const totalPayout = (claimsData.claims || []).reduce(
      (sum, claim) => sum + Number(claim.payout_amount || 0),
      0,
    );

    dom.totalPolicies.textContent = totalPolicies;
    dom.totalClaims.textContent = totalClaims;
    dom.totalPayout.textContent = `INR ${totalPayout.toLocaleString()}`;
  } catch (error) {
    console.error("[stats] failed:", error);
    dom.totalPolicies.textContent = "0";
    dom.totalClaims.textContent = "0";
    dom.totalPayout.textContent = "INR 0";
  }
}

async function refreshPolicies(options = {}) {
  const { showToastOnSuccess = false } = options;

  try {
    const data = await apiCall("/policies", {}, { showErrorToast: false });
    state.policies = data.policies || [];
    dom.debugPolicyCount.textContent = String(state.policies.length);

    dom.policySelect.innerHTML =
      '<option value="">-- Select a Policy --</option>';
    state.policies.forEach((policy) => {
      const option = document.createElement("option");
      option.value = policy.policy_id;
      option.textContent = `${policy.policy_id} | ${policy.crop_type} | ${policy.is_active ? "Active" : "Inactive"}`;
      dom.policySelect.appendChild(option);
    });

    dom.policyEmptyState.classList.toggle("hidden", state.policies.length > 0);
    updateProtectedNavigation();
    updateDebugPanel();

    if (showToastOnSuccess) {
      showToast("Policies refreshed.", "success");
    }

    if (
      state.selectedPolicyId &&
      state.policies.some(
        (policy) => policy.policy_id === state.selectedPolicyId,
      )
    ) {
      dom.policySelect.value = state.selectedPolicyId;
    } else {
      state.selectedPolicyId = "";
    }
  } catch (error) {
    console.error("[policies] failed:", error);
    state.policies = [];
    dom.policySelect.innerHTML =
      '<option value="">-- Select a Policy --</option>';
    dom.policyEmptyState.classList.remove("hidden");
    updateProtectedNavigation();
    showToast("Failed to load policies. Please retry.", "error");
  }
}

async function loadPolicyDashboard(policyId) {
  if (!policyId) {
    return;
  }

  console.log("[dashboard] loading policy", policyId);
  showLoading("Loading dashboard...");

  try {
    const policyData = await apiCall(`/policies/${policyId}`);
    const policy = policyData.policy;

    const weatherData = await apiCall(
      `/weather/risk/${policy.farm.latitude}/${policy.farm.longitude}`,
    );
    const ndviData = await apiCall(
      `/ndvi/health/${policy.farm.latitude}/${policy.farm.longitude}?crop=${encodeURIComponent(policy.farm.crop_type || "")}`,
    );
    const claimData = await apiCall(
      `/claims/check/${policyId}`,
      {},
      { allowBusinessError: true, showErrorToast: false },
    );

    let predictionData = { success: false };
    if (weatherData.success) {
      predictionData = await apiCall(
        "/predict/risk",
        {
          method: "POST",
          body: JSON.stringify({
            rainfall_annual:
              weatherData.rainfall_analysis?.estimated_annual_mm || 1000,
            temperature: weatherData.current_conditions?.temperature || 25,
            humidity: weatherData.current_conditions?.humidity || 70,
            wind_speed: weatherData.current_conditions?.wind_speed || 10,
          }),
        },
        { showErrorToast: false, allowBusinessError: true },
      );
    }

    updatePolicyInfo(policy);
    updateWeatherCard(weatherData);
    updateNDVICard(ndviData);
    updatePredictionCard(predictionData);
    updateClaimEligibility(claimData);
    if (Array.isArray(ndviData.time_series)) {
      updateNDVIChart(ndviData.time_series);
    }

    dom.claimPolicyId.value = policyId;
  } catch (error) {
    console.error("[dashboard] failed:", error);
    const message = getFriendlyMessage(error);
    dom.policyInfoContent.innerHTML = `
            <div class="empty-state">
                <p>${message}</p>
                <button class="btn btn-secondary btn-sm" data-action="retry-dashboard" data-policy="${policyId}">Retry</button>
            </div>
        `;
    showToast(message, "error");
  } finally {
    hideLoading();
  }
}

function updatePolicyInfo(policy) {
  const isActive = Boolean(policy.status?.is_active);
  dom.policyStatus.textContent = isActive ? "Active" : "Inactive";
  dom.policyStatus.className = `status-badge ${isActive ? "active" : "inactive"}`;

  dom.policyInfoContent.innerHTML = `
        <div>
            <p><strong>Policy ID:</strong> ${policy.policy_id}</p>
            <p><strong>Farmer:</strong> ${policy.farmer?.name || "-"}</p>
            <p><strong>Crop:</strong> ${policy.farm?.crop_type || "-"}</p>
            <p><strong>Location:</strong> ${policy.farm?.latitude}, ${policy.farm?.longitude}</p>
            <p><strong>Premium:</strong> INR ${Number(policy.insurance?.premium || 0).toLocaleString()}</p>
            <p><strong>Coverage:</strong> INR ${Number(policy.insurance?.coverage || 0).toLocaleString()}</p>
            <p><strong>Premium Paid:</strong> ${policy.insurance?.premium_paid ? "Yes" : "No"}</p>
        </div>
        ${!policy.insurance?.premium_paid ? `<button class="btn btn-success btn-sm" data-action="pay-premium" data-policy="${policy.policy_id}">Pay Premium</button>` : ""}
    `;
}

function updateWeatherCard(data) {
  const triggered = Boolean(data.weather_trigger);
  dom.weatherTrigger.textContent = triggered ? "TRIGGER" : "Normal";
  dom.weatherTrigger.className = `trigger-badge ${triggered ? "true" : "false"}`;

  if (!data.success) {
    dom.weatherContent.innerHTML =
      '<p class="empty-state">Weather data unavailable.</p>';
    return;
  }

  dom.weatherContent.innerHTML = `
        <div class="weather-data">
            <div class="weather-item"><div class="label">Temperature</div><div class="value">${data.current_conditions?.temperature ?? "--"} C</div></div>
            <div class="weather-item"><div class="label">Humidity</div><div class="value">${data.current_conditions?.humidity ?? "--"}%</div></div>
            <div class="weather-item"><div class="label">Wind Speed</div><div class="value">${Number(data.current_conditions?.wind_speed || 0).toFixed(1)} km/h</div></div>
            <div class="weather-item"><div class="label">Risk Level</div><div class="value">${data.risk_level || "Unknown"}</div></div>
        </div>
    `;
}

function updateNDVICard(data) {
  const triggered = Boolean(data.ndvi_trigger);
  dom.ndviTrigger.textContent = triggered ? "TRIGGER" : "Normal";
  dom.ndviTrigger.className = `trigger-badge ${triggered ? "true" : "false"}`;

  if (!data.success) {
    dom.ndviContent.innerHTML =
      '<p class="empty-state">NDVI data unavailable.</p>';
    return;
  }

  const healthText = String(data.health_status || "Unknown");
  let healthClass = "severe";
  if (healthText.toLowerCase().includes("healthy")) {
    healthClass = "healthy";
  } else if (healthText.toLowerCase().includes("moderate")) {
    healthClass = "moderate";
  }

  dom.ndviContent.innerHTML = `
        <div class="ndvi-gauge">
            <div class="gauge-value">${Number(data.current_ndvi || 0).toFixed(2)}</div>
            <div>Expected: ${Number(data.expected_ndvi || 0).toFixed(2)}</div>
            <div>Drop: ${Number(data.ndvi_drop_percent || 0).toFixed(1)}%</div>
            <div class="health-status ${healthClass}">${healthText}</div>
        </div>
    `;
}

function updatePredictionCard(data) {
  if (!data.success || !data.prediction) {
    dom.predictionContent.innerHTML =
      '<p class="empty-state">Risk prediction unavailable.</p>';
    return;
  }

  const prediction = data.prediction;
  const confidence = Number(prediction.confidence || 0) * 100;
  const probabilities = prediction.probabilities || {};

  dom.predictionContent.innerHTML = `
        <p><strong>${prediction.risk_category || "Unknown"}</strong></p>
        <p>Confidence: ${confidence.toFixed(1)}%</p>
        <p>${Object.entries(probabilities)
          .map(([key, value]) => `${key}: ${(Number(value) * 100).toFixed(0)}%`)
          .join(" | ")}</p>
    `;
}

function updateClaimEligibility(data) {
  if (!data.success) {
    dom.claimEligibility.innerHTML = `
            <div class="empty-state">
                <p>${data.error || "Claim eligibility unavailable."}</p>
            </div>
        `;
    return;
  }

  const eligible = Boolean(data.double_verification?.claim_eligible);
  dom.claimEligibility.innerHTML = `
        <div>
            <p><strong>${eligible ? "Eligible for claim" : "Not eligible"}</strong></p>
            <p>Weather Trigger: ${data.double_verification?.weather_trigger ? "Yes" : "No"}</p>
            <p>NDVI Trigger: ${data.double_verification?.ndvi_trigger ? "Yes" : "No"}</p>
            <p>Payout: INR ${Number(data.payout?.amount || 0).toLocaleString()}</p>
            ${eligible ? `<button class="btn btn-success btn-sm" data-action="process-claim" data-policy="${data.policy_id}">Process Claim</button>` : ""}
        </div>
    `;
}

function updateNDVIChart(timeSeries) {
  const canvas = document.getElementById("ndviChart");
  if (!canvas || typeof Chart === "undefined") {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (state.ndviChart) {
    state.ndviChart.destroy();
  }

  const labels = timeSeries.map((point) => point.date);
  const values = timeSeries.map((point) => Number(point.ndvi || 0));

  state.ndviChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "NDVI",
          data: values,
          borderColor: "#16a34a",
          backgroundColor: "rgba(22, 163, 74, 0.14)",
          tension: 0.3,
          fill: true,
        },
        {
          label: "Stress Threshold",
          data: new Array(labels.length).fill(0.35),
          borderColor: "#dc2626",
          borderDash: [6, 4],
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" },
      },
      scales: {
        y: {
          min: 0,
          max: 1,
        },
      },
    },
  });
}

async function refreshClaims() {
  try {
    const data = await apiCall("/claims", {}, { showErrorToast: false });
    const claims = data.claims || [];

    if (!claims.length) {
      dom.claimsTableBody.innerHTML =
        '<tr><td colspan="7" class="empty-state">No claims found.</td></tr>';
      return;
    }

    dom.claimsTableBody.innerHTML = claims
      .map(
        (claim) => `
            <tr>
                <td>${claim.claim_id}</td>
                <td>${claim.policy_id}</td>
                <td><span class="status-badge ${claim.status === "APPROVED" ? "active" : "inactive"}">${claim.status}</span></td>
                <td>${claim.weather_trigger ? "Yes" : "No"}</td>
                <td>${claim.ndvi_trigger ? "Yes" : "No"}</td>
                <td>INR ${Number(claim.payout_amount || 0).toLocaleString()}</td>
                <td>${claim.created_at ? new Date(claim.created_at).toLocaleDateString() : "-"}</td>
            </tr>
        `,
      )
      .join("");
  } catch (error) {
    console.error("[claims] failed:", error);
    dom.claimsTableBody.innerHTML =
      '<tr><td colspan="7" class="empty-state">Failed to load claims. Retry.</td></tr>';
    showToast("Unable to load claims. Please retry.", "error");
  }
}

async function checkClaimEligibility() {
  const policyId = (dom.claimPolicyId.value || "").trim();
  if (!policyId) {
    showToast("Enter policy ID first.", "warning");
    return;
  }

  const forceEligible = Boolean(dom.forceEligibleClaim?.checked);
  const endpoint = forceEligible
    ? `/claims/check/${policyId}?force_eligible=true`
    : `/claims/check/${policyId}`;

  try {
    const data = await apiCall(
      endpoint,
      {},
      { allowBusinessError: true, showErrorToast: false },
    );
    dom.claimResult.classList.remove("hidden", "approved", "rejected");

    if (data.success) {
      const eligible = Boolean(data.double_verification?.claim_eligible);
      dom.claimResult.classList.add(eligible ? "approved" : "rejected");
      dom.claimResult.innerHTML = `
                <p><strong>${eligible ? "Claim Eligible" : "Claim Not Eligible"}</strong></p>
                <p>Policy: ${data.policy_id}</p>
                <p>Farmer: ${data.farmer_name}</p>
                <p>Payout: INR ${Number(data.payout?.amount || 0).toLocaleString()}</p>
                ${data.test_mode?.override_applied ? "<p><small>Test mode override applied.</small></p>" : ""}
            `;
    } else {
      dom.claimResult.classList.add("rejected");
      dom.claimResult.innerHTML = `<p>${data.error || "Eligibility check failed."}</p>`;
    }
  } catch (error) {
    console.error("[claim-check] failed:", error);
    showToast(getFriendlyMessage(error), "error");
  }
}

async function processClaim(policyId) {
  const resolvedPolicyId = (policyId || dom.claimPolicyId.value || "").trim();
  if (!resolvedPolicyId) {
    showToast("Enter policy ID first.", "warning");
    return;
  }

  const forceEligible = Boolean(dom.forceEligibleClaim?.checked);

  try {
    const data = await apiCall(
      `/claims/process/${resolvedPolicyId}`,
      {
        method: "POST",
        body: JSON.stringify({ force_eligible: forceEligible }),
      },
      { allowBusinessError: true },
    );
    if (!data.success) {
      showToast(data.error || "Claim processing failed.", "error");
      return;
    }

    if (data.status === "APPROVED") {
      showToast(
        `Claim approved. Payout INR ${Number(data.payout?.amount || 0).toLocaleString()}.`,
        "success",
      );
    } else {
      showToast(`Claim rejected: ${data.reason || "Not eligible"}`, "warning");
    }

    await refreshClaims();
    await loadStats();
    if (state.selectedPolicyId) {
      await loadPolicyDashboard(state.selectedPolicyId);
    }
  } catch (error) {
    console.error("[claim-process] failed:", error);
    showToast(getFriendlyMessage(error), "error");
  }
}

async function payPremium(policyId) {
  try {
    const data = await apiCall(`/policies/${policyId}/pay-premium`, {
      method: "POST",
    });
    if (!data.success) {
      showToast(data.error || "Premium payment failed.", "error");
      return;
    }

    showToast("Premium paid successfully.", "success");
    await refreshPolicies();
    await loadStats();
    if (state.selectedPolicyId) {
      await loadPolicyDashboard(state.selectedPolicyId);
    }
  } catch (error) {
    console.error("[premium] failed:", error);
    showToast(getFriendlyMessage(error), "error");
  }
}

function showSuccessModal(policy) {
  dom.successModalDetails.innerHTML = `
        <p><strong>Policy ID:</strong> ${policy.policy_id}</p>
        <p><strong>Farmer:</strong> ${policy.farmer_name || "-"}</p>
        <p><strong>Crop:</strong> ${policy.crop_type || "-"}</p>
        <p><strong>Premium:</strong> INR ${Number(policy.premium || 0).toLocaleString()}</p>
        <p><strong>Coverage:</strong> INR ${Number(policy.coverage || 0).toLocaleString()}</p>
    `;
  toggleSuccessModal(true);
}

function toggleSuccessModal(show) {
  dom.successModal.classList.toggle("hidden", !show);
}

async function ensureBackendConnection() {
  if (state.backendConnected) {
    return true;
  }

  return performHealthCheck();
}

async function performHealthCheck() {
  const endpoint = `${API_BASE}/health`;
  console.log("[health] Checking backend connection:", endpoint);

  try {
    const response = await fetch(endpoint, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    const data = await response.json();
    const healthy = response.ok && data.status === "healthy";
    setBackendStatus(healthy);

    state.lastApiCall = { endpoint: "/health", method: "GET" };
    state.lastApiResponse = data;
    updateDebugPanel();

    if (!healthy) {
      console.warn("[health] backend unhealthy", data);
    }
    return healthy;
  } catch (error) {
    console.error("[health] failed:", error);
    setBackendStatus(false);
    state.lastApiCall = { endpoint: "/health", method: "GET" };
    state.lastApiResponse = { error: String(error.message || error) };
    updateDebugPanel();
    return false;
  }
}

function setBackendStatus(connected) {
  state.backendConnected = connected;
  dom.backendStatus.classList.toggle("connected", connected);
  dom.backendStatus.classList.toggle("disconnected", !connected);
  dom.backendStatusText.textContent = connected
    ? "Backend connected"
    : "Backend not connected";
  dom.backendBanner.classList.toggle("hidden", connected);
}

async function apiCall(endpoint, options = {}, config = {}) {
  const {
    showLoader = true,
    showErrorToast = true,
    allowBusinessError = false,
  } = config;

  if (endpoint !== "/health" && !(await ensureBackendConnection())) {
    throw new Error("Backend not connected. Please start backend and retry.");
  }

  const method = options.method || "GET";
  const url = `${API_BASE}${endpoint}`;

  state.lastApiCall = {
    method,
    endpoint,
    body: options.body ? safeJsonParse(options.body) : null,
  };
  updateDebugPanel();

  console.log(`[api] ${method} ${url}`);

  if (showLoader) {
    showLoading("Processing request...");
  }

  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    const data = await response.json().catch(() => ({}));
    console.log("[api] response", endpoint, data);
    state.lastApiResponse = data;
    updateDebugPanel();

    if (!response.ok) {
      throw new Error(data.error || data.message || "Request failed.");
    }

    if (!allowBusinessError && data.success === false) {
      throw new Error(data.error || "Request could not be completed.");
    }

    return data;
  } catch (error) {
    console.error(`[api] ${endpoint} failed`, error);
    if (showErrorToast) {
      showToast(getFriendlyMessage(error), "error");
    }
    throw error;
  } finally {
    if (showLoader) {
      hideLoading();
    }
  }
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch (error) {
    return text;
  }
}

function getFriendlyMessage(error) {
  const message = (error && error.message) || "";
  if (message.includes("Failed to fetch") || message.includes("NetworkError")) {
    return "Cannot reach backend. Please ensure backend is running on port 5001.";
  }
  if (message.includes("Backend not connected")) {
    return message;
  }
  return message || "Something went wrong. Please try again.";
}

function showToast(message, type = "info") {
  const iconByType = {
    success: "fa-circle-check",
    error: "fa-circle-xmark",
    warning: "fa-triangle-exclamation",
    info: "fa-circle-info",
  };

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<i class="fas ${iconByType[type] || iconByType.info}"></i><span>${message}</span>`;
  dom.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 4500);
}

function showLoading(text = "Loading...") {
  state.loadingCount += 1;
  dom.loadingText.textContent = text;
  dom.loadingOverlay.classList.remove("hidden");
}

function hideLoading() {
  state.loadingCount = Math.max(0, state.loadingCount - 1);
  if (state.loadingCount === 0) {
    dom.loadingOverlay.classList.add("hidden");
  }
}

function setButtonLoading(button, isLoading, loadingText) {
  if (!button) {
    return;
  }

  if (!button.dataset.defaultHtml) {
    button.dataset.defaultHtml = button.innerHTML;
  }

  button.disabled = isLoading;
  button.innerHTML = isLoading
    ? `<i class="fas fa-spinner fa-spin"></i> ${loadingText}`
    : button.dataset.defaultHtml;
}

function updateDebugPanel() {
  dom.debugApiStatus.textContent = state.backendConnected
    ? "Connected"
    : "Disconnected";
  dom.debugApiStatus.className = `debug-pill ${state.backendConnected ? "on" : "off"}`;
  dom.debugPolicyCount.textContent = String(state.policies.length);
  dom.debugLastCall.textContent = state.lastApiCall
    ? JSON.stringify(state.lastApiCall, null, 2)
    : "-";
  dom.debugLastResponse.textContent = state.lastApiResponse
    ? JSON.stringify(state.lastApiResponse, null, 2)
    : "-";
}
