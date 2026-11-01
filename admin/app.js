const pages = {};
let token = sessionStorage.getItem("tk") || "";

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, function (c) {
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c];
  });
}

async function api(path, opts) {
  opts = opts || {};
  const h = {"Content-Type": "application/json"};
  if (token) h["Authorization"] = "Bearer " + token;
  const r = await fetch(path, {
    method: opts.method || "GET",
    headers: h,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (r.status === 401 && token) {
    logout();
    throw new Error("انتهت الجلسة، سجّل الدخول من جديد");
  }
  if (r.status === 204) return null;
  let d = null;
  try { d = await r.json(); } catch (e) {}
  if (!r.ok) {
    let m = "خطأ " + r.status;
    if (d && typeof d.detail === "string") m = tr(d.detail); else if (d && d.detail) m = "بيانات غير صالحة";
    throw new Error(m);
  }
  return d;
}

const NAV = [
  ["dashboard", "الرئيسية"],
  ["licenses", "أكواد التفعيل"],
  ["subscriptions", "الاشتراكات"],
  ["uuids", "UUIDs"],
  ["proxies", "البروكسيات"],
  ["config", "إعدادات Xray"],
  ["xray", "سيرفرات Xray"],
  ["devices", "الأجهزة"],
  ["logs", "السجل"],
  ["account", "حسابي"],
];

function $(id) { return document.getElementById(id); }

async function route() {
  const k = (location.hash || "#dashboard").slice(1);
  $("nav").innerHTML = NAV.map(function (n) {
    return '<a href="#' + n[0] + '" class="' + (n[0] === k ? "on" : "") + '">' + n[1] + "</a>";
  }).join("");
  const cur = NAV.find(function (n) { return n[0] === k; });
  $("title").textContent = cur ? cur[1] : "";
  const el = $("view");
  el.onclick = null;
  if (!pages[k]) { el.textContent = "قريباً"; return; }
  try {
    await pages[k](el);
  } catch (e) {
    el.innerHTML = '<p class="err">' + esc(e.message) + "</p>";
  }
}

function start() {
  $("login").hidden = true;
  $("shell").hidden = false;
  route();
}

function logout() {
  token = "";
  sessionStorage.removeItem("tk");
  $("shell").hidden = true;
  $("login").hidden = false;
}

$("loginForm").addEventListener("submit", async function (ev) {
  ev.preventDefault();
  $("loginErr").textContent = "";
  try {
    const d = await api("/api/v1/admin/login", {
      method: "POST",
      body: {username: $("u").value.trim(), password: $("p").value},
    });
    token = d.access_token;
    sessionStorage.setItem("tk", token);
    $("p").value = "";
    start();
  } catch (e) {
    let m = e.message;
    if (m === "invalid credentials") m = "بيانات الدخول غير صحيحة";
    if (m === "too many attempts") m = "محاولات كثيرة، انتظر 15 دقيقة";
    $("loginErr").textContent = m;
  }
});

$("logout").addEventListener("click", logout);
window.addEventListener("hashchange", route);
window.addEventListener("load", function () { if (token) start(); });

const AR = {
  "uuid already exists": "هذا الـ UUID موجود مسبقاً",
  "uuid not found": "الـ UUID غير موجود",
  "nothing to update": "لا يوجد ما يُحدَّث",
  "license not found": "الكود غير موجود",
  "proxy not found": "البروكسي غير موجود",
  "unauthorized": "غير مصرّح",
};

function tr(m) {
  if (AR[m]) return AR[m];
  if (m.indexOf("uuid is linked") === 0) return "هذا الـ UUID مرتبط بأكواد، لا يمكن حذفه";
  return m;
}
