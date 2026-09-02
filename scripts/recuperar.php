<?php
$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    echo 'wp-load.php not found';
    exit;
}

echo '<h1>Recuperando WordPress</h1>';

// Listar plugins ativos
$active = get_option('active_plugins', array());
echo '<p>Plugins ativos: ' . count($active) . '</p>';
foreach ($active as $p) {
    echo '<p>- ' . $p . '</p>';
}

// Desativar W3 Total Cache
$new_active = array();
foreach ($active as $p) {
    if (strpos($p, 'w3-total-cache') === false) {
        $new_active[] = $p;
    } else {
        echo '<p>Removendo: ' . $p . '</p>';
    }
}

// Ativar nosso plugin
$adcash = 'adcash-ads/adcash-ads.php';
if (!in_array($adcash, $new_active)) {
    $new_active[] = $adcash;
    echo '<p>Ativando: ' . $adcash . '</p>';
}

update_option('active_plugins', $new_active);

echo '<p style="color:green">Pronto!</p>';
echo '<p><a href="/">Ver site</a></p>';
?>
