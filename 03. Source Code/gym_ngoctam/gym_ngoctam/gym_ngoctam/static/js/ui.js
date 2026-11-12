// Phòng Gym NT – tương tác giao diện dùng chung
document.addEventListener("click", function (e) {
  // Mở / đóng menu
  if (e.target.closest("[data-menu-toggle]")) {
    document.body.classList.toggle("menu-open");
    return;
  }
  if (e.target.closest(".menu-backdrop")) {
    document.body.classList.remove("menu-open");
    return;
  }
  // Đóng hộp thoại
  var closeBtn = e.target.closest("[data-close]");
  if (closeBtn) {
    var ov = closeBtn.closest(".overlay");
    if (ov) ov.hidden = true;
    return;
  }
  // Mở bottom sheet
  var opener = e.target.closest("[data-open-sheet]");
  if (opener) {
    var sheet = document.getElementById(opener.dataset.openSheet);
    if (sheet) {
      var hidden = document.getElementById(sheet.dataset.input);
      sheet.querySelectorAll("input[type=radio]").forEach(function (r) { r.checked = r.value === hidden.value; });
      sheet.hidden = false;
    }
    return;
  }
  // Nút "Chọn" trong bottom sheet
  var choose = e.target.closest("[data-sheet-choose]");
  if (choose) {
    var sh = choose.closest(".overlay");
    var picked = sh.querySelector("input[type=radio]:checked");
    if (picked) {
      document.getElementById(sh.dataset.input).value = picked.value;
      document.getElementById(sh.dataset.label).textContent = sh.dataset.prefix + picked.dataset.text;
    }
    sh.hidden = true;
  }
});

// Công tắc trạng thái: đổi chữ "Đang bán" / "Ngừng bán"
document.querySelectorAll("[data-switch-label]").forEach(function (input) {
  var label = document.getElementById(input.dataset.switchLabel);
  function sync() {
    label.textContent = input.checked ? input.dataset.on : input.dataset.off;
    label.classList.toggle("off", !input.checked);
  }
  input.addEventListener("change", sync);
});

// Ô chọn có data-sheet → mở bảng chọn từ dưới lên (Hủy / Xong) như Figma
(function () {
  var sels = document.querySelectorAll("select[data-sheet]");
  if (!sels.length) return;
  var ov = document.createElement("div");
  ov.className = "overlay sheet-overlay"; ov.hidden = true;
  ov.innerHTML = '<div class="sheet"><div class="grabber"></div><div class="picker-head">' +
    '<button type="button" class="btn btn-outline" data-huy>Hủy</button><h3></h3>' +
    '<button type="button" class="btn btn-primary" data-xong>Xong</button></div><div class="picker-list"></div></div>';
  document.body.appendChild(ov);
  var cur = null, val = null;
  function open(sel) {
    cur = sel; val = sel.value;
    ov.querySelector("h3").textContent = sel.dataset.sheet;
    var list = ov.querySelector(".picker-list");
    list.innerHTML = "";
    Array.prototype.forEach.call(sel.options, function (o) {
      if (o.value === "") return;
      var b = document.createElement("button");
      b.type = "button"; b.textContent = o.text; b.dataset.v = o.value;
      if (o.value === val) b.className = "on";
      b.addEventListener("click", function () {
        val = o.value;
        list.querySelectorAll("button").forEach(function (x) { x.classList.toggle("on", x === b); });
      });
      list.appendChild(b);
    });
    ov.hidden = false;
    var on = list.querySelector(".on"); if (on) on.scrollIntoView({ block: "center" });
  }
  sels.forEach(function (s) {
    s.addEventListener("mousedown", function (e) { e.preventDefault(); open(s); });
    s.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(s); } });
  });
  ov.querySelector("[data-huy]").addEventListener("click", function () { ov.hidden = true; });
  ov.querySelector("[data-xong]").addEventListener("click", function () {
    if (cur && val !== null) { cur.value = val; cur.dispatchEvent(new Event("change", { bubbles: true })); }
    ov.hidden = true;
  });
  ov.addEventListener("click", function (e) { if (e.target === ov) ov.hidden = true; });
})();

// Thông báo sau khi bấm Xuất báo cáo
document.querySelectorAll("[data-xuat]").forEach(function (a) {
  a.addEventListener("click", function () {
    var t = document.getElementById("toast-xuat");
    if (!t) return;
    t.hidden = false; t.firstElementChild.classList.remove("hide");
    setTimeout(function () { t.firstElementChild.classList.add("hide"); setTimeout(function () { t.hidden = true; }, 400); }, 3000);
  });
});
