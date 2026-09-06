let currentPresets = {};
let latestValidationResult = null;

const STAGE_KEYS = [
  { id: "syntax", name: "1. Syntax" },
  { id: "schema", name: "2. Schema" },
  { id: "constraints", name: "3. Bounds" },
  { id: "semantic", name: "4. Semantic" },
  { id: "cross_field", name: "5. Cross" },
  { id: "safety", name: "6. Safety" },
  { id: "k6_compatibility", name: "7. k6 Compat" },
  { id: "compilation", name: "8. Compile" }
];

document.addEventListener("DOMContentLoaded", () => {
  initPresets();
  setupEventListeners();
});

async function initPresets() {
  try {
    const res = await fetch("/api/v1/presets");
    currentPresets = await res.json();
    const select = document.getElementById("preset-select");
    select.innerHTML = '<option value="">-- Select Preset Test Case --</option>';

    for (const key of Object.keys(currentPresets)) {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = formatPresetName(key);
      select.appendChild(opt);
    }

    // Default select valid_stress
    if (currentPresets["valid_stress"]) {
      select.value = "valid_stress";
      loadPreset("valid_stress");
    }
  } catch (err) {
    console.error("Failed to load presets:", err);
  }
}

function formatPresetName(key) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, c => c.toUpperCase());
}

function loadPreset(key) {
  if (!currentPresets[key]) return;
  const val = currentPresets[key];
  const jsonStr = typeof val === "string" ? val : JSON.stringify(val, null, 2);
  document.getElementById("json-input").value = jsonStr;
  runValidation();
}

function setupEventListeners() {
  document.getElementById("preset-select").addEventListener("change", (e) => {
    if (e.target.value) {
      loadPreset(e.target.value);
    }
  });

  document.getElementById("btn-validate").addEventListener("click", () => {
    runValidation();
  });

  document.getElementById("btn-format").addEventListener("click", () => {
    formatInputJson();
  });

  document.getElementById("btn-repair").addEventListener("click", () => {
    runAutoRepair();
  });

  document.getElementById("btn-copy-script").addEventListener("click", () => {
    const code = document.getElementById("script-output").textContent;
    navigator.clipboard.writeText(code);
    const btn = document.getElementById("btn-copy-script");
    const origText = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => btn.textContent = origText, 1500);
  });
}

function formatInputJson() {
  const textarea = document.getElementById("json-input");
  try {
    const parsed = JSON.parse(textarea.value);
    textarea.value = JSON.stringify(parsed, null, 2);
  } catch (e) {
    alert("Cannot format: JSON contains syntax errors.");
  }
}

async function runValidation() {
  const inputVal = document.getElementById("json-input").value;
  setRunningState();

  try {
    const res = await fetch("/api/v1/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ spec: inputVal, auto_compile: true })
    });

    const result = await res.json();
    latestValidationResult = result;
    renderResults(result);
  } catch (err) {
    console.error("Validation request failed:", err);
    alert("Validation API error: " + err.message);
  }
}

async function runAutoRepair() {
  const inputVal = document.getElementById("json-input").value;
  let parsedSpec = null;
  try {
    parsedSpec = JSON.parse(inputVal);
  } catch (e) {
    // If raw input is malformed, try to pass as raw or alert
    alert("Cannot auto-repair unparseable JSON directly. Please fix syntax errors first.");
    return;
  }

  try {
    const res = await fetch("/api/v1/repair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        spec: parsedSpec,
        errors: latestValidationResult ? latestValidationResult.errors : null
      })
    });

    const data = await res.json();
    if (data.applied_fixes && data.applied_fixes.length > 0) {
      document.getElementById("json-input").value = JSON.stringify(data.repaired_spec, null, 2);
      renderResults(data.revalidated_result);
      alert("Applied Automatic Repairs:\n\n• " + data.applied_fixes.join("\n• "));
    } else {
      alert("No automatic repairs were necessary or possible for the current errors.");
    }
  } catch (err) {
    console.error("Auto-repair failed:", err);
    alert("Repair failed: " + err.message);
  }
}

function setRunningState() {
  STAGE_KEYS.forEach(s => {
    const pill = document.getElementById(`stage-${s.id}`);
    if (pill) {
      pill.className = "stage-pill running";
    }
  });
}

function renderResults(result) {
  // 1. Update Stepper Pills
  STAGE_KEYS.forEach(s => {
    const pill = document.getElementById(`stage-${s.id}`);
    if (pill) {
      const status = (result.stages && result.stages[s.id]) || "SKIPPED";
      pill.className = "stage-pill " + status.toLowerCase();
    }
  });

  // 2. Status Banner
  const statusEl = document.getElementById("status-badge");
  const scoreEl = document.getElementById("score-val");
  statusEl.textContent = result.status;
  statusEl.className = "status-badge " + result.status.toLowerCase();
  scoreEl.textContent = result.validation_score + "/100";

  // 3. Diagnostics
  const diagList = document.getElementById("diagnostics-list");
  diagList.innerHTML = "";

  const allItems = [...(result.errors || []), ...(result.warnings || [])];

  if (allItems.length === 0) {
    diagList.innerHTML = `
      <div style="color: var(--accent-green); padding: 12px; background: rgba(63,185,80,0.1); border-radius: 6px; font-weight: 500;">
        All 8 Progressive Verification Gates passed successfully! Zero errors or policy violations detected.
      </div>
    `;
  } else {
    allItems.forEach(item => {
      const isWarn = item.severity === "WARNING" || item.severity === "INFO";
      const card = document.createElement("div");
      card.className = `error-card ${isWarn ? "warning" : ""}`;
      card.innerHTML = `
        <div class="error-header">
          <span class="error-code">${item.code} [${item.stage}]</span>
          <span class="error-path">${item.path}</span>
        </div>
        <div class="error-msg">${item.message}</div>
        ${item.expected ? `<div style="font-size:12px; color:var(--text-secondary); margin-bottom:4px;">Expected: <code style="color:var(--accent-green);">${item.expected}</code> | Received: <code style="color:var(--accent-red);">${item.received}</code></div>` : ""}
        ${item.repair_hint ? `<div class="error-hint">Fix: ${item.repair_hint}</div>` : ""}
      `;
      diagList.appendChild(card);
    });
  }

  // 4. Script Preview
  const scriptEl = document.getElementById("script-output");
  if (result.compiled_k6_script) {
    scriptEl.textContent = result.compiled_k6_script;
  } else {
    scriptEl.textContent = "// Compilation blocked: Fix validation errors above to compile valid k6 ES6 script.";
  }
}
