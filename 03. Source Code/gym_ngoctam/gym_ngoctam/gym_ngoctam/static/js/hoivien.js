// Tương tác màn hình Thêm / Chỉnh sửa hội viên
(function () {
  var dataEl = document.getElementById("goi-data");
  var GOI = dataEl ? JSON.parse(dataEl.textContent) : [];
  function byId(id) { return document.getElementById(id); }

  // ---- Bảng chọn gói
  var sheetGoi = byId("sheet-goi");
  var openGoi = byId("btn-chon-goi");
  if (sheetGoi && openGoi) {
    var hidden = byId("maGoi");
    openGoi.addEventListener("click", function () {
      if (openGoi.disabled) return;
      sheetGoi.querySelectorAll("input[type=radio]").forEach(function (r) { r.checked = r.value === hidden.value; });
      byId("goi-err").hidden = true;
      sheetGoi.hidden = false;
    });
    byId("goi-chon").addEventListener("click", function () {
      var picked = sheetGoi.querySelector("input[type=radio]:checked");
      if (!picked) { byId("goi-err").hidden = false; return; }
      hidden.value = picked.value;
      var g = GOI.find(function (x) { return x.ma === picked.value; });
      byId("goi-label").textContent = g.ten;
      openGoi.classList.add("is-chosen");
      var f = openGoi.closest(".field"); if (f) { f.classList.remove("has-error"); var e = f.querySelector(".err"); if (e) e.remove(); }
      var box = byId("box-dang-ky");
      if (box && g.tieuDe) {
        byId("dk-tieu-de").textContent = g.tieuDe;
        byId("dk-goi-ht").textContent = g.goiHT;
        byId("dk-goi-moi").textContent = g.goiMoi;
        byId("dk-so-ngay").textContent = g.soNgay;
        byId("dk-tien").textContent = g.gia + " VNĐ";
        box.hidden = false;
        var ht = byId("ht-fields"); if (ht) ht.hidden = true;
      }
      sheetGoi.hidden = true;
    });
  }

  // ---- Ảnh hội viên
  var sheetAnh = byId("sheet-anh");
  var openAnh = byId("btn-anh");
  if (sheetAnh && openAnh) {
    openAnh.addEventListener("click", function () { sheetAnh.hidden = false; });
    sheetAnh.querySelectorAll("input[type=file]").forEach(function (inp) {
      inp.addEventListener("change", function () {
        if (!inp.files.length) return;
        sheetAnh.querySelectorAll("input[type=file]").forEach(function (o) { if (o !== inp) o.value = ""; });
        var img = byId("anh-preview");
        img.src = URL.createObjectURL(inp.files[0]);
        img.hidden = false;
        byId("anh-icon").style.display = "none";
        var pick = openAnh.closest(".photo-pick");
        pick.classList.remove("has-error");
        byId("anh-label").innerHTML = 'Đổi ảnh hội viên <span class="star">*</span>';
        sheetAnh.hidden = true;
      });
    });
  }

  // ---- Ô tick Bảo lưu gói tập
  var bl = byId("baoLuu");
  if (bl) {
    var row = bl.closest(".check-row");
    var dangBL = bl.dataset.dangBaoLuu === "1";
    var loi = bl.dataset.loi || "";
    function sync() {
      var errEl = byId("bl-err");
      if (!dangBL && bl.checked && loi) {
        bl.checked = false;
        row.classList.add("is-error");
        errEl.textContent = loi; errEl.hidden = false;
      } else if (errEl && !errEl.dataset.server) {
        row.classList.remove("is-error");
        errEl.hidden = true;
      }
      var boxBL = byId("box-bao-luu"), boxKT = byId("box-ket-thuc");
      if (boxBL) boxBL.hidden = !(bl.checked && !dangBL);
      if (boxKT) boxKT.hidden = !(dangBL && !bl.checked);
      row.classList.toggle("is-active", bl.checked || dangBL);
    }
    bl.addEventListener("change", function () { var e = byId("bl-err"); if (e) delete e.dataset.server; sync(); });
  }

  // ---- Thanh toán: hộp xác nhận hủy
  var huy = byId("btn-huy-tt");
  if (huy) huy.addEventListener("click", function () { byId("modal-huy-tt").hidden = false; });
})();

// Toast tự ẩn
document.querySelectorAll(".toast").forEach(function (t) {
  setTimeout(function () { t.classList.add("hide"); setTimeout(function () { t.remove(); }, 400); }, 3500);
});

// ---- Gợi ý tìm kiếm hội viên (≥ 3 ký tự)
(function () {
  var o = document.getElementById("o-tim"), box = document.getElementById("goi-y");
  if (!o || !box) return;
  var timer, mau = { "Còn hạn": "tag-green", "Đang bảo lưu": "tag-amber" };
  function esc(s) { var d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
  o.addEventListener("input", function () {
    clearTimeout(timer);
    var q = o.value.trim();
    if (q.length < 3) { box.hidden = true; return; }
    timer = setTimeout(function () {
      fetch(o.dataset.goiY + "?q=" + encodeURIComponent(q)).then(function (r) { return r.json(); }).then(function (d) {
        if (!d.ket_qua.length) { box.hidden = true; return; }
        box.innerHTML = d.ket_qua.map(function (h) {
          var av = h.anh ? '<img src="' + h.anh + '" alt="">' : '<svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>';
          return '<a href="' + h.link + '"><div class="row"><div class="avatar">' + av + '</div><div class="grow"><div class="name">' + esc(h.ten) +
            '</div><div class="sub">' + esc(h.goi) + '</div></div><span class="tag ' + (mau[h.trangThai] || "tag-red") + '">' + esc(h.trangThai) + '</span></div></a>';
        }).join("");
        box.hidden = false;
      }).catch(function () { box.hidden = true; });
    }, 250);
  });
  document.addEventListener("click", function (e) { if (!e.target.closest(".search")) box.hidden = true; });
})();

// ---- Lọc danh sách tại chỗ (màn Xóa và Chuyển nhượng)
function locDanhSach(inputId, listId, emptyId) {
  var o = document.getElementById(inputId), ds = document.getElementById(listId);
  if (!o || !ds) return;
  o.addEventListener("input", function () {
    var q = o.value.trim().toLowerCase(), con = 0;
    ds.querySelectorAll(".pick-card").forEach(function (c) {
      var hien = !q || c.dataset.tim.indexOf(q) >= 0;
      c.hidden = !hien; if (hien) con++;
    });
    document.getElementById(emptyId).hidden = con > 0;
  });
}

// ---- Màn Chọn hội viên cần xóa
(function () {
  var f = document.getElementById("form-xoa");
  if (!f) return;
  locDanhSach("loc-xoa", "ds-xoa", "xoa-rong");
  var btn = document.getElementById("btn-xoa");
  function dem() {
    var n = f.querySelectorAll("input[name=chon]:checked").length;
    document.getElementById("dem-chon").textContent = n;
    btn.textContent = "Xóa (" + n + ")";
    btn.disabled = n === 0;
    f.querySelectorAll(".pick-card").forEach(function (c) { c.classList.toggle("is-picked", c.querySelector("input").checked); });
    document.getElementById("xoa-tieu-de").textContent = "Xóa " + n + " hội viên?";
  }
  f.addEventListener("change", dem);
  document.getElementById("chon-tat-ca").addEventListener("click", function () {
    var hien = f.querySelectorAll(".pick-card:not([hidden]) input[name=chon]");
    var tatCa = Array.prototype.every.call(hien, function (i) { return i.checked; });
    hien.forEach(function (i) { i.checked = !tatCa; });
    dem();
  });
  btn.addEventListener("click", function () { document.getElementById("modal-xoa").hidden = false; });
  dem();
})();

// ---- Màn Chuyển nhượng: chọn người nhận
(function () {
  var f = document.getElementById("form-cn");
  if (!f) return;
  locDanhSach("loc-cn", "ds-cn", "cn-rong");
  var btn = document.getElementById("btn-tiep-tuc");
  function sync() {
    var chon = f.querySelector("input[name=nguoi_nhan]:checked");
    var conHien = f.querySelectorAll(".pick-card:not([hidden])").length;
    btn.disabled = !chon || !conHien || chon.closest(".pick-card").hidden;
    f.querySelectorAll(".pick-card").forEach(function (c) { c.classList.toggle("is-picked", c.querySelector("input").checked); });
  }
  f.addEventListener("change", sync);
  f.addEventListener("input", sync);
})();
