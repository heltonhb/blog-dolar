<?php
$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    die('wp-load.php não encontrado');
}

echo '<h1>Diagnóstico do Ad Inserter</h1>';

// 1. Verificar plugin ativo
echo '<h2>1. Plugin Status</h2>';
$active_plugins = get_option('active_plugins');
$ad_inserter_active = false;
foreach ($active_plugins as $plugin) {
    if (strpos($plugin, 'ad-inserter') !== false) {
        $ad_inserter_active = true;
        echo '<p>✅ Plugin Ad Inserter está ATIVO</p>';
        break;
    }
}
if (!$ad_inserter_active) {
    echo '<p>❌ Plugin Ad Inserter NÃO está ativo!</p>';
}

// 2. Verificar configuração
echo '<h2>2. Configuração dos Blocos</h2>';
$ai_config = get_option('ai-insert-ads');
if ($ai_config) {
    echo '<table border="1" cellpadding="5">';
    echo '<tr><th>Bloco</th><th>Nome</th><th>Habilitado</th><th>Código (primeiros 100 chars)</th><th>Páginas</th></tr>';
    
    foreach ($ai_config as $key => $block) {
        if (is_array($block)) {
            $name = isset($block['name']) ? $block['name'] : $key;
            $enabled = isset($block['enabled']) ? $block['enabled'] : 0;
            $code = isset($block['code']) ? $block['code'] : '';
            $pages = isset($block['pages']) ? $block['pages'] : array();
            
            echo '<tr>';
            echo '<td>' . htmlspecialchars($key) . '</td>';
            echo '<td>' . htmlspecialchars($name) . '</td>';
            echo '<td>' . ($enabled ? '✅' : '❌') . '</td>';
            echo '<td><code>' . htmlspecialchars(substr($code, 0, 100)) . '</code></td>';
            echo '<td>' . implode(', ', array_keys($pages)) . '</td>';
            echo '</tr>';
        }
    }
    echo '</table>';
} else {
    echo '<p>❌ Nenhuma configuração encontrada!</p>';
}

// 3. Verificar se o código AdCash está no código fonte
echo '<h2>3. Verificação do Código AdCash</h2>';
if ($ai_config) {
    $found = false;
    foreach ($ai_config as $key => $block) {
        if (is_array($block) && isset($block['code'])) {
            if (strpos($block['code'], 'acscdn.com') !== false) {
                echo '<p>✅ Código AdCash encontrado no bloco ' . htmlspecialchars($key) . '</p>';
                $found = true;
            }
        }
    }
    if (!$found) {
        echo '<p>❌ Código AdCash NÃO encontrado em nenhum bloco!</p>';
        echo '<p>Isso pode significar que o código não foi salvo corretamente.</p>';
    }
}

// 4. Verificar cache
echo '<h2>4. Cache</h2>';
$w3tc_active = false;
foreach ($active_plugins as $plugin) {
    if (strpos($plugin, 'w3-total-cache') !== false) {
        $w3tc_active = true;
        break;
    }
}
echo '<p>W3 Total Cache: ' . ($w3tc_active ? '⚠️ ATIVO (pode causar problemas)' : '✅ Desativado') . '</p>';

// Verificar object cache
if (file_exists(WP_CONTENT_DIR . '/object-cache.php')) {
    echo '<p>⚠️ object-cache.php existe (pode interferir)</p>';
} else {
    echo '<p>✅ object-cache.php não existe</p>';
}

// Verificar advanced-cache
if (file_exists(WP_CONTENT_DIR . '/advanced-cache.php')) {
    echo '<p>⚠️ advanced-cache.php existe (remova!)</p>';
} else {
    echo '<p>✅ advanced-cache.php não existe</p>';
}

// 5. Teste de renderização
echo '<h2>5. Teste de Renderização</h2>';
echo '<p>Testando se o Ad Inserter renderiza código:</p>';

if ($ai_config) {
    foreach ($ai_config as $key => $block) {
        if (is_array($block) && isset($block['code']) && !empty($block['code'])) {
            echo '<div style="border:1px solid #ccc; padding:10px; margin:5px 0; background:#f9f9f9;">';
            echo '<strong>Bloco ' . htmlspecialchars($key) . ':</strong><br>';
            echo '<pre>' . htmlspecialchars($block['code']) . '</pre>';
            echo '</div>';
        }
    }
}

echo '<hr>';
echo '<p><a href="/wp-admin/options-general.php?page=ad-inserter.php">Configurações Ad Inserter</a></p>';
echo '<p><a href="/">Ver site</a></p>';
?>
