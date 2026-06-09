const output = document.getElementById("output");
const workflowId = document.getElementById("workflow-id");
const searchResults = document.getElementById("search-results");

function show(data) {
  output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
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
    throw new Error(body?.detail || body || response.statusText);
  }
  return body;
}

document.getElementById("create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const engagementId = form.engagement_id.value.trim();
  const countries = form.countries.value.split(",").map((c) => c.trim()).filter(Boolean);
  const payload = {
    engagement_id: engagementId,
    intake: {
      company_name: form.company_name.value.trim(),
      industry: form.industry.value.trim(),
      countries,
    },
  };
  try {
    const record = await api("/api/v1/engagements", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    workflowId.value = engagementId;
    show({ created: record });
  } catch (error) {
    show(String(error.message || error));
  }
});

document.getElementById("btn-discovery").addEventListener("click", async () => {
  const id = workflowId.value.trim();
  if (!id) return show("Enter an engagement ID.");
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
  const id = workflowId.value.trim();
  if (!id) return show("Enter an engagement ID.");
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
  const id = workflowId.value.trim();
  if (!id) return show("Enter an engagement ID.");
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
