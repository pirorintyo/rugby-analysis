SELECT
  p.id AS post_id,
  u.username,
  p.created_at,
  p.post_content
FROM posts p
JOIN users u ON u.id = p.user_id
ORDER BY p.created_at DESC;

SELECT
  p.id AS post_id,
  u.username,
  p.created_at,
  p.evaluation_comment,
  p.post_content,
  e.entry_type,
  e.position,
  e.body
FROM posts p
JOIN users u ON u.id = p.user_id
LEFT JOIN post_entries e ON e.post_id = p.id
WHERE p.id = ?
ORDER BY e.entry_type, e.position;

