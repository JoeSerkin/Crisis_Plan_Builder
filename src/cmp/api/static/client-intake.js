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

function addHelp(wrapper, text) {
  if (!text) return;
  const help = document.createElement("p");
  help.className = "field-help";
  help.textContent = text;
  wrapper.appendChild(help);
}

function renderSelect(part, required) {
  const select = document.createElement("select");
  select.name = part.name;
  if (!required) {
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "— Select —";
    select.appendChild(blank);
  }
  for (const option of part.options || []) {
    const opt = document.createElement("option");
    opt.value = optionValue(option);
    opt.textContent = optionLabel(option);
    select.appendChild(opt);
  }
  if (required) select.required = true;
  return select;
}

function renderCountryMultiselect(part, required) {
  const wrapper = document.createElement("div");
  wrapper.className = "country-multiselect";
  const select = document.createElement("select");
  select.name = part.name;
  select.multiple = true;
  select.size = 8;
  for (const option of part.options || []) {
    const opt = document.createElement("option");
    opt.value = optionValue(option);
    opt.textContent = optionLabel(option);
    select.appendChild(opt);
  }
  wrapper.appendChild(select);
  const hint = document.createElement("p");
  hint.className = "field-hint";
  hint.textContent = "Hold Ctrl (Windows) or Cmd (Mac) to select multiple countries.";
  wrapper.appendChild(hint);
  if (required) select.required = true;
  return wrapper;
}

function renderChecklist(part) {
  const box = document.createElement("div");
  box.className = "checklist-options";
  for (const option of part.options || []) {
    const row = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.name = part.name;
    cb.value = optionValue(option);
    row.appendChild(cb);
    row.appendChild(document.createTextNode(optionLabel(option)));
    box.appendChild(row);
  }
  return box;
}

function renderFileInput(part) {
  const input = document.createElement("input");
  input.type = "file";
  input.name = part.name;
  if (part.accept) input.accept = part.accept;
  input.dataset.fileField = "true";
  return input;
}

function renderPart(part, required = false) {
  const block = document.createElement("div");
  block.className = "field-part";
  const partLabel = document.createElement("label");
  partLabel.className = "part-label";
  partLabel.textContent = part.label;
  block.appendChild(partLabel);

  let input;
  if (part.type === "select") {
    input = renderSelect(part, required);
  } else if (part.type === "country_multiselect") {
    input = renderCountryMultiselect(part, required);
  } else if (part.type === "checklist") {
    input = renderChecklist(part);
  } else if (part.type === "file") {
    input = renderFileInput(part);
  } else if (part.type === "number") {
    input = document.createElement("input");
    input.type = "number";
    input.name = part.name;
    if (part.placeholder) input.placeholder = part.placeholder;
    if (part.min != null) input.min = String(part.min);
  } else if (part.type === "text") {
    input = document.createElement("input");
    input.type = "text";
    input.name = part.name;
    if (part.placeholder) input.placeholder = part.placeholder;
  } else {
    input = document.createElement("textarea");
    input.name = part.name;
    input.placeholder = part.placeholder || "";
  }

  if (required && part.type !== "checklist" && part.type !== "country_multiselect" && part.type !== "file") {
    input.required = true;
  }

  block.appendChild(input);
  return block;
}

function renderSiteList(field) {
  const container = document.createElement("div");
  container.className = "site-list";
  container.dataset.fieldPath = field.field_path;

  const rows = document.createElement("div");
  rows.className = "site-rows";
  container.appendChild(rows);

  function addRow(data = {}) {
    const row = document.createElement("div");
    row.className = "site-row";
    row.innerHTML = `
      <label>Location name<input type="text" name="sites.name" value="${data.name || ""}" placeholder="e.g. Berlin office" /></label>
      <label>Country<select name="sites.country"><option value="">— Select —</option></select></label>
      <label>Approx. people<input type="number" name="sites.headcount" min="0" value="${data.headcount || ""}" placeholder="50" /></label>
      <label>Main activity<input type="text" name="sites.primary_function" value="${data.primary_function || ""}" placeholder="e.g. manufacturing, HQ, warehouse" /></label>
      <button type="button" class="secondary remove-site">Remove</button>
    `;
    const countrySelect = row.querySelector('select[name="sites.country"]');
    for (const option of field.country_options || []) {
      const opt = document.createElement("option");
      opt.value = optionValue(option);
      opt.textContent = optionLabel(option);
      if (data.country === opt.value) opt.selected = true;
      countrySelect.appendChild(opt);
    }
    row.querySelector(".remove-site").addEventListener("click", () => row.remove());
    rows.appendChild(row);
  }

  addRow();
  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "secondary";
  addBtn.textContent = "Add another location";
  addBtn.addEventListener("click", () => addRow());
  container.appendChild(addBtn);

  if (field.file_part) {
    container.appendChild(renderPart(field.file_part));
  }

  return container;
}

function renderEntityList(field) {
  const container = document.createElement("div");
  container.className = "entity-list";
  container.dataset.fieldPath = field.field_path;

  const rows = document.createElement("div");
  rows.className = "entity-rows";
  container.appendChild(rows);

  function addRow(data = {}) {
    const row = document.createElement("div");
    row.className = "entity-row";
    row.innerHTML = `
      <label>Legal company name<input type="text" class="entity-name" value="${data.name || ""}" placeholder="e.g. Example Humanitarian NGO Ltd" /></label>
      <label>Country registered<select class="entity-country"><option value="">— Select —</option></select></label>
      <label>Role in group<select class="entity-role"><option value="">— Select —</option></select></label>
      <button type="button" class="secondary remove-entity">Remove</button>
    `;
    const countrySelect = row.querySelector(".entity-country");
    for (const option of field.country_options || []) {
      const opt = document.createElement("option");
      opt.value = optionValue(option);
      opt.textContent = optionLabel(option);
      if (data.country === opt.value) opt.selected = true;
      countrySelect.appendChild(opt);
    }
    const roleSelect = row.querySelector(".entity-role");
    for (const option of field.role_options || []) {
      const opt = document.createElement("option");
      opt.value = optionValue(option);
      opt.textContent = optionLabel(option);
      if (data.role === opt.value) opt.selected = true;
      roleSelect.appendChild(opt);
    }
    row.querySelector(".remove-entity").addEventListener("click", () => row.remove());
    rows.appendChild(row);
  }

  addRow();
  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "secondary";
  addBtn.textContent = "Add another company";
  addBtn.addEventListener("click", () => addRow());
  container.appendChild(addBtn);

  if (field.file_part) {
    container.appendChild(renderPart(field.file_part));
  }

  return container;
}

function renderContactList(field) {
  const container = document.createElement("div");
  container.className = "contact-list";
  container.dataset.fieldPath = field.field_path;

  const rows = document.createElement("div");
  rows.className = "contact-rows";
  container.appendChild(rows);

  function addRow(data = {}) {
    const row = document.createElement("div");
    row.className = "contact-row";
    row.innerHTML = `
      <label>Name<input type="text" class="contact-name" value="${data.name || ""}" placeholder="Full name or role title" /></label>
      <label>Country<select class="contact-country"><option value="">— Select —</option></select></label>
      <label>City<input type="text" class="contact-city" value="${data.city || ""}" placeholder="City" /></label>
      <label>Phone<input type="text" class="contact-phone" value="${data.phone || ""}" placeholder="+1 555 0100" /></label>
      <label>Email<input type="email" class="contact-email" value="${data.email || ""}" placeholder="name@company.com" /></label>
      <button type="button" class="secondary remove-contact">Remove</button>
    `;
    const countrySelect = row.querySelector(".contact-country");
    for (const option of field.country_options || []) {
      const opt = document.createElement("option");
      opt.value = optionValue(option);
      opt.textContent = optionLabel(option);
      if (data.country === opt.value) opt.selected = true;
      countrySelect.appendChild(opt);
    }
    row.querySelector(".remove-contact").addEventListener("click", () => row.remove());
    rows.appendChild(row);
  }

  addRow();
  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "secondary";
  addBtn.textContent = "Add another contact";
  addBtn.addEventListener("click", () => addRow());
  container.appendChild(addBtn);

  return container;
}

function renderField(field) {
  const wrapper = document.createElement("div");
  wrapper.className = "intake-field";
  wrapper.dataset.fieldPath = field.field_path;

  const label = document.createElement("div");
  label.className = "field-label";
  const badges = [];
  if (field.required) badges.push('<span class="required-badge">Required</span>');
  else if (field.priority_label) {
    badges.push(`<span class="priority-badge priority-${field.priority}">${field.priority_label}</span>`);
  }
  label.innerHTML = `<strong>${field.label}</strong>${field.required ? " *" : ""}${badges.join("")}`;
  wrapper.appendChild(label);

  const question = document.createElement("p");
  question.className = "field-question";
  question.textContent = field.question;
  wrapper.appendChild(question);

  if (field.type === "compound") {
    const compound = document.createElement("div");
    compound.className = "compound-field";
    for (const part of field.parts || []) {
      compound.appendChild(renderPart(part, field.required && part.name === field.parts[0]?.name));
    }
    wrapper.appendChild(compound);
  } else if (field.type === "site_list") {
    field.country_options = field.country_options || field.options;
    wrapper.appendChild(renderSiteList(field));
  } else if (field.type === "entity_list") {
    field.country_options = field.country_options || field.options;
    wrapper.appendChild(renderEntityList(field));
  } else if (field.type === "contact_list") {
    field.country_options = field.country_options || field.options;
    wrapper.appendChild(renderContactList(field));
  } else if (field.type === "select") {
    wrapper.appendChild(renderSelect(field, field.required));
  } else if (field.type === "country_multiselect" || field.type === "multiselect") {
    wrapper.appendChild(renderCountryMultiselect(field, field.required));
  } else if (field.type === "checklist") {
    wrapper.appendChild(renderChecklist(field));
  } else if (field.type === "number") {
    const input = document.createElement("input");
    input.type = "number";
    input.name = field.field_path;
    if (field.min != null) input.min = String(field.min);
    if (field.placeholder) input.placeholder = field.placeholder;
    if (field.required) input.required = true;
    wrapper.appendChild(input);
  } else if (field.type === "text") {
    const input = document.createElement("input");
    input.type = "text";
    input.name = field.field_path;
    if (field.placeholder) input.placeholder = field.placeholder;
    if (field.required) input.required = true;
    wrapper.appendChild(input);
  } else if (field.type === "file") {
    wrapper.appendChild(renderFileInput(field));
  } else {
    const input = document.createElement("textarea");
    input.name = field.field_path;
    input.placeholder = field.placeholder || "";
    if (field.required) input.required = true;
    wrapper.appendChild(input);
  }

  addHelp(wrapper, field.help);
  return wrapper;
}

async function readFileValue(input) {
  const file = input.files?.[0];
  if (!file) return null;
  const textTypes = [".txt", ".md", ".csv", ".json"];
  const lower = file.name.toLowerCase();
  if (textTypes.some((ext) => lower.endsWith(ext))) {
    const text = await file.text();
    return { filename: file.name, content: text.slice(0, 20000) };
  }
  return { filename: file.name, content: null, note: "Binary file attached — consultant will review separately." };
}

async function collectAnswers(form) {
  const answers = {};
  const elements = form.querySelectorAll("[name]");

  for (const el of elements) {
    if (el.dataset.fileField === "true") {
      const value = await readFileValue(el);
      if (value) answers[el.name] = value;
      continue;
    }

    if (el.type === "checkbox" && el.name !== "sites.name") {
      if (!answers[el.name]) answers[el.name] = [];
      if (el.checked) answers[el.name].push(el.value);
      continue;
    }

    if (el.tagName === "SELECT" && el.multiple) {
      answers[el.name] = [...el.selectedOptions].map((opt) => opt.value);
      continue;
    }

    if (el.name === "sites.name") continue;

    if (el.tagName === "SELECT" || el.type === "text" || el.type === "number" || el.tagName === "TEXTAREA") {
      if (el.value !== "") answers[el.name] = el.value;
    }
  }

  const siteRows = form.querySelectorAll(".site-row");
  const sites = [];
  for (const row of siteRows) {
    const name = row.querySelector('input[name="sites.name"]')?.value?.trim();
    if (!name) continue;
    sites.push({
      name,
      country: row.querySelector('select[name="sites.country"]')?.value || "",
      headcount: row.querySelector('input[name="sites.headcount"]')?.value || "",
      primary_function: row.querySelector('input[name="sites.primary_function"]')?.value || "",
    });
  }
  if (sites.length) answers.sites = sites;

  for (const list of form.querySelectorAll(".entity-list")) {
    const fieldPath = list.dataset.fieldPath;
    const entities = [];
    for (const row of list.querySelectorAll(".entity-row")) {
      const name = row.querySelector(".entity-name")?.value?.trim();
      if (!name) continue;
      entities.push({
        name,
        country: row.querySelector(".entity-country")?.value || "",
        role: row.querySelector(".entity-role")?.value || "",
      });
    }
    if (entities.length) answers[fieldPath] = entities;
  }

  for (const list of form.querySelectorAll(".contact-list")) {
    const fieldPath = list.dataset.fieldPath;
    const contacts = [];
    for (const row of list.querySelectorAll(".contact-row")) {
      const name = row.querySelector(".contact-name")?.value?.trim();
      if (!name) continue;
      contacts.push({
        name,
        country: row.querySelector(".contact-country")?.value || "",
        city: row.querySelector(".contact-city")?.value?.trim() || "",
        phone: row.querySelector(".contact-phone")?.value?.trim() || "",
        email: row.querySelector(".contact-email")?.value?.trim() || "",
      });
    }
    if (contacts.length) answers[fieldPath] = contacts;
  }

  return answers;
}

let workflowState = null;
let pendingFiles = [];

function setStatus(elementId, message, isError = false) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = message || "";
  el.className = isError ? "merge-status error" : "merge-status";
}

function showWizardStep(stepId) {
  for (const panel of document.querySelectorAll(".wizard-panel")) {
    panel.hidden = true;
  }
  const panel = document.getElementById(`step-${stepId}`);
  if (panel) panel.hidden = false;

  for (const item of document.querySelectorAll("#wizard-progress li")) {
    item.classList.toggle("active", item.dataset.step === stepId);
    item.classList.toggle("done", isStepBefore(item.dataset.step, stepId));
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function isStepBefore(candidate, current) {
  const order = ["setup", "review", "gaps", "confirm", "complete"];
  return order.indexOf(candidate) < order.indexOf(current);
}

async function apiJson(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || body);
    throw new Error(detail || response.statusText);
  }
  return body;
}

async function apiUpload(path, formData) {
  const response = await fetch(path, { method: "POST", body: formData });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || response.statusText);
  }
  return body;
}

function renderUploadList() {
  const list = document.getElementById("upload-list");
  list.innerHTML = "";
  for (const file of pendingFiles) {
    const li = document.createElement("li");
    li.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
    list.appendChild(li);
  }
}

async function loadGapFormSchema(engagementId) {
  const response = await fetch(`/api/v1/intake-form/${encodeURIComponent(engagementId)}/gaps-schema`);
  if (!response.ok) throw new Error("Failed to load remaining questions");
  return response.json();
}

function renderForm(schema) {
  const container = document.getElementById("form-sections");
  container.innerHTML = "";

  if (!schema.sections?.length) {
    container.innerHTML = '<p class="muted">No additional questions — your documents covered everything we need.</p>';
    return;
  }

  for (const section of schema.sections) {
    const details = document.createElement("details");
    details.className = "panel form-section";
    details.open = true;

    const summary = document.createElement("summary");
    summary.textContent = `${section.label} (${section.fields.length} question${section.fields.length === 1 ? "" : "s"})`;
    details.appendChild(summary);

    for (const field of section.fields) {
      if (field.type === "site_list" && !field.country_options) {
        field.country_options = field.options;
      }
      if (!field.country_options && (field.field_path === "countries" || field.type === "country_multiselect")) {
        field.country_options = field.options;
      }
      details.appendChild(renderField(field));
    }

    container.appendChild(details);
  }
}

function renderAppliedFields(result) {
  const container = document.getElementById("applied-fields");
  container.innerHTML = "";
  const fields = result.applied_fields || [];
  if (!fields.length) {
    container.innerHTML = '<p class="muted">We could not auto-match fields from your documents. You will answer all questions in the next step.</p>';
    return;
  }
  const ul = document.createElement("ul");
  ul.className = "applied-list";
  for (const field of fields) {
    const li = document.createElement("li");
    li.textContent = field.replace(/_/g, " ");
    ul.appendChild(li);
  }
  container.appendChild(ul);
}

function updateConfirmStep(result) {
  const score = result.readiness_score;
  const threshold = result.readiness_threshold || 60;
  const open = result.open_gap_count ?? 0;
  document.getElementById("confirm-summary").textContent =
    score != null
      ? `Readiness score: ${score}/${threshold}. ${open} open question(s) remain.`
      : `We have ${open} open question(s) before your consultant can compile the plan.`;

  const note = document.getElementById("confirm-gaps-note");
  if (open > 0) {
    note.hidden = false;
    note.textContent =
      "Some gaps remain. You can go back to answer more questions, or confirm now and your consultant will follow up.";
  } else {
    note.hidden = true;
  }
}

async function bootstrapAndUpload() {
  const engagementId = normalizeEngagementId(document.getElementById("engagement-id").value);
  const companyName = document.getElementById("company-name").value.trim();
  const industry = document.getElementById("industry-filter").value;

  if (!engagementId || !companyName || !industry) {
    throw new Error("Engagement ID, organization name, and industry are required.");
  }
  if (!pendingFiles.length) {
    throw new Error("Upload at least one document (crisis plan, policy, or org chart).");
  }

  await apiJson(`/api/v1/intake-form/${encodeURIComponent(engagementId)}/bootstrap`, {
    method: "POST",
    body: JSON.stringify({ company_name: companyName, industry, countries: [] }),
  });

  for (const file of pendingFiles) {
    const formData = new FormData();
    formData.append("file", file);
    await apiUpload(`/api/v1/intake-form/${encodeURIComponent(engagementId)}/upload`, formData);
  }

  return apiJson(`/api/v1/intake-form/${encodeURIComponent(engagementId)}/process-documents`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

async function resumeWorkflow(engagementId) {
  const status = await apiJson(`/api/v1/intake-form/${encodeURIComponent(engagementId)}/status`);
  if (!status.exists) return;

  if (status.client_name) document.getElementById("company-name").value = status.client_name;
  if (status.industry) document.getElementById("industry-filter").value = status.industry;

  workflowState = status;

  if (status.status === "client_confirmed") {
    document.getElementById("complete-message").textContent =
      "You already confirmed this submission. Your consultant is working on your plan.";
    showWizardStep("complete");
    return;
  }

  if (status.status === "gap_review") {
    document.getElementById("review-summary").textContent =
      `Readiness ${status.readiness_score ?? "—"}/${status.readiness_threshold}. ${status.open_gap_count} question(s) still open.`;
    renderAppliedFields({ applied_fields: [] });
    if (status.open_gap_count > 0) {
      showWizardStep("gaps");
      await loadAndRenderGaps(engagementId);
    } else {
      updateConfirmStep(status);
      showWizardStep("confirm");
    }
  }
}

async function loadAndRenderGaps(engagementId) {
  const schema = await loadGapFormSchema(engagementId);
  workflowState = { ...workflowState, ...schema };
  document.getElementById("gaps-intro").textContent =
    schema.field_count > 0
      ? `Please answer these ${schema.field_count} question(s). Your documents already filled in the rest.`
      : "No additional questions needed.";
  renderForm(schema);
}

document.getElementById("document-upload").addEventListener("change", (event) => {
  pendingFiles = [...(event.target.files || [])];
  renderUploadList();
});

document.getElementById("btn-process-docs").addEventListener("click", async () => {
  setStatus("setup-status", "Uploading and analyzing documents…");
  try {
    const result = await bootstrapAndUpload();
    workflowState = result;
    const engagementId = normalizeEngagementId(document.getElementById("engagement-id").value);

    document.getElementById("review-summary").textContent =
      `We applied ${result.applied_count} field(s) from your documents. Readiness score: ${result.readiness_score ?? "—"}/${result.readiness_threshold}. ${result.open_gap_count} question(s) still needed.`;
    renderAppliedFields(result);
    showWizardStep("review");

    if (result.open_gap_count > 0) {
      await loadAndRenderGaps(engagementId);
    }
    setStatus("setup-status", "");
  } catch (error) {
    setStatus("setup-status", String(error.message || error), true);
  }
});

document.getElementById("btn-to-gaps").addEventListener("click", async () => {
  const engagementId = normalizeEngagementId(document.getElementById("engagement-id").value);
  if ((workflowState?.open_gap_count ?? 0) > 0) {
    showWizardStep("gaps");
    await loadAndRenderGaps(engagementId);
  } else {
    updateConfirmStep(workflowState || {});
    showWizardStep("confirm");
  }
});

document.getElementById("client-intake-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const engagementId = normalizeEngagementId(document.getElementById("engagement-id").value);
  const answers = await collectAnswers(event.target);
  setStatus("gaps-status", "Saving…");
  try {
    const result = await apiJson(`/api/v1/intake-form/${encodeURIComponent(engagementId)}/submit-gaps`, {
      method: "POST",
      body: JSON.stringify({ answers, industry: document.getElementById("industry-filter").value }),
    });
    workflowState = result;
    updateConfirmStep(result);
    setStatus("gaps-status", "Saved.");
    showWizardStep("confirm");
  } catch (error) {
    setStatus("gaps-status", String(error.message || error), true);
  }
});

document.getElementById("btn-skip-to-confirm").addEventListener("click", () => {
  updateConfirmStep(workflowState || {});
  showWizardStep("confirm");
});

document.getElementById("btn-confirm-submit").addEventListener("click", async () => {
  const engagementId = normalizeEngagementId(document.getElementById("engagement-id").value);
  setStatus("confirm-status", "Submitting…");
  try {
    const form = document.getElementById("client-intake-form");
    const answers = form ? await collectAnswers(form) : {};
    const result = await apiJson(`/api/v1/intake-form/${encodeURIComponent(engagementId)}/confirm`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    });
    document.getElementById("complete-message").textContent = result.message;
    setStatus("confirm-status", "");
    showWizardStep("complete");
  } catch (error) {
    setStatus("confirm-status", String(error.message || error), true);
  }
});

const params = new URLSearchParams(window.location.search);
if (params.get("industry")) {
  document.getElementById("industry-filter").value = params.get("industry");
}
if (params.get("engagement")) {
  document.getElementById("engagement-id").value = params.get("engagement");
  resumeWorkflow(normalizeEngagementId(params.get("engagement"))).catch(() => {});
}
