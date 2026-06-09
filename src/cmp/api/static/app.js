const output = document.getElementById("output");
const workflowId = document.getElementById("workflow-id");
const searchResults = document.getElementById("search-results");

function show(data) {
  output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function normalizeEngagementId(raw) {
  return raw
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[-_.]+|[-_.]+$/g, "");
}

function formatApiError(body) {
  if (Array.isArray(body?.detail)) {
    return body.detail
      .map((item) => {
        const field = item.loc?.slice(1).join(".") || "request";
        return `${field}: ${item.msg}`;
      })
      .join("\n");
  }
  if (typeof body?.detail === "string") {
    return body.detail;
  }
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
  if (!response.ok) {
    throw new Error(formatApiError(body) || response.statusText);
  }
  return body;
}

document.getElementById("create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const rawId = form.elements.namedItem("engagement_id").value;
  const engagementId = normalizeEngagementId(rawId);
  const countries = form.elements.namedItem("countries").value
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean);

  if (!engagementId) {
    show("Engagement ID is required (letters, numbers, hyphens only).");
    return;
  }
  if (!countries.length) {
    show("Enter at least one country.");
    return;
  }

  const payload = {
    engagement_id: engagementId,
    intake: {
      company_name: form.elements.namedItem("company_name").value.trim(),
      industry: form.elements.namedItem("industry").value.trim(),
      countries,
    },
  };

  try {
    const record = await api("/api/v1/engagements", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    workflowId.value = engagementId;
    show({
      created: record,
      note: rawId.trim() !== engagementId ? `Using engagement ID: ${engagementId}` : undefined,
    });
  } catch (error) {
    show(String(error.message || error));
  }
});

document.getElementById("btn-discovery").addEventListener("click", async () => {
  const id = normalizeEngagementId(workflowId.value);
  if (!id) return show("Enter an engagement ID.");
  workflowId.value = id;
  try {
    const result = await api(`/api/v1/engagements/${encodeURIComponent(id)}/discovery`, {
      method: "POST",
    });
    show(result);
  } catch (error) {
    show(String(error.message || error));
  }
});

document.getElementById("btn-plan").addEventListener("click", async () => {
  const id = normalizeEngagementId(workflowId.value);
  if (!id) return show("Enter an engagement ID.");
  workflowId.value = id;
  try {
    const result = await api(`/api/v1/engagements/${encodeURIComponent(id)}/plan`, {
      method: "POST",
    });
    show(result);
  } catch (error) {
    show(String(error.message || error));
  }
});

document.getElementById("btn-docx").addEventListener("click", async () => {
  const id = normalizeEngagementId(workflowId.value);
  if (!id) return show("Enter an engagement ID.");
  workflowId.value = id;
  try {
    const result = await api(`/api/v1/engagements/${encodeURIComponent(id)}/export/docx`, {
      method: "POST",
    });
    show(result);
  } catch (error) {
    show(String(error.message || error));
  }
});

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
