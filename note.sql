--更新
UPDATE posts
SET evaluation_comment = ?, post_content = ?
WHERE id = ? AND user_id = ?;

--削除
DELETE FROM posts
WHERE id = ? AND user_id = ?;