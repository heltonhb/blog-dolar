<?php
$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    die('wp-load.php nao encontrado');
}

echo '<h1>Ativando plugin AdCash</h1>';

// Verificar se o plugin existe
$plugin_file = WP_CONTENT_DIR . '/plugins/adcash-ads/adcash-ads.php';
if (file_exists($plugin_file)) {
    echo '<p>Plugin encontrado: adcash-ads.php</p>';
    
    // Ativar o plugin
    $active_plugins = get_option('active_plugins', array());
    $plugin_path = 'adcash-ads/adcash-ads.php';
    
    if (!in_array($plugin_path, $active_plugins)) {
        $active_plugins[] = $plugin_path;
        update_option('active_plugins', $active_plugins);
        echo '<p style="color:green">Plugin ATIVADO com sucesso!</p>';
    } else {
        echo '<p>Plugin ja estava ativo</p>';
    }
    
    // Verificar se esta ativo
    $active_plugins = get_option('active_plugins', array());
    if (in_array($plugin_path, $active_plugins)) {
        echo '<p style="color:green">Confirmado: Plugin esta ATIVO</p>';
    } else {
        echo '<p style="color:red">ERRO: Plugin NAO esta ativo</p>';
    }
} else {
    echo '<p style="color:red">Plugin nao encontrado!</p>';
}

echo '<hr>';
echo '<p><a href="/">Ver site</a></p>';
echo '<p><a href="/wp-admin/plugins.php">Gerenciar plugins</a></p>';
?>
