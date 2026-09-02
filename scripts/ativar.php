<?php
$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    echo 'wp-load.php not found';
    exit;
}

$active = get_option('active_plugins', array());
$plugin = 'adcash-ads/adcash-ads.php';

if (!in_array($plugin, $active)) {
    $active[] = $plugin;
    update_option('active_plugins', $active);
}

echo 'Plugin ativo: ';
var_dump(in_array($plugin, get_option('active_plugins', array())));
?>
