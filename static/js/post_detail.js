function createReadonlyTextarea(value = "") {
  const wrap = document.createElement("div");
  wrap.className = "field readonly-field";

  const ta = document.createElement("textarea");
  ta.className = "mini-textarea";
  ta.rows = 3;
  ta.value = value;
  ta.readOnly = true;

  wrap.appendChild(ta);
  return wrap;
}

function addReadonlyToStack(stackEl, value = "") {
  const field = createReadonlyTextarea(value);
  stackEl.appendChild(field);
}

document.addEventListener("DOMContentLoaded", () => {
  const script = document.getElementById("detailData");
  if (!script) return;

  let data = null;
  try {
    data = JSON.parse(script.textContent);
  } catch (e) {
    return;
  }
  if (!data) return;

  // 下部表示
  const titleEl = document.getElementById("title");
  const reflectionEl = document.getElementById("reflection");
  if (titleEl && data.title != null) titleEl.value = data.title;
  if (reflectionEl && data.reflection != null) reflectionEl.value = data.reflection;

  // 盤面復元
  const cols = data.columns || {};
  document.querySelectorAll(".stack[data-key]").forEach(stack => {
    const key = stack.dataset.key;
    const arr = cols[key] || [];
    stack.innerHTML = "";
    (arr || []).forEach(v => addReadonlyToStack(stack, v));
  });
});