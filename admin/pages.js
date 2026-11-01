pages.dashboard = async function (el) {
  el.textContent = "جارٍ التحميل...";
  const s = await api("/api/v1/admin/stats");
  const cards = [
    ["إجمالي الأكواد", "licenses_total"],
    ["الأكواد النشطة", "licenses_active"],
    ["الأكواد المنتهية", "licenses_expired"],
    ["الأكواد المحظورة", "licenses_banned"],
    ["الأكواد المعطّلة", "licenses_disabled"],
    ["الأجهزة المفعّلة", "devices_active"],
    ["عدد UUIDs", "uuids_total"],
    ["عدد الاشتراكات", "subscriptions_total"],
  ];
  let h = '<div class="grid">';
  cards.forEach(function (c) {
    h += '<div class="card stat"><span class="muted">' + c[0] + "</span><b>" + esc(s[c[1]]) + "</b></div>";
  });
  h += "</div><h3>آخر عمليات التفعيل</h3>";
  if (!s.recent_activations.length) {
    h += '<p class="muted">لا توجد عمليات بعد</p>';
  } else {
    h += "<table><tr><th>رقم الكود</th><th>IP</th><th>الوقت</th></tr>";
    s.recent_activations.forEach(function (r) {
      const t = new Date(r.at).toLocaleString("ar-IQ");
      h += "<tr><td>" + esc(r.license_id) + "</td><td>" + esc(r.ip) + "</td><td>" + esc(t) + "</td></tr>";
    });
    h += "</table>";
  }
  el.innerHTML = h;
};

pages.uuids = async function (el) {
  const rows = await api("/api/v1/admin/uuids");
  let h = '<form id="uf" class="card row">' +
    '<input id="ul" placeholder="وصف (اختياري)">' +
    '<input id="uv" dir="ltr" placeholder="UUID (فارغ = توليد تلقائي)">' +
    "<button>إضافة</button></form>" +
    '<p id="um" class="err"></p>';
  h += '<div class="tw"><table><tr><th>#</th><th>UUID</th><th>الوصف</th><th>الحالة</th><th>الأكواد</th><th></th></tr>';
  rows.forEach(function (u) {
    h += "<tr><td>" + u.id + '</td><td class="ltr">' + esc(u.value) + "</td><td>" + esc(u.label) +
      "</td><td>" + (u.is_active ? "مفعّل" : "معطّل") + "</td><td>" + u.licenses + "</td><td>" +
      '<button class="ghost" data-act="label" data-id="' + u.id + '">وصف</button> ' +
      '<button class="ghost" data-act="toggle" data-id="' + u.id + '" data-on="' + (u.is_active ? 1 : 0) + '">' +
      (u.is_active ? "تعطيل" : "تفعيل") + "</button> " +
      '<button class="danger" data-act="del" data-id="' + u.id + '">حذف</button></td></tr>';
  });
  h += "</table></div>";
  if (!rows.length) h += '<p class="muted">لا توجد UUIDs بعد</p>';
  el.innerHTML = h;
  uuidActions(el, rows);
};

function uuidActions(el, rows) {
  const msg = function (t) { $("um").textContent = t || ""; };
  $("uf").onsubmit = async function (ev) {
    ev.preventDefault();
    msg();
    try {
      await api("/api/v1/admin/uuids", {
        method: "POST",
        body: {label: $("ul").value.trim() || null, value: $("uv").value.trim() || null},
      });
      await pages.uuids(el);
    } catch (e) { msg(e.message); }
  };
  el.onclick = async function (ev) {
    const b = ev.target.closest("button[data-act]");
    if (!b) return;
    msg();
    const id = b.dataset.id;
    const base = "/api/v1/admin/uuids/" + id;
    try {
      if (b.dataset.act === "toggle") {
        await api(base, {method: "PATCH", body: {is_active: b.dataset.on !== "1"}});
      } else if (b.dataset.act === "label") {
        const cur = rows.find(function (r) { return String(r.id) === id; });
        const t = prompt("الوصف الجديد", (cur && cur.label) || "");
        if (t === null) return;
        await api(base, {method: "PATCH", body: {label: t.trim()}});
      } else if (b.dataset.act === "del") {
        if (!confirm("حذف هذا الـ UUID؟")) return;
        await api(base, {method: "DELETE"});
      }
      await pages.uuids(el);
    } catch (e) { msg(e.message); }
  };
}

const ST = {active: "نشط", disabled: "معطّل", banned: "محظور"};

function fmt(x) {
  return x ? new Date(x).toLocaleString("en-GB") : "-";
}

function lb(act, id, text, cls) {
  return '<button class="' + (cls || "ghost") + '" data-act="' + act + '" data-id="' + id + '">' + text + "</button> ";
}

function licForm(uuids) {
  const on = uuids.filter(function (u) { return u.is_active; });
  if (!on.length) return '<p class="err">أضف UUID مفعّلاً أولاً من صفحة UUIDs</p>';
  let h = '<form id="lf" class="card row"><select id="lu">';
  on.forEach(function (u) {
    h += '<option value="' + u.id + '">' + esc(u.label || u.value.slice(0, 8)) + "</option>";
  });
  h += '</select><input id="ld" type="number" min="1" max="3650" value="30" placeholder="الأيام">' +
    '<input id="ln" placeholder="ملاحظة (اسم المشترك)"><button>إنشاء كود</button></form>';
  return h + '<p id="lm" class="err"></p>';
}

function codeBox(code) {
  if (!code) return "";
  return '<div class="card codebox"><b id="cc">' + esc(code) + "</b>" +
    '<button id="cp">نسخ</button><p class="muted">احفظ الكود الآن، لن يظهر مرة أخرى.</p></div>';
}

function licTable(rows, um) {
  let h = '<div class="tw"><table><tr><th>#</th><th>الحالة</th><th>UUID</th><th>ينتهي</th><th>الجهاز</th><th>ملاحظة</th><th></th></tr>';
  rows.forEach(function (l) {
    const sub = l.subscription;
    let st = ST[l.status] || l.status;
    if (l.status === "active" && (!sub || new Date(sub.ends_at) < Date.now())) st = "منتهي";
    const u = um[l.uuid_id];
    let b = "";
    if (l.status === "active") b += lb("disable", l.id, "تعطيل") + lb("ban", l.id, "حظر");
    else b += lb("enable", l.id, "تفعيل");
    b += lb("renew", l.id, "تجديد") + lb("reset", l.id, "فك الجهاز") + lb("log", l.id, "سجل") + lb("del", l.id, "حذف", "danger");
    h += "<tr><td>" + l.id + "</td><td>" + st + "</td><td>" + esc(u ? (u.label || u.value.slice(0, 8)) : l.uuid_id) +
      "</td><td>" + fmt(sub && sub.ends_at) + "</td><td>" + (l.device ? esc(l.device.model || "مرتبط") : "-") +
      "</td><td>" + esc(l.note) + "</td><td>" + b + "</td></tr>";
  });
  h += "</table></div>";
  if (!rows.length) h += '<p class="muted">لا توجد أكواد بعد</p>';
  return h;
}

pages.licenses = async function (el, newCode) {
  const res = await Promise.all([api("/api/v1/admin/licenses"), api("/api/v1/admin/uuids")]);
  const um = {};
  res[1].forEach(function (u) { um[u.id] = u; });
  el.innerHTML = codeBox(newCode) + licForm(res[1]) + licTable(res[0], um) + '<div id="lg" class="lg"></div>';
  licActions(el);
};

function licActions(el) {
  const msg = function (t) { const m = $("lm"); if (m) m.textContent = t || ""; };
  const cp = $("cp");
  if (cp) cp.onclick = async function () {
    try { await navigator.clipboard.writeText($("cc").textContent); cp.textContent = "تم النسخ"; }
    catch (e) { getSelection().selectAllChildren($("cc")); cp.textContent = "حدّد الكود وانسخه"; }
  };
  const lf = $("lf");
  if (lf) lf.onsubmit = async function (ev) {
    ev.preventDefault();
    msg();
    try {
      const d = await api("/api/v1/admin/licenses", {
        method: "POST",
        body: {uuid_id: Number($("lu").value), days: Number($("ld").value), note: $("ln").value.trim() || null},
      });
      await pages.licenses(el, d.code);
    } catch (e) { msg(e.message); }
  };
  el.onclick = async function (ev) {
    const b = ev.target.closest("button[data-act]");
    if (!b) return;
    msg();
    const a = b.dataset.act;
    const base = "/api/v1/admin/licenses/" + b.dataset.id;
    try {
      if (a === "disable" || a === "enable") {
        await api(base + "/status", {method: "POST", body: {status: a === "disable" ? "disabled" : "active"}});
      } else if (a === "ban") {
        if (!confirm("حظر هذا الكود؟")) return;
        await api(base + "/revoke", {method: "POST"});
      } else if (a === "renew") {
        const d = prompt("عدد أيام التجديد", "30");
        if (!d) return;
        await api(base + "/renew", {method: "POST", body: {days: Number(d)}});
      } else if (a === "reset") {
        if (!confirm("فك ارتباط الجهاز بهذا الكود؟")) return;
        await api(base + "/reset-device", {method: "POST"});
      } else if (a === "del") {
        if (!confirm("حذف الكود نهائياً؟")) return;
        await api(base, {method: "DELETE"});
      } else if (a === "log") {
        const rows = await api(base + "/log");
        $("lg").innerHTML = "<h4>سجل الكود " + esc(b.dataset.id) + "</h4>" + (rows.length ? rows.map(function (r) {
          return "<div>" + esc(fmt(r.at)) + " — " + esc(r.action) + " — " + esc(r.ip) + "</div>";
        }).join("") : "لا يوجد سجل");
        return;
      }
      await pages.licenses(el);
    } catch (e) { msg(e.message); }
  };
}

pages.proxies = async function (el) {
  const rows = await api("/api/v1/admin/proxies");
  let h = '<form id="pf" class="card row">' +
    '<input id="pn" placeholder="اسم البروكسي" required>' +
    '<input id="pa" dir="ltr" placeholder="العنوان (IP أو دومين)" required>' +
    "<button>إضافة</button></form><p id=\"pm\" class=\"err\"></p>";
  h += '<div class="tw"><table><tr><th>#</th><th>الاسم</th><th>العنوان</th><th>الحالة</th><th></th></tr>';
  rows.forEach(function (p) {
    h += "<tr><td>" + p.id + "</td><td>" + esc(p.name) + '</td><td class="ltr">' + esc(p.address) +
      "</td><td>" + (p.is_active ? "مفعّل" : "معطّل") + "</td><td>" +
      lb("pname", p.id, "الاسم") + lb("paddr", p.id, "العنوان") + lb("pacc", p.id, "الأكواد") +
      lb("ptog", p.id, p.is_active ? "تعطيل" : "تفعيل") + lb("pdel", p.id, "حذف", "danger") + "</td></tr>";
  });
  h += "</table></div>";
  if (!rows.length) h += '<p class="muted">لا توجد بروكسيات بعد</p>';
  h += '<div id="pacc" class="lg"></div>';
  el.innerHTML = h;
  proxyActions(el, rows);
};

function proxyActions(el, rows) {
  const msg = function (t) { $("pm").textContent = t || ""; };
  $("pf").onsubmit = async function (ev) {
    ev.preventDefault();
    msg();
    try {
      await api("/api/v1/admin/proxies", {
        method: "POST",
        body: {name: $("pn").value.trim(), address: $("pa").value.trim()},
      });
      await pages.proxies(el);
    } catch (e) { msg(e.message); }
  };
  el.onclick = async function (ev) {
    const b = ev.target.closest("button[data-act]");
    if (!b) return;
    msg();
    const id = b.dataset.id;
    const p = rows.find(function (r) { return String(r.id) === id; });
    const base = "/api/v1/admin/proxies/" + id;
    const a = b.dataset.act;
    try {
      if (a === "ptog") {
        await api(base, {method: "PATCH", body: {is_active: !p.is_active}});
      } else if (a === "pname") {
        const t = prompt("الاسم الجديد", p.name);
        if (!t) return;
        await api(base, {method: "PATCH", body: {name: t.trim()}});
      } else if (a === "paddr") {
        const t = prompt("العنوان الجديد", p.address);
        if (!t) return;
        await api(base, {method: "PATCH", body: {address: t.trim()}});
      } else if (a === "pdel") {
        if (!confirm("حذف هذا البروكسي؟")) return;
        await api(base, {method: "DELETE"});
      } else if (a === "pacc") {
        const d = await api(base + "/access");
        const box = $("pacc");
        let hh = "<h4>الأكواد المسموح لها بالبروكسي: " + esc(p.name) + "</h4>" +
          '<p class="muted">إن لم تختر أي كود، تصبح كل الأكواد مسموحة تلقائياً.</p><div class="row">';
        d.licenses.forEach(function (l) {
          const on = d.license_ids.indexOf(l.id) >= 0;
          hh += '<label style="display:flex;gap:6px;align-items:center;min-width:180px">' +
            '<input type="checkbox" class="pacc-cb" value="' + l.id + '"' + (on ? " checked" : "") + ">" +
            "#" + l.id + " — " + esc(l.note || ("UUID " + l.id)) + "</label>";
        });
        hh += '</div><button id="pacc-save">حفظ الصلاحيات</button>';
        box.innerHTML = hh;
        $("pacc-save").onclick = async function () {
          try {
            const ids = Array.prototype.map.call(document.querySelectorAll(".pacc-cb:checked"), function (c) { return Number(c.value); });
            await api(base + "/access", {method: "PUT", body: {license_ids: ids}});
            msg("تم حفظ صلاحيات البروكسي.");
          } catch (e) { msg(e.message); }
        };
        return;
      }
      await pages.proxies(el);
    } catch (e) { msg(e.message); }
  };
}

const TPL = {
  log: {loglevel: "warning"},
  inbounds: [{tag: "socks-in", listen: "127.0.0.1", port: 10808, protocol: "socks", settings: {udp: true}}],
  outbounds: [
    {
      tag: "proxy", protocol: "vless",
      settings: {vnext: [{address: "SERVER", port: 443, users: [{id: "{{UUID}}", encryption: "none"}]}]},
      streamSettings: {network: "tcp", security: "tls", tlsSettings: {serverName: "SNI"}},
    },
    {tag: "proxyfb", protocol: "http", settings: {servers: [{address: "1.1.1.1", port: 80}]}},
    {tag: "direct", protocol: "freedom"},
  ],
};

pages.config = async function (el, flash) {
  const res = await Promise.all([api("/api/v1/admin/config"), api("/api/v1/admin/config/versions")]);
  const d = res[0];
  let h = '<p class="muted">الإصدار المنشور حالياً: ' + (d.current_version || "لا يوجد") + "</p>" +
    '<textarea id="cj" dir="ltr" rows="22" spellcheck="false">' + esc(JSON.stringify(d.draft, null, 2)) + "</textarea>" +
    '<div class="row" style="margin-top:10px"><input id="cn" placeholder="ملاحظة النشر (اختياري)">' +
    '<button id="cs">حفظ المسودة</button><button id="cpb" class="danger">نشر</button>' +
    '<button id="ct" class="ghost">إدراج قالب</button></div>' +
    '<pre id="cm" class="err" style="white-space:pre-wrap">' + esc(flash || "") + "</pre>" +
    "<h3>الإصدارات</h3>";
  h += '<div class="tw"><table><tr><th>#</th><th>الملاحظة</th><th>التاريخ</th><th></th></tr>';
  res[1].forEach(function (v) {
    h += "<tr><td>" + v.version + (v.is_current ? " ✔" : "") + "</td><td>" + esc(v.note) + "</td><td>" +
      esc(fmt(v.created_at)) + "</td><td>" + lb("vview", v.version, "عرض") + lb("vrest", v.version, "استرجاع") + "</td></tr>";
  });
  h += "</table></div>";
  if (!res[1].length) h += '<p class="muted">لا توجد إصدارات منشورة بعد</p>';
  el.innerHTML = h;
  configActions(el);
};

function cfgObj() {
  try { return JSON.parse($("cj").value); }
  catch (e) { throw new Error("JSON غير صالح: " + e.message); }
}

function cfgReport(r) {
  let t = "";
  if (r.errors.length) t += "أخطاء:\n- " + r.errors.join("\n- ");
  if (r.warnings.length) t += (t ? "\n" : "") + "تنبيهات:\n- " + r.warnings.join("\n- ");
  return t;
}

function cfgSave() {
  return api("/api/v1/admin/config", {method: "PUT", body: {config: cfgObj()}});
}

function configActions(el) {
  const msg = function (t) { $("cm").textContent = t || ""; };
  $("ct").onclick = function () {
    if (confirm("استبدال المحتوى بقالب تجريبي؟")) $("cj").value = JSON.stringify(TPL, null, 2);
  };
  $("cs").onclick = async function () {
    msg();
    try { msg("تم حفظ المسودة.\n" + cfgReport(await cfgSave())); } catch (e) { msg(e.message); }
  };
  $("cpb").onclick = async function () {
    msg();
    try {
      const r = await cfgSave();
      if (r.errors.length) { msg(cfgReport(r)); return; }
      if (!confirm("نشر هذا الإعداد؟ سيحصل عليه كل المشتركين.")) return;
      const p = await api("/api/v1/admin/config/publish", {method: "POST", body: {note: $("cn").value.trim() || null}});
      await pages.config(el, "تم النشر: الإصدار " + p.version + "\n" + cfgReport({errors: [], warnings: p.warnings}));
    } catch (e) { msg(e.message); }
  };
  el.onclick = async function (ev) {
    const b = ev.target.closest("button[data-act]");
    if (!b) return;
    msg();
    const v = b.dataset.id;
    try {
      if (b.dataset.act === "vview") {
        const d = await api("/api/v1/admin/config/versions/" + v);
        $("cj").value = JSON.stringify(d.content, null, 2);
        msg("عُرض الإصدار " + v + " في المحرر (لم يُحفظ بعد).");
      } else if (b.dataset.act === "vrest") {
        if (!confirm("نسخ الإصدار " + v + " إلى المسودة؟")) return;
        await api("/api/v1/admin/config/versions/" + v + "/restore", {method: "POST"});
        await pages.config(el, "نُسخ الإصدار " + v + " إلى المسودة. انشره إن أردت.");
      }
    } catch (e) { msg(e.message); }
  };
}

pages.devices = async function (el) {
  const rows = await api("/api/v1/admin/devices");
  let h = '<div class="tw"><table><tr><th>#</th><th>الكود</th><th>الجهاز</th><th>البصمة</th><th>الحالة</th><th>رُبط</th><th>آخر ظهور</th></tr>';
  rows.forEach(function (d) {
    h += "<tr><td>" + d.id + "</td><td>" + d.license_id + "</td><td>" + esc(d.model || "-") +
      '</td><td class="ltr">' + esc(d.fingerprint) + "</td><td>" + (d.is_active ? "مرتبط" : "مفكوك") +
      "</td><td>" + esc(fmt(d.bound_at)) + "</td><td>" + esc(fmt(d.last_seen_at)) + "</td></tr>";
  });
  h += "</table></div>";
  if (!rows.length) h += '<p class="muted">لا توجد أجهزة بعد</p>';
  el.innerHTML = h;
};

pages.logs = async function (el) {
  const rows = await api("/api/v1/admin/audit-logs?limit=200");
  let h = '<div class="tw"><table><tr><th>الوقت</th><th>العملية</th><th>الكيان</th><th>IP</th><th>تفاصيل</th></tr>';
  rows.forEach(function (r) {
    const det = r.details ? JSON.stringify(r.details).slice(0, 80) : "";
    h += "<tr><td>" + esc(fmt(r.at)) + '</td><td class="ltr">' + esc(r.action) + "</td><td>" +
      esc((r.entity_type || "") + " " + (r.entity_id || "")) + '</td><td class="ltr">' + esc(r.ip) +
      '</td><td class="ltr">' + esc(det) + "</td></tr>";
  });
  h += "</table></div>";
  el.innerHTML = h;
};

pages.account = async function (el) {
  const me = await api("/api/v1/admin/me");
  el.innerHTML = '<form id="af" class="card" style="max-width:360px;display:grid;gap:10px">' +
    "<h3>حساب المدير: " + esc(me.username) + "</h3>" +
    '<input id="a0" type="password" placeholder="كلمة المرور الحالية" autocomplete="current-password" required>' +
    '<input id="a1" type="password" placeholder="كلمة المرور الجديدة (12 خانة على الأقل)" autocomplete="new-password" required>' +
    '<input id="a2" type="password" placeholder="تأكيد كلمة المرور الجديدة" autocomplete="new-password" required>' +
    '<button>تغيير كلمة المرور</button><p id="am" class="err"></p></form>';
  $("af").onsubmit = async function (ev) {
    ev.preventDefault();
    const m = $("am");
    m.className = "err";
    m.textContent = "";
    if ($("a1").value !== $("a2").value) { m.textContent = "تأكيد كلمة المرور غير مطابق"; return; }
    if ($("a1").value.length < 12) { m.textContent = "كلمة المرور أقل من 12 خانة"; return; }
    try {
      await api("/api/v1/admin/password", {method: "POST", body: {current: $("a0").value, new: $("a1").value}});
      $("af").reset();
      m.className = "muted";
      m.textContent = "تم تغيير كلمة المرور.";
    } catch (e) {
      m.textContent = e.message === "wrong password" ? "كلمة المرور الحالية خاطئة" : e.message;
    }
  };
};

/* ============================ Subscriptions ============================ */

const SUBST = {active: "نشط", stopped: "موقوف", banned: "محظور"};

pages.subscriptions = async function (el) {
  const res = await Promise.all([
    api("/api/v1/admin/subscriptions"),
    api("/api/v1/admin/licenses"),
  ]);
  const subs = res[0];
  const lics = res[1];
  let h = '<form id="sf" class="card row"><select id="sl">';
  lics.forEach(function (l) {
    h += '<option value="' + l.id + '">#' + l.id + " — " + esc(l.note || ("UUID " + l.uuid_id)) + "</option>";
  });
  h += '</select><input id="sd" type="number" min="1" max="3650" value="30" placeholder="الأيام">' +
    '<button>إضافة اشتراك</button></form><p id="sm" class="err"></p>';
  h += '<div class="tw"><table><tr><th>#</th><th>الكود</th><th>UUID</th><th>الحالة</th><th>يبدأ</th><th>ينتهي</th><th></th></tr>';
  subs.forEach(function (s) {
    const st = SUBST[s.status] || s.status;
    const expired = new Date(s.ends_at) < Date.now();
    let b = "";
    if (s.status === "active") b += lb("sstop", s.id, "إيقاف") + lb("sban", s.id, "حظر");
    else b += lb("sact", s.id, "تفعيل");
    b += lb("sext", s.id, "تمديد") + lb("sdel", s.id, "حذف", "danger");
    h += "<tr><td>" + s.id + "</td><td>#" + s.license_id + " " + esc(s.license_note || "") +
      '</td><td class="ltr">' + esc((s.uuid || "").slice(0, 8)) + "</td><td>" + st +
      (expired && s.status === "active" ? " (منتهي)" : "") + "</td><td>" + esc(fmt(s.starts_at)) +
      "</td><td>" + esc(fmt(s.ends_at)) + "</td><td>" + b + "</td></tr>";
  });
  h += "</table></div>";
  if (!subs.length) h += '<p class="muted">لا توجد اشتراكات بعد</p>';
  el.innerHTML = h;
  subActions(el);
};

function subActions(el) {
  const msg = function (t) { const m = $("sm"); if (m) m.textContent = t || ""; };
  $("sf").onsubmit = async function (ev) {
    ev.preventDefault();
    msg();
    try {
      await api("/api/v1/admin/subscriptions", {
        method: "POST",
        body: {license_id: Number($("sl").value), days: Number($("sd").value)},
      });
      await pages.subscriptions(el);
    } catch (e) { msg(e.message); }
  };
  el.onclick = async function (ev) {
    const b = ev.target.closest("button[data-act]");
    if (!b) return;
    msg();
    const a = b.dataset.act;
    const base = "/api/v1/admin/subscriptions/" + b.dataset.id;
    try {
      if (a === "sact" || a === "sstop" || a === "sban") {
        const st = a === "sact" ? "active" : a === "sstop" ? "stopped" : "banned";
        await api(base + "/status", {method: "POST", body: {status: st}});
      } else if (a === "sext") {
        const d = prompt("عدد أيام التمديد", "30");
        if (!d) return;
        await api(base + "/extend", {method: "POST", body: {days: Number(d)}});
      } else if (a === "sdel") {
        if (!confirm("حذف هذا الاشتراك؟")) return;
        await api(base, {method: "DELETE"});
      }
      await pages.subscriptions(el);
    } catch (e) { msg(e.message); }
  };
}

/* ============================ Xray servers ============================ */

pages.xray = async function (el) {
  const rows = await api("/api/v1/admin/xray/servers");
  let h = '<form id="xf" class="card row">' +
    '<input id="xn" placeholder="اسم السيرفر" required>' +
    '<input id="xa" dir="ltr" placeholder="عنوان الاتصال (IP/domain)" required>' +
    '<input id="xp" type="number" value="443" placeholder="المنفذ">' +
    '<input id="xu" dir="ltr" placeholder="https://agent-host:8443" required>' +
    '<input id="xt" dir="ltr" placeholder="Agent token" required>' +
    "<button>إضافة سيرفر</button></form><p id=\"xm\" class=\"err\"></p>";
  h += '<div class="tw"><table><tr><th>#</th><th>الاسم</th><th>العنوان</th><th>الوكيل</th><th>الحالة</th><th>الإصدار</th><th></th></tr>';
  rows.forEach(function (s) {
    h += "<tr><td>" + s.id + "</td><td>" + esc(s.name) + '</td><td class="ltr">' + esc(s.address + ":" + s.port) +
      '</td><td class="ltr">' + esc(s.agent_url) + "</td><td>" + esc(s.status) +
      "</td><td>" + esc(s.xray_version || "-") + "</td><td>" +
      lb("xcheck", s.id, "فحص") + lb("xcfg", s.id, "إعداد") + lb("xapply", s.id, "تطبيق") +
      lb("xsync", s.id, "مزامنة") + lb("xusers", s.id, "مستخدمون") + lb("xdel", s.id, "حذف", "danger") +
      "</td></tr>";
  });
  h += "</table></div>";
  if (!rows.length) h += '<p class="muted">لا توجد سيرفرات Xray بعد</p>';
  h += '<div id="xpanel" class="lg"></div>';
  el.innerHTML = h;
  xrayActions(el, rows);
};

function xrayActions(el, rows) {
  const msg = function (t) { const m = $("xm"); if (m) m.textContent = t || ""; };
  $("xf").onsubmit = async function (ev) {
    ev.preventDefault();
    msg();
    try {
      await api("/api/v1/admin/xray/servers", {
        method: "POST",
        body: {
          name: $("xn").value.trim(),
          address: $("xa").value.trim(),
          port: Number($("xp").value) || 443,
          agent_url: $("xu").value.trim(),
          agent_token: $("xt").value.trim(),
        },
      });
      await pages.xray(el);
    } catch (e) { msg(e.message); }
  };
  el.onclick = async function (ev) {
    const b = ev.target.closest("button[data-act]");
    if (!b) return;
    msg();
    const id = b.dataset.id;
    const a = b.dataset.act;
    const base = "/api/v1/admin/xray/servers/" + id;
    const panel = $("xpanel");
    try {
      if (a === "xcheck") {
        const r = await api(base + "/check", {method: "POST"});
        msg("السيرفر متصل — " + (r.xray_version || "") + " — الخدمة: " + (r.service || "?"));
      } else if (a === "xdel") {
        if (!confirm("حذف هذا السيرفر؟")) return;
        await api(base, {method: "DELETE"});
        await pages.xray(el);
      } else if (a === "xapply") {
        if (!confirm("تطبيق الإعداد المحفوظ وإعادة تشغيل Xray؟")) return;
        const r = await api(base + "/apply", {method: "POST"});
        msg("تم التطبيق — إصدار " + r.version);
      } else if (a === "xsync") {
        const r = await api(base + "/sync-users", {method: "POST"});
        msg("تمت مزامنة " + r.synced + " مستخدم");
      } else if (a === "xcfg") {
        const d = await api(base + "/config");
        panel.innerHTML = "<h4>إعداد سيرفر Xray #" + esc(id) + "</h4>" +
          '<textarea id="xcj" dir="ltr" rows="20" spellcheck="false">' +
          esc(JSON.stringify(d.config || {log: {loglevel: "warning"}, inbounds: [], outbounds: []}, null, 2)) +
          '</textarea><div class="row" style="margin-top:10px"><button id="xcs">حفظ والتحقق</button>' +
          '<button id="xca">حفظ وتطبيق</button></div><p id="xcm" class="err"></p>';
        $("xcs").onclick = async function () {
          try {
            await api(base + "/config", {method: "PUT", body: {config: JSON.parse($("xcj").value)}});
            $("xcm").textContent = "تم الحفظ والتحقق بنجاح.";
          } catch (e) { $("xcm").textContent = e.message; }
        };
        $("xca").onclick = async function () {
          try {
            await api(base + "/config", {method: "PUT", body: {config: JSON.parse($("xcj").value)}});
            const r = await api(base + "/apply", {method: "POST"});
            $("xcm").textContent = "تم التطبيق — إصدار " + r.version;
          } catch (e) { $("xcm").textContent = e.message; }
        };
      } else if (a === "xusers") {
        const res = await Promise.all([api(base + "/users"), api("/api/v1/admin/uuids")]);
        const users = res[0];
        const uuids = res[1];
        let h = "<h4>مستخدمو السيرفر #" + esc(id) + "</h4>" +
          '<div class="row"><select id="xus">';
        uuids.forEach(function (u) {
          h += '<option value="' + u.id + '">' + esc(u.label || u.value.slice(0, 8)) + "</option>";
        });
        h += '</select><input id="xue" placeholder="email (اختياري)"><button id="xua">إضافة</button></div>' +
          '<div class="tw"><table><tr><th>#</th><th>UUID</th><th>Email</th><th>الحالة</th><th></th></tr>';
        users.forEach(function (u) {
          h += "<tr><td>" + u.id + '</td><td class="ltr">' + esc(u.uuid) + "</td><td>" + esc(u.email || "-") +
            "</td><td>" + (u.is_enabled ? "مفعّل" : "معطّل") + "</td><td>" +
            lb("xutog", u.id, u.is_enabled ? "تعطيل" : "تفعيل") + lb("xudel", u.id, "حذف", "danger") +
            "</td></tr>";
        });
        h += "</table></div>";
        panel.innerHTML = h;
        $("xua").onclick = async function () {
          try {
            await api(base + "/users", {method: "POST", body: {uuid_id: Number($("xus").value), email: $("xue").value.trim() || null}});
            await pages.xray(el);
            const b2 = document.querySelector('button[data-act="xusers"][data-id="' + id + '"]');
            if (b2) b2.click();
          } catch (e) { msg(e.message); }
        };
        panel.onclick = async function (ev2) {
          const bb = ev2.target.closest("button[data-act]");
          if (!bb) return;
          const ubase = base + "/users/" + bb.dataset.id;
          try {
            if (bb.dataset.act === "xudel") {
              if (!confirm("حذف المستخدم؟")) return;
              await api(ubase, {method: "DELETE"});
            } else if (bb.dataset.act === "xutog") {
              const u = users.find(function (x) { return String(x.id) === bb.dataset.id; });
              await api(ubase, {method: "PATCH", body: {is_enabled: !u.is_enabled}});
            }
            const b2 = document.querySelector('button[data-act="xusers"][data-id="' + id + '"]');
            if (b2) b2.click();
          } catch (e) { msg(e.message); }
        };
      }
    } catch (e) { msg(e.message); }
  };
}
