const engagementPicker = document.getElementById("engagement-picker");
const workflowEmpty = document.getElementById("workflow-empty");
const workflowActive = document.getElementById("workflow-active");
const summaryClient = document.getElementById("summary-client");
const summaryMeta = document.getElementById("summary-meta");
const summaryStatus = document.getElementById("summary-status");
const workflowSteps = document.getElementById("workflow-steps");
const readinessValue = document.getElementById("readiness-value");
const readinessDetail = document.getElementById("readiness-detail");
const nextActionCopy = document.getElementById("next-action-copy");
const readinessCard = document.querySelector(".readiness-card");
const output = document.getElementById("output");
const searchResults = document.getElementById("search-results");
const intakeLink = document.getElementById("intake-link");
const btnNext = document.getElementById("btn-next");
const btnDiscovery = document.getElementById("btn-discovery");
const btnPlan = document.getElementById("btn-plan");
const btnDocx = document.getElementById("btn-docx");
const gapsList = document.getElementById("gaps-list");
const gapsSummary = document.getElementById("gaps-summary");
const mergeJson = document.getElementById("merge-json");
const documentsList = document.getElementById("documents-list");
const proposalsPanel = document.getElementById("proposals-panel");
const proposalsList = document.getElementById("proposals-list");
const proposalsMeta = document.getElementById("proposals-meta");
const deliverablesBrowser = document.getElementById("deliverables-browser");
const deliverableViewer = document.getElementById("deliverable-viewer");
const viewerTitle = document.getElementById("viewer-title");
const viewerContent = document.getElementById("viewer-content");
const viewerDownload = document.getElementById("viewer-download");

let currentWorkflow = null;
let currentEngagementId = "";
let currentGaps = [];
let currentProposals = [];

function showRaw(data) {
  output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function normalizeEngagementId(raw) {
  return raw
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9_.-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[-_.]+|[-_.]+$/g, "");
}

function formatApiError(body) {
  if (Array.isArray(body?.detail)) {
    return body.detail
      .map((item) => `${item.loc?.slice(1).join(".") || "request"}: ${item.msg}`)
      .join("\n");
  }
  if (typeof body?.detail === "string") return body.detail;
  return JSON.stringify(body, null, 2);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!response.ok) throw new Error(formatApiError(body) || response.statusText);
  return body;
}

async function apiUpload(path, formData) {
  const response = await fetch(path, { method: "POST", body: formData });
  const text = await response.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!response.ok) throw new Error(formatApiError(body) || response.statusText);
  return body;
}

function switchTab(tabName) {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    const active = panel.dataset.panel === tabName;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
}

function formatEngagementOption(record) {
  return `${record.engagement_id} — ${record.client_name || record.engagement_id}`;
}

function populateEngagementPicker(list) {
  engagementPicker.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = list.length ? "Choose an engagement…" : "No engagements yet";
  engagementPicker.appendChild(placeholder);
  for (const record of list) {
    const option = document.createElement("option");
    option.value = record.engagement_id;
    option.textContent = formatEngagementOption(record);
    engagementPicker.appendChild(option);
  }
  if (currentEngagementId && list.some((record) => record.engagement_id === currentEngagementId)) {
    engagementPicker.value = currentEngagementId;
  }
}

async function loadEngagements(selectId) {
  const list = await api("/api/v1/engagements");
  populateEngagementPicker(list);
  if (selectId) {
    currentEngagementId = selectId;
    engagementPicker.value = selectId;
    await refreshEngagementViews();
  }
}

function renderSteps(steps) {
  workflowSteps.innerHTML = "";
  for (const step of steps) {
    const item = document.createElement("li");
    item.className = step.state;
    item.innerHTML = `<span class="step-label">${step.label}</span><span class="step-detail">${step.detail || step.state}</span>`;
    workflowSteps.appendChild(item);
  }
}

function renderWorkflow(workflow) {
  currentWorkflow = workflow;
  workflowEmpty.hidden = true;
  workflowActive.hidden = false;
  summaryClient.textContent = workflow.client_name || workflow.engagement_id;
  summaryMeta.textContent = [workflow.industry, workflow.engagement_id].filter(Boolean).join(" · ");
  summaryStatus.textContent = workflow.status || "new";
  summaryStatus.className = `status-pill ${workflow.status || ""}`;
  intakeLink.href = `/intake?engagement=${encodeURIComponent(workflow.engagement_id)}`;
  renderSteps(workflow.steps);

  if (workflow.readiness_score == null) {
    readinessValue.textContent = "—";
    readinessDetail.textContent = "Run discovery to calculate readiness.";
    readinessCard.className = "readiness-card";
  } else {
    readinessValue.textContent = String(workflow.readiness_score);
    const gaps = workflow.critical_gaps ?? 0;
    readinessDetail.textContent = workflow.gate_passed
      ? `Ready for full plan (${workflow.readiness_score}/${workflow.readiness_threshold}).`
      : `Blocked at readiness gate (${workflow.readiness_score}/${workflow.readiness_threshold}). ${gaps} critical gap(s).`;
    readinessCard.className = `readiness-card ${workflow.gate_passed ? "pass" : "block"}`;
  }

  const next = workflow.next_action;
  nextActionCopy.textContent = next.description;
  btnNext.textContent = next.label;
  btnNext.disabled = next.kind === "info";
  btnPlan.disabled = !workflow.gate_passed;
  btnDocx.disabled = workflow.deliverable_count === 0;
}

async function loadWorkflow(engagementId) {
  if (!engagementId) {
    currentEngagementId = "";
    currentWorkflow = null;
    workflowEmpty.hidden = false;
    workflowActive.hidden = true;
    return;
  }
  currentEngagementId = engagementId;
  const workflow = await api(`/api/v1/engagements/${encodeURIComponent(engagementId)}/workflow`);
  renderWorkflow(workflow);
}

function priorityClass(priority) {
  return `priority-${(priority || "medium").toLowerCase()}`;
}

function renderGaps(data) {
  currentGaps = data.gaps || [];
  if (data.message) {
    gapsSummary.textContent = data.message;
  } else {
    const open = currentGaps.filter((gap) => !gap.resolved).length;
    gapsSummary.textContent = `Readiness ${data.readiness_score}/${data.readiness_threshold} · ${open} open gap(s) · ${data.critical_gaps?.length || 0} critical`;
  }

  gapsList.innerHTML = "";
  if (!currentGaps.length) {
    gapsList.innerHTML = '<div class="empty-inline">No open gaps — discovery is clear or not yet run.</div>';
    return;
  }

  for (const gap of currentGaps) {
    const card = document.createElement("article");
    card.className = `gap-card ${gap.resolved ? "resolved" : ""}`;
    card.innerHTML = `
      <div class="gap-head">
        <label class="checkbox-inline">
          <input type="checkbox" class="gap-select" data-requirement-id="${gap.requirement_id}" ${gap.resolved ? "disabled" : ""} />
          <strong>${gap.requirement_id}</strong>
          <span class="priority ${priorityClass(gap.priority)}">${gap.priority}</span>
        </label>
        <span class="muted">${gap.field_path}</span>
      </div>
      <h4>${gap.label}</h4>
      <p>${gap.why_it_matters}</p>
      ${gap.question ? `<p class="question"><em>${gap.question}</em></p>` : ""}
      <div class="gap-actions">
        <input type="text" class="gap-value" data-field-path="${gap.field_path}" placeholder="Enter value to merge" ${gap.resolved ? "disabled" : ""} />
        <button type="button" class="secondary gap-apply" data-field-path="${gap.field_path}" ${gap.resolved ? "disabled" : ""}>Apply value</button>
      </div>
    `;
    gapsList.appendChild(card);
  }

  gapsList.querySelectorAll(".gap-apply").forEach((button) => {
    button.addEventListener("click", async () => {
      const fieldPath = button.dataset.fieldPath;
      const input = gapsList.querySelector(`.gap-value[data-field-path="${fieldPath}"]`);
      await applyMerge({ [fieldPath]: input.value }, []);
    });
  });
}

async function loadGaps() {
  if (!currentEngagementId) return;
  const data = await api(`/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/gaps`);
  renderGaps(data);
}

async function applyMerge(updates, resolve, rerunDiscovery = true) {
  if (!currentEngagementId) return;
  const result = await api(`/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/merge`, {
    method: "POST",
    body: JSON.stringify({ updates, resolve, rerun_discovery: rerunDiscovery }),
  });
  showRaw(result);
  await refreshEngagementViews();
  return result;
}

async function loadDocuments() {
  if (!currentEngagementId) return;
  documentsList.innerHTML = "";
  const docs = await api(`/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/documents`);
  if (!docs.length) {
    documentsList.innerHTML = '<div class="empty-inline">No documents uploaded yet.</div>';
    return;
  }
  for (const doc of docs) {
    const row = document.createElement("div");
    row.className = "doc-row";
    row.innerHTML = `
      <div>
        <strong>${doc.filename}</strong>
        <span class="muted">${Math.round(doc.size_bytes / 1024)} KB · ${doc.suffix}</span>
      </div>
      <button type="button" class="secondary extract-doc" data-document-id="${doc.document_id}">Extract proposals</button>
    `;
    documentsList.appendChild(row);
  }
  documentsList.querySelectorAll(".extract-doc").forEach((button) => {
    button.addEventListener("click", () => extractDocument(button.dataset.documentId));
  });
}

function renderProposals(data) {
  currentProposals = data.proposals || [];
  proposalsPanel.hidden = false;
  proposalsMeta.textContent = `${data.proposal_count} proposal(s) from ${data.document_id} · ${data.open_gaps} open gap(s)`;
  proposalsList.innerHTML = "";
  if (!currentProposals.length) {
    proposalsList.innerHTML = '<div class="empty-inline">No matching fields found in this document.</div>';
    return;
  }
  for (const proposal of currentProposals) {
    const value =
      typeof proposal.proposed_value === "string"
        ? proposal.proposed_value
        : JSON.stringify(proposal.proposed_value);
    const card = document.createElement("article");
    card.className = "gap-card";
    card.innerHTML = `
      <label class="checkbox-inline">
        <input type="checkbox" class="proposal-select" data-field-path="${proposal.field_path}" checked />
        <strong>${proposal.requirement_id}</strong>
        <span class="priority ${priorityClass("high")}">${proposal.confidence}</span>
      </label>
      <h4>${proposal.label}</h4>
      <p class="muted">${proposal.source_snippet}</p>
      <pre class="proposal-value">${value}</pre>
    `;
    proposalsList.appendChild(card);
  }
}

async function extractDocument(documentId) {
  const data = await api(
    `/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/documents/${encodeURIComponent(documentId)}/extract`,
    { method: "POST" }
  );
  showRaw(data);
  renderProposals(data);
  switchTab("documents");
}

function renderDeliverablesBrowser(workflow) {
  deliverablesBrowser.innerHTML = "";
  const markdown = (workflow?.deliverables || []).map((file) => ({ file, kind: "markdown" }));
  const docx = (workflow?.docx_files || []).map((file) => ({ file, kind: "docx" }));
  const entries = [...markdown, ...docx];
  if (!entries.length) {
    deliverablesBrowser.innerHTML = '<div class="empty-inline">No deliverables yet. Generate the full plan first.</div>';
    return;
  }
  for (const entry of entries) {
    const row = document.createElement("div");
    row.className = "doc-row";
    const downloadPath =
      entry.kind === "docx"
        ? `/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/download/docx/${encodeURIComponent(entry.file)}`
        : `/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/download/markdown/${encodeURIComponent(entry.file)}`;
    row.innerHTML = `
      <div><strong>${entry.file}</strong><span class="muted">${entry.kind.toUpperCase()}</span></div>
      <div class="row-actions">
        ${entry.kind === "markdown" ? `<button type="button" class="secondary view-md" data-path="${entry.file}">View</button>` : ""}
        <a class="secondary button-link" href="${downloadPath}">Download</a>
      </div>
    `;
    deliverablesBrowser.appendChild(row);
  }
  deliverablesBrowser.querySelectorAll(".view-md").forEach((button) => {
    button.addEventListener("click", () => viewDeliverable(button.dataset.path));
  });
}

async function viewDeliverable(path) {
  const data = await api(
    `/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/deliverables/${encodeURIComponent(path)}`
  );
  viewerTitle.textContent = path;
  viewerDownload.href = `/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/download/markdown/${encodeURIComponent(path)}`;
  viewerDownload.download = path.split("/").pop();
  viewerContent.innerHTML = window.marked ? marked.parse(data.content) : `<pre>${data.content}</pre>`;
  deliverableViewer.hidden = false;
}

async function refreshEngagementViews() {
  await loadWorkflow(currentEngagementId);
  await loadGaps();
  await loadDocuments();
  renderDeliverablesBrowser(currentWorkflow);
}

async function runApiAction(path, label) {
  btnNext.disabled = true;
  try {
    const result = await api(path, { method: "POST" });
    showRaw({ action: label, result });
    await refreshEngagementViews();
    return result;
  } finally {
    if (currentWorkflow?.next_action?.kind !== "info") btnNext.disabled = false;
  }
}

async function runNextAction() {
  if (!currentWorkflow?.next_action) return;
  const next = currentWorkflow.next_action;
  if (next.id === "gaps") {
    switchTab("gaps");
    return;
  }
  if (next.kind === "link") {
    window.location.href = next.path;
    return;
  }
  if (next.kind === "api") {
    await runApiAction(next.path, next.label);
  }
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

engagementPicker.addEventListener("change", () => {
  currentEngagementId = engagementPicker.value;
  refreshEngagementViews().catch((error) => showRaw(String(error.message || error)));
});

document.getElementById("btn-refresh-engagements").addEventListener("click", () => {
  loadEngagements(currentEngagementId).catch((error) => showRaw(String(error.message || error)));
});

document.getElementById("create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const engagementId = normalizeEngagementId(form.elements.namedItem("engagement_id").value);
  const countries = form.elements.namedItem("countries").value.split(",").map((c) => c.trim()).filter(Boolean);
  if (!engagementId || !countries.length) return showRaw("Engagement ID and countries are required.");
  const record = await api("/api/v1/engagements", {
    method: "POST",
    body: JSON.stringify({
      engagement_id: engagementId,
      intake: {
        company_name: form.elements.namedItem("company_name").value.trim(),
        industry: form.elements.namedItem("industry").value.trim(),
        countries,
      },
    }),
  });
  await loadEngagements(record.engagement_id);
  showRaw({ created: record });
  form.reset();
});

btnNext.addEventListener("click", () => runNextAction().catch((error) => showRaw(String(error.message || error))));
btnDiscovery.addEventListener("click", () =>
  runApiAction(`/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/discovery`, "Discovery").catch((e) =>
    showRaw(String(e.message || e))
  )
);
btnPlan.addEventListener("click", () =>
  runApiAction(`/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/plan`, "Full plan").catch((e) =>
    showRaw(String(e.message || e))
  )
);
btnDocx.addEventListener("click", () =>
  runApiAction(`/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/export/docx`, "DOCX export").catch((e) =>
    showRaw(String(e.message || e))
  )
);
document.getElementById("btn-export-docx-panel").addEventListener("click", () =>
  runApiAction(`/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/export/docx`, "DOCX export").catch((e) =>
    showRaw(String(e.message || e))
  )
);

document.getElementById("btn-refresh-gaps").addEventListener("click", () =>
  loadGaps().catch((error) => showRaw(String(error.message || error)))
);
document.getElementById("btn-open-intake").addEventListener("click", () => {
  if (currentEngagementId) window.location.href = `/intake?engagement=${encodeURIComponent(currentEngagementId)}`;
});
document.getElementById("btn-resolve-selected").addEventListener("click", async () => {
  const resolve = [...document.querySelectorAll(".gap-select:checked")].map((el) => el.dataset.requirementId);
  if (!resolve.length) return showRaw("Select at least one gap to mark as N/A.");
  await applyMerge({}, resolve);
});
document.getElementById("btn-apply-merge").addEventListener("click", async () => {
  try {
    const updates = JSON.parse(mergeJson.value || "{}");
    await applyMerge(updates, []);
    mergeJson.value = "";
  } catch (error) {
    showRaw(`Invalid JSON: ${error.message || error}`);
  }
});

document.getElementById("document-upload").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file || !currentEngagementId) return;
  const formData = new FormData();
  formData.append("file", file);
  try {
    const uploaded = await apiUpload(
      `/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/documents/upload`,
      formData
    );
    showRaw({ uploaded });
    event.target.value = "";
    await loadDocuments();
  } catch (error) {
    showRaw(String(error.message || error));
  }
});

document.getElementById("btn-apply-proposals").addEventListener("click", async () => {
  const updates = {};
  for (const checkbox of document.querySelectorAll(".proposal-select:checked")) {
    const fieldPath = checkbox.dataset.fieldPath;
    const proposal = currentProposals.find((item) => item.field_path === fieldPath);
    if (proposal) updates[fieldPath] = proposal.proposed_value;
  }
  if (!Object.keys(updates).length) return showRaw("Select at least one proposal to apply.");
  await api(`/api/v1/engagements/${encodeURIComponent(currentEngagementId)}/documents/apply`, {
    method: "POST",
    body: JSON.stringify({ updates, resolve: [], rerun_discovery: true }),
  }).then(async (result) => {
    showRaw(result);
    proposalsPanel.hidden = true;
    await refreshEngagementViews();
  });
});

document.getElementById("btn-refresh-deliverables").addEventListener("click", () =>
  refreshEngagementViews().catch((error) => showRaw(String(error.message || error)))
);

document.getElementById("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const q = event.target.q.value.trim();
  searchResults.innerHTML = "";
  try {
    const results = await api(`/api/v1/knowledge/search?q=${encodeURIComponent(q)}`);
    if (!results.length) {
      searchResults.innerHTML = "<li>No matches.</li>";
      return;
    }
    for (const item of results) {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${item.heading}</strong><span>${item.source}</span><p>${item.excerpt}</p>`;
      searchResults.appendChild(li);
    }
  } catch (error) {
    searchResults.innerHTML = `<li>${error.message || error}</li>`;
  }
});

const params = new URLSearchParams(window.location.search);
loadEngagements(normalizeEngagementId(params.get("engagement") || "")).catch((error) => {
  engagementPicker.innerHTML = '<option value="">Could not load engagements</option>';
  showRaw(String(error.message || error));
});
