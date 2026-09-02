<?php
/**
 * Desativar W3 Total Cache e limpar cache
 */
$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    die('wp-load.php não encontrado');
}

echo '<h1>Desativando W3 Total Cache</h1>';

// 1. Desativar o plugin
$active_plugins = get_option('active_plugins', array());
$new_plugins = array();
$found = false;

foreach ($active_plugins as $plugin) {
    if (strpos($plugin, 'w3-total-cache') !== false) {
        $found = true;
        echo '<p>❌ Removendo W3 Total Cache do plugins ativos...</p>';
    } else {
        $new_plugins[] = $plugin;
    }
}

if ($found) {
    update_option('active_plugins', $new_plugins);
    echo '<p>✅ W3 Total Cache desativado!</p>';
} else {
    echo '<p>⚠️ W3 Total Cache não estava nos plugins ativos</p>';
}

// 2. Limpar opções de cache do W3 Total Cache
$w3tc_options = array(
    'w3tc_minify',
    'w3tc_page_cache',
    'w3tc_objectcache',
    'w3tc_dbcache',
    'w3tc_browsercache',
    'w3tc_cdn',
    'w3tc_new_relic',
    'w3tc龆shaft',
);

foreach ($w3tc_options as $option) {
    if (get_option($option)) {
        delete_option($option);
        echo '<p>✅ Opção ' . $option . ' removida</p>';
    }
}

// 3. Limpar cache do WordPress
wp_cache_flush();
echo '<p>✅ Cache do WordPress limpo</p>';

// 4. Limpar diretórios de cache manualmente
$cache_dirs = array(
    WP_CONTENT_DIR . '/cache',
    WP_CONTENT_DIR . '/w3tc-config',
    WP_CONTENT_DIR . '/w3-total-cache',
    WP_CONTENT_DIR . '/w3-total-cache-upgrade',
);

foreach ($cache_dirs as $dir) {
    if (is_dir($dir)) {
        echo '<p>⚠️ Diretório de cache encontrado: ' . $dir . '</p>';
        echo '<p>→ Remova manualmente via FTP se necessário</p>';
    }
}

// 5. Verificar .htaccess
echo '<h2>Verificando .htaccess</h2>';
$htaccess = file_get_contents(ABSPATH . '.htaccess');
if (strpos($htaccess, 'w3-total-cache') !== false || strpos($htaccess, 'W3TC') !== false) {
    echo '<p>⚠️ .htaccess contém regras do W3 Total Cache!</p>';
    echo '<p>→ É necessário limpar o .htaccess</p>';
    
    // Limpar .htaccess
    $clean_htaccess = '# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteBase /
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress
';
    file_put_contents(ABSPATH . '.htaccess', $clean_htaccess);
    echo '<p>✅ .htaccess limpo!</p>';
} else {
    echo '<p>✅ .htaccess está limpo</p>';
}

echo '<hr>';
echo '<h2>Cache limpo com sucesso!</h2>';
echo '<p><a href="/">Ver site agora</a></p>';
echo '<p><a href="/wp-admin/plugins.php">Gerenciar plugins</a></p>';
?>
