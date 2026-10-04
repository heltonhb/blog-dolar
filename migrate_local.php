<?php
// Change to the htdocs directory where wp-load.php is located
chdir(__DIR__ . '/htdocs');
// Load wp-config.php and wp-load.php
require_once 'wp-config.php';
require_once 'wp-load.php';
global $wpdb;
// Check if wpdb is set
if (!isset($wpdb)) {
    die("wpdb not set\n");
}
echo "Connected to database: " . $wpdb->dbname . "\n";
$antigo = 'https://tech-tips.ct.ws';
$novo = 'https://techtips.dpdns.org';
// 1. Update siteurl and home
echo "Updating siteurl and home...\n";
$wpdb->query($wpdb->prepare(
    "UPDATE {$wpdb->options} SET option_value = %s WHERE option_name IN ('siteurl', 'home')",
    $novo
));
echo "Done.\n";
// 2. Search-replace in posts (content and guid)
echo "Updating posts content and guid...\n";
$wpdb->query("UPDATE {$wpdb->posts} SET post_content = REPLACE(post_content, '$antigo', '$novo')");
$wpdb->query("UPDATE {$wpdb->posts} SET guid = REPLACE(guid, '$antigo', '$novo')");
echo "Done.\n";
// 3. Postmeta
echo "Updating postmeta...\n";
$wpdb->query("UPDATE {$wpdb->postmeta} SET meta_value = REPLACE(meta_value, '$antigo', '$novo') WHERE meta_value LIKE '%tech-tips.ct.ws%'");
echo "Done.\n";
// 4. Options
echo "Updating options...\n";
$wpdb->query("UPDATE {$wpdb->options} SET option_value = REPLACE(option_value, '$antigo', '$novo') WHERE option_value LIKE '%tech-tips.ct.ws%'");
echo "Done.\n";
// Show before and after counts for verification
echo "== Verification ==\n";
foreach (array('siteurl', 'home') as $opt) {
    echo $opt . ': ' . get_option($opt) . "\n";
}
$resto = $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_content LIKE '%tech-tips.ct.ws%' OR guid LIKE '%tech-tips.ct.ws%'");
echo "posts ainda com ct.ws: $resto\n";
echo "FIM\n";
?>