<?php
$conn = new mysqli(getenv('WP_DB_HOST'), getenv('WP_DB_USER'), getenv('WP_DB_PASS'), getenv('WP_DB_NAME'));
if ($conn->connect_error) { die('ERRO: ' . $conn->connect_error); }

$title = "A Beginner Guide to Understanding Cloud Computing Basics";
$slug = "beginners-guide-to-cloud-computing-basics";
$excerpt = "New to the cloud? Discover cloud computing basics for beginners, including types, services, and why it is changing the tech world.";
$body = file_get_contents('article_body.html');
$body_escaped = $conn->real_escape_string($body);
$now = date('Y-m-d H:i:s');

$sql = "INSERT INTO wpq9_posts (post_title, post_content, post_excerpt, post_status, post_name, post_type, post_date, post_date_gmt, comment_status, ping_status) VALUES ('" . $conn->real_escape_string($title) . "', '" . $body_escaped . "', '" . $conn->real_escape_string($excerpt) . "', 'publish', '" . $conn->real_escape_string($slug) . "', 'post', '$now', '$now', 'open', 'open')";

$conn->query($sql);
$post_id = $conn->insert_id;

echo 'Post publicado! ID: ' . $post_id . '<br>';
echo '<a href="/">Ver site</a>';

$conn->close();
?>