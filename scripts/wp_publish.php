<?php
// Publicar artigo via API do WordPress (executar no servidor)
$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    echo 'wp-load.php not found';
    exit;
}

// Dados do artigo
$post_data = array(
    'post_title' => 'How to Protect Your Digital Privacy Online: The Ultimate Guide',
    'post_content' => '',
    'post_name' => 'how-to-protect-your-digital-privacy-online',
    'post_excerpt' => 'Learn how to protect your digital privacy online with this comprehensive guide. Discover actionable tips to secure your data, block trackers, and browse safely.',
    'post_status' => 'draft',
    'post_author' => 1
);

// Inserir post
$post_id = wp_insert_post($post_data);

if ($post_id) {
    echo 'Post criado com sucesso! ID: ' . $post_id . PHP_EOL;
    echo 'Link: ' . get_permalink($post_id) . PHP_EOL;
    
    // Adicionar tags se existirem
    $tags = 'digital privacy,cybersecurity,online safety,vpn,data protection,privacy tips';
    if ($tags) {
        wp_set_post_tags($post_id, $tags);
    }
} else {
    echo 'Erro ao criar post' . PHP_EOL;
}
?>
