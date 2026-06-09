let lastIntake = null;

function normalizeEngagementId(raw) {
  return raw
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[-_.]+|[-_.]+$/g, "");
}

function optionLabel(option) {
  if (typeof option === "string") return option;
  return option.label || option.value;
}

function optionValue(option) {
  if (typeof option === "string") return option;
  return option.value;
}

function renderField(field) {
  const wrapper = document.createElement("div");
  wrapper.className = "intake-field";
  wrapper.dataset.fieldPath = field.field_path;

  const label = document.createElement("label");
  label.className = "field-label";
  label.innerHTML = `${field.label}${field.required ? " *" : ""}<span class="priority-badge priority-${field.priority}">${field.priority}</span>`;
  wrapper.appendChild(label);

  const question = document.createElement("p");
  question.className = "field-question";
  question.textContent = field.question;
  wrapper.appendChild(question);

  let input;
  const name = field.field_path;

  if (field.type === "select") {
    input = document.createElement("select");
    input.name = name;
    if (!field.required) {
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "— Select —";
      input.appendChild(blank);
    }
    for (const option of field.options || []) {
      const opt = document.createElement("option");
      opt.value = optionValue(option);
      opt.textContent = optionLabel(option);
      input.appendChild(opt);
    }
  } else if (field.type === "multiselect") {
    input = document.createElement("div");
    input.className = "multiselect-options";
    for (const option of field.options || []) {
      const value = optionValue(option);
      const row = document.createElement("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.name = name;
      cb.value = value;
      row.appendChild(cb);
      row.appendChild(document.createTextNode(optionLabel(option)));
      input.appendChild(row);
    }
  } else if (field.type === "number") {
    input = document.createElement("input");
    input.type = "number";
    input.name = name;
    if (field.min != null) input.min = String(field.min);
    if (field.placeholder) input.placeholder = field.placeholder;
  } else if (field.type === "text") {
    input = document.createElement("input");
    input.type = "text";
    input.name = name;
    if (field.placeholder) input.placeholder = field.placeholder;
  } else {
    input = document.createElement("textarea");
    input.name = name;
    input.placeholder = field.placeholder || "";
  }

  if (field.required && field.type !== "multiselect") {
    input.required = true;
  }

  wrapper.appendChild(input);

  if (field.help) {
    const help = document.createElement("p");
    help.className = "field-help";
    help.textContent = field.help;
    wrapper.appendChild(help);
  }

  return wrapper;
}

function collectAnswers(form) {
  const answers = {};
  const elements = form.querySelectorAll("[name]");
  const seen = new Set();

  for (const el of elements) {
    const name = el.name;
    if (seen.has(name) && el.type !== "checkbox") continue;

    if (el.type === "checkbox") {
      if (!answers[name]) answers[name] = [];
      if (el.checked) answers[name].push(el.value);
      seen.add(name);
      continue;
    }

    if (el.tagName === "SELECT" || el.type === "text" || el.type === "number" || el.tagName === "TEXTAREA") {
      answers[name] = el.value;
      seen.add(name);
    }
  }

  return answers;
}

async function loadFormSchema() {
  const industry = document.getElementById("industry-filter").value;
  const url = industry
    ? `/api/v1/intake-form/schema?industry=${encodeURIComponent(industry)}`
    : "/api/v1/intake-form/schema";
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to load form schema");
  return response.json();
}

function renderForm(schema) {
  const container = document.getElementById("form-sections");
  container.innerHTML = "";

  for (const section of schema.sections) {
    const details = document.createElement("details");
    details.className = "panel form-section";
    details.open = section.id === "org_profile";

    const summary = document.createElement("summary");
    summary.textContent = `${section.label} (${section.fields.length} questions)`;
    details.appendChild(summary);

    for (const field of section.fields) {
      details.appendChild(renderField(field));
    }

    container.appendChild(details);
  }

  document.getElementById("form-meta").textContent =
    `${schema.field_count} questions loaded${schema.industry ? ` for ${schema.industry}` : ""}.`;
  document.getElementById("client-intake-form").hidden = false;

  const industry = document.getElementById("industry-filter").value;
  if (industry) {
    const industryInput = document.querySelector('[name="industry"]');
    if (industryInput) industryInput.value = industry;
  }
}

document.getElementById("btn-load-form").addEventListener("click", async () => {
  try {
    const schema = await loadFormSchema();
    renderForm(schema);
  } catch (error) {
    alert(error.message || error);
  }
});

document.getElementById("client-intake-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const industry = document.getElementById("industry-filter").value || undefined;
  const answers = collectAnswers(form);

  if (answers.industry && typeof answers.industry === "string") {
    // keep industry from form field if present
  } else if (industry) {
    answers.industry = industry;
  }

  const response = await fetch("/api/v1/intake-form/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers, industry }),
  });
  const body = await response.json();
  if (!response.ok) {
    alert(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail, null, 2));
    return;
  }

  lastIntake = body.intake;
  document.getElementById("result-json").textContent = JSON.stringify(body.intake, null, 2);
  document.getElementById("result-panel").hidden = false;
  document.getElementById("btn-download").disabled = false;
  document.getElementById("btn-save-engagement").disabled = false;
  window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
});

document.getElementById("btn-download").addEventListener("click", () => {
  if (!lastIntake) return;
  const blob = new Blob([JSON.stringify(lastIntake, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${lastIntake.company_name || "client"}-intake.json`.replace(/[^\w.-]+/g, "-");
  link.click();
  URL.revokeObjectURL(url);
});

document.getElementById("btn-save-engagement").addEventListener("click", async () => {
  if (!lastIntake) return;
  const engagementId = normalizeEngagementId(document.getElementById("engagement-id").value);
  if (!engagementId) {
    alert("Enter an engagement ID to save.");
    return;
  }

  const industry = document.getElementById("industry-filter").value || lastIntake.industry;
  const answers = collectAnswers(document.getElementById("client-intake-form"));

  const response = await fetch(`/api/v1/intake-form/submit/${encodeURIComponent(engagementId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers, industry }),
  });
  const body = await response.json();
  if (!response.ok) {
    alert(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail, null, 2));
    return;
  }
  alert(body.message || "Saved.");
});

const params = new URLSearchParams(window.location.search);
if (params.get("industry")) {
  document.getElementById("industry-filter").value = params.get("industry");
}
if (params.get("engagement")) {
  document.getElementById("engagement-id").value = params.get("engagement");
}
