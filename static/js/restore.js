document.addEventListener("DOMContentLoaded", async () => {
  const list = document.getElementById("postlist");
  if (!list) return;

  const res = await fetch("/api/posts");
  const posts = await res.json();

  list.innerHTML = "";

  for (const p of posts) {
    const article = document.createElement("article");
    article.className = "post-card";

    const meta = document.createElement("div");
    meta.className = "post-meta";

    const user = document.createElement("strong");
    user.className = "post-user";
    user.textContent = `@${p.username}`;

    const date = document.createElement("span");
    date.className = "post-date";
    date.textContent = p.created_at;

    meta.appendChild(user);
    meta.appendChild(date);

    const link = document.createElement("a");
    link.href = `/posts/${p.post_id}`;
    link.textContent = p.post_content;

    const body = document.createElement("p");
    body.className = "post-text";
    body.appendChild(link);

    article.appendChild(meta);
    article.appendChild(body);

    list.appendChild(article);
  }
});