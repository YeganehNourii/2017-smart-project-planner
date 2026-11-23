// Web demo: keeps the project as plain JSON, sends it to the Python core
// (planner.web.analyse, running in Pyodide) after every change, and renders
// the result. If Python rejects a change (e.g. a dependency cycle) the change
// is undone and the error is shown.
(function () {
  "use strict";

  const STORAGE_KEY = "smart-planner-project";
  const $ = (id) => document.getElementById(id);
  let analyse = null;   // Python function
  let sample = null;    // sample project JSON
  let project = null;   // current project (plain object)

  const today = new Date().toISOString().slice(0, 10);

  function setStatus(text, ready) {
    $("status").textContent = text;
    $("status").classList.toggle("ready", !!ready);
  }

  function showError(text) {
    $("error").hidden = !text;
    $("error").textContent = text || "";
  }

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") node.className = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined && v !== false) node.setAttribute(k, v === true ? "" : v);
    }
    for (const c of children) node.append(c instanceof Node ? c : document.createTextNode(String(c)));
    return node;
  }

  // ---- Python bridge ------------------------------------------------------

  async function boot() {
    try {
      const pyodide = await loadPyodide();
      const manifest = await (await fetch("py/manifest.json")).json();
      pyodide.FS.mkdirTree("/home/pyodide/planner");
      for (const path of manifest.python) {
        const code = await (await fetch("py/" + path)).text();
        pyodide.FS.writeFile("/home/pyodide/" + path, code);
      }
      sample = await (await fetch("py/samples/campus-app.json")).json();
      pyodide.runPython("import sys; sys.path.insert(0, '/home/pyodide')");
      analyse = pyodide.pyimport("planner.web").analyse;
      setStatus(`Python ${pyodide.version ? "(Pyodide " + pyodide.version + ")" : ""} ready.`, true);
    } catch (err) {
      setStatus("Could not start Python: " + err + ". If you opened the file directly, run scripts/build_site.py and serve site/ over HTTP.");
      return;
    }
    document.querySelectorAll("button, input, select").forEach((n) => (n.disabled = false));

    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch (e) { /* ignore */ }
    if (!setProject(saved || sample)) setProject(sample);
  }

  function run(p) {
    return JSON.parse(analyse(JSON.stringify(p), 5, today));
  }

  // Applies a new project if Python accepts it. Returns true on success.
  function setProject(next) {
    const result = run(next);
    if (!result.ok) {
      showError(result.error);
      return false;
    }
    showError("");
    project = next;
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(project)); } catch (e) { /* private mode */ }
    render(result);
    return true;
  }

  function change(mutator) {
    const copy = JSON.parse(JSON.stringify(project));
    mutator(copy);
    return setProject(copy);
  }

  // ---- Rendering ----------------------------------------------------------

  function render(r) {
    $("p-name").value = project.name;
    $("p-start").value = project.start;

    const warn = r.warnings.join("\n");
    $("warnings").hidden = !warn;
    $("warnings").textContent = warn ? "⚠ " + r.warnings.join("\n⚠ ") : "";

    const byId = Object.fromEntries(r.schedule.map((s) => [s.id, s]));

    // Next up
    const next = $("next");
    next.replaceChildren();
    if (r.next.length === 0) next.append(el("li", {}, r.schedule.length ? "Everything is done 🎉" : "Add a task to get started."));
    for (const n of r.next) {
      const crit = byId[n.id].critical;
      next.append(el("li", {},
        el("strong", {}, n.name), n.owner ? ` — ${n.owner}` : "",
        el("span", { class: "why" + (crit ? " crit" : "") }, n.reasons.join(" · "))));
    }

    // Critical path chain
    $("duration").textContent = r.schedule.length
      ? `· ${r.project.duration} days, ${r.project.start} → ${r.project.end}` : "";
    const chain = $("critical");
    chain.replaceChildren();
    r.critical_path.forEach((id, i) => {
      if (i) chain.append(el("span", { class: "arrow" }, "→"));
      chain.append(el("span", { class: "chip" + (byId[id].done ? " done" : ""), title: byId[id].name }, id));
    });

    // Gantt chart (figure built by planner.gantt in Python)
    const css = getComputedStyle(document.documentElement);
    const layout = Object.assign({}, r.figure.layout, {
      title: null,  // the card already shows the dates
      margin: Object.assign({}, r.figure.layout.margin, { t: 10 }),
      font: { color: css.getPropertyValue("--fg").trim(), family: "system-ui, sans-serif" },
    });
    if (r.schedule.length) {
      Plotly.react("gantt", r.figure.data, layout, { responsive: true, displaylogo: false });
    } else {
      Plotly.purge("gantt");
    }

    // Task table
    const body = $("tasks").querySelector("tbody");
    body.replaceChildren();
    for (const s of r.schedule) {
      const cls = [s.done ? "done" : "", s.critical ? "critical" : ""].join(" ").trim();
      body.append(el("tr", { class: cls },
        el("td", {}, el("input", {
          type: "checkbox", checked: s.done, "aria-label": "done: " + s.name,
          onchange: (e) => change((p) => { p.tasks.find((t) => t.id === s.id).done = e.target.checked; }),
        })),
        el("td", {}, s.id),
        el("td", {}, s.name),
        el("td", {}, s.owner),
        el("td", { class: "num" }, s.duration === 0 ? "◆" : s.duration),
        el("td", {}, s.depends_on.join(", ")),
        el("td", {}, s.start),
        el("td", {}, s.finish),
        el("td", { class: "num" }, s.slack),
        el("td", {}, s.deadline || "", s.late ? el("span", { class: "badge" }, `late ${s.days_late}d`) : ""),
        el("td", {}, el("button", {
          type: "button", title: "Delete " + s.id,
          onclick: () => {
            const users = r.schedule.filter((x) => x.depends_on.includes(s.id)).map((x) => x.id);
            if (users.length) return showError(`Cannot delete ${s.id}: ${users.join(", ")} depend(s) on it.`);
            change((p) => { p.tasks = p.tasks.filter((t) => t.id !== s.id); });
          },
        }, "✕")),
      ));
    }
    $("task-ids").replaceChildren(...r.schedule.map((s) => el("option", { value: s.id })));
  }

  // ---- Events -------------------------------------------------------------

  $("btn-sample").addEventListener("click", () => setProject(JSON.parse(JSON.stringify(sample))));
  $("btn-new").addEventListener("click", () =>
    setProject({ name: $("p-name").value || "My project", start: $("p-start").value || today, tasks: [] }));
  $("p-name").addEventListener("change", (e) => change((p) => { p.name = e.target.value; }));
  $("p-start").addEventListener("change", (e) => change((p) => { p.start = e.target.value; }));

  $("btn-export").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(project, null, 2) + "\n"], { type: "application/json" });
    const a = el("a", { href: URL.createObjectURL(blob), download: "project.json" });
    a.click();
    URL.revokeObjectURL(a.href);
  });

  $("file-import").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try { setProject(JSON.parse(await file.text())); }
    catch (err) { showError("Not a valid JSON file: " + err.message); }
    e.target.value = "";
  });

  $("add").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    const task = {
      id: f.get("id").trim(),
      name: f.get("name").trim(),
      duration: Number(f.get("duration")),
      owner: f.get("owner").trim(),
      priority: Number(f.get("priority")),
      deadline: f.get("deadline") || null,
      depends_on: f.get("depends_on").split(",").map((x) => x.trim()).filter(Boolean),
      done: false,
    };
    if (project.tasks.some((t) => t.id === task.id)) return showError(`Task id "${task.id}" already exists.`);
    if (change((p) => p.tasks.push(task))) e.target.reset();
  });

  boot();
})();
