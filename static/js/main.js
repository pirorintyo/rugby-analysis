function createTextarea(value = "") {
  const wrap = document.createElement("div");
  wrap.className = "field";

  const ta = document.createElement("textarea");
  ta.className = "mini-textarea";
  ta.rows = 3;
  ta.placeholder = "ここに入力";
  ta.value = value;

  const del = document.createElement("button");
  del.type = "button";
  del.className = "del";
  del.textContent = "×";
  del.addEventListener("click", () => wrap.remove());

  wrap.appendChild(ta);
  wrap.appendChild(del);
  return wrap;
}

function addTextareaToStack(stackEl, value = "") {
  // +ボタンの前に差し込む（UI的に下に積む）
  const plusBtn = stackEl.querySelector(".plus");
  const field = createTextarea(value);
  stackEl.insertBefore(field, plusBtn);
}

function buildColumnsJson() {
  const columns = {};
  document.querySelectorAll(".stack[data-key]").forEach(stack => {
    const key = stack.dataset.key; // options / facts_on / facts_off / reasons
    const values = Array.from(stack.querySelectorAll("textarea"))
      .map(t => t.value.trim())
      .filter(v => v.length > 0);
    columns[key] = values;
  });
  return columns;
}

function restoreFromData(data) {
  if (!data) return;

  // 既存をクリア
  document.querySelectorAll(".stack[data-key]").forEach(stack => {
    Array.from(stack.querySelectorAll(".field")).forEach(el => el.remove());
  });

  // columns 復元
  const cols = data.columns || {};
  Object.entries(cols).forEach(([key, arr]) => {
    const stack = document.querySelector(`.stack[data-key="${key}"]`);
    if (!stack) return;
    (arr || []).forEach(v => addTextareaToStack(stack, v));
  });

  // 下部入力復元
  if (data.title != null) document.getElementById("title").value = data.title;
  if (data.post_body != null) document.getElementById("postBody").value = data.post_body;
  if (data.reflection != null) document.getElementById("reflection").value = data.reflection;
}

document.addEventListener("DOMContentLoaded", () => {
  // +ボタン
  document.querySelectorAll(".plus").forEach(btn => {
    btn.addEventListener("click", () => {
      const stackId = btn.dataset.stack;
      const stack = document.getElementById(stackId);
      addTextareaToStack(stack);
    });
  });

  // 詳細ページ復元：テンプレ埋め込みがあれば復元
  const initialScript = document.getElementById("initialData");
  if (initialScript) {
    try {
      const initial = JSON.parse(initialScript.textContent);
      restoreFromData(initial);
    } catch (e) {
      // 何もしない（初期データ無し）
    }
  }

  // 送信前に columns_json を埋める
  const form = document.getElementById("postForm");
  form.addEventListener("submit", (e) => {
    const columns = buildColumnsJson();
    document.getElementById("columnsJson").value = JSON.stringify(columns);

    // ここで簡易バリデーション入れたいなら可能
    // 例：全部空なら止める等
    // if (!Object.values(columns).some(arr => arr.length) && !document.getElementById("postBody").value.trim()) {
    //   e.preventDefault();
    //   alert("何か入力してください");
    // }
  });
});