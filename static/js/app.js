function renderSimpleChart(id, labels, values) {
  const canvas = document.getElementById(id);
  if (!canvas || !window.Chart) return;
  new Chart(canvas, {
    type: "bar",
    data: { labels, datasets: [{ label: "Visitors", data: values, backgroundColor: ["#175cd3", "#12b76a", "#f79009", "#f04438", "#7a5af8"] }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.io) {
    const socket = io();
    socket.on("notification", (data) => {
      const badge = document.getElementById("notifyBadge");
      if (badge) badge.textContent = String((parseInt(badge.textContent || "0", 10) || 0) + 1);
      if (window.bootstrap) {
        const toast = document.createElement("div");
        toast.className = "toast align-items-center text-bg-primary border-0 position-fixed bottom-0 end-0 m-3";
        toast.innerHTML = `<div class="d-flex"><div class="toast-body">${data.message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
        document.body.appendChild(toast);
        new bootstrap.Toast(toast).show();
      }
    });
  }

  const form = document.getElementById("collegeSearchForm");
  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = document.getElementById("collegeIdInput");
      const box = document.getElementById("ajaxSearchResult");
      box.innerHTML = '<div class="text-muted">Searching...</div>';
      const res = await fetch(`/security/api/search?college_id=${encodeURIComponent(input.value)}`);
      const data = await res.json();
      box.innerHTML = data.found
        ? `<div class="alert alert-success"><strong>${data.name}</strong><br>${data.designation || "Student"} · ${data.department || "-"} · ${data.phone || "-"}</div>`
        : '<div class="alert alert-warning">No college ID record found.</div>';
    });
  }
});
