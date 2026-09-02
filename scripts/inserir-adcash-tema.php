<?php
/**
 * Inserir código AdCash diretamente no tema Astra
 * Esta é uma solução alternativa se o Ad Inserter não estiver funcionando
 */
$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    die('wp-load.php não encontrado');
}

echo '<h1>Inserir AdCash no Tema Astra</h1>';

// Código AdCash
$adcash_code = '<script id="aclib" type="text/javascript" src="//acscdn.com/script/aclib.js"></script>
<script type="text/javascript">
    aclib.runAutoTag({
        zoneId: \'suhf5fqztw\',
    });
</script>';

// 1. Inserir no functions.php do tema child (se existir) ou no tema pai
$theme = wp_get_theme();
$theme_name = $theme->get('Template'); // Tema pai
$child_theme = $theme->get('TextDomain'); // Tema child

echo '<h2>1. Verificando tema</h2>';
echo '<p>Tema pai: ' . $theme_name . '</p>';
echo '<p>Tema child: ' . ($child_theme ? $child_theme : 'Nenhum') . '</p>';

// Função para inserir código no header via wp_head
function insert_adcash_in_header() {
    global $adcash_code;
    echo "\n<!-- AdCash Ads Start -->\n";
    echo $adcash_code;
    echo "\n<!-- AdCash Ads End -->\n";
}

// 2. Criar plugin customizado para inserir os anúncios
echo '<h2>2. Criando plugin customizado de anúncios</h2>';

$plugin_dir = WP_CONTENT_DIR . '/plugins/adcash-ads';
$plugin_file = $plugin_dir . '/adcash-ads.php';

// Criar diretório se não existir
if (!is_dir($plugin_dir)) {
    mkdir($plugin_dir, 0755, true);
    echo '<p>✅ Diretório do plugin criado</p>';
}

// Conteúdo do plugin
$plugin_content = '<?php
/**
 * Plugin Name: AdCash Ads Custom
 * Description: Insere código AdCash no site
 * Version: 1.0
 * Author: Blog em Dolar
 */

if (!defined(\'ABSPATH\')) {
    exit;
}

// Código AdCash
$adcash_code = \'<script id="aclib" type="text/javascript" src="//acscdn.com/script/aclib.js"></script>
<script type="text/javascript">
    aclib.runAutoTag({
        zoneId: \'\\\'suhf5fqztw\\\'\',
    });
</script>\';

// Inserir no header (wp_head)
add_action(\'wp_head\', function() {
    global $adcash_code;
    echo "\n<!-- AdCash Ads Start -->\n";
    echo $adcash_code;
    echo "\n<!-- AdCash Ads End -->\n";
}, 1);

// Inserir no footer (wp_footer)
add_action(\'wp_footer\', function() {
    global $adcash_code;
    echo "\n<!-- AdCash Footer Start -->\n";
    echo $adcash_code;
    echo "\n<!-- AdCash Footer End -->\n";
}, 1);

// Inserir após o conteúdo do post
add_filter(\'the_content\', function(\$content) {
    global $adcash_code;
    if (is_single() || is_page()) {
        return \$content . "\n<!-- AdCash In-Content Start -->\n" . $adcash_code . "\n<!-- AdCash In-Content End -->\n";
    }
    return \$content;
}, 99);
?>';

// Salvar o plugin
if (file_put_contents($plugin_file, $plugin_content)) {
    echo '<p>✅ Plugin criado: adcash-ads.php</p>';
} else {
    echo '<p style="color:red">❌ Erro ao criar plugin</p>';
}

// 3. Ativar o plugin
echo '<h2>3. Ativando plugin</h2>';

$active_plugins = get_option('active_plugins', array());
$plugin_path = 'adcash-ads/adcash-ads.php';

if (!in_array($plugin_path, $active_plugins)) {
    $active_plugins[] = $plugin_path;
    update_option('active_plugins', $active_plugins);
    echo '<p>✅ Plugin ativado!</p>';
} else {
    echo '<p>⚠️ Plugin já estava ativo</p>';
}

echo '<hr>';
echo '<h2>Pronto! Código AdCash inserido no site</h2>';
echo '<p>Agora acesse: <a href="/">Ver site</a></p>';
echo '<p>Se ainda não aparecer, verifique: <a href="/verificar-renderizacao.php">/verificar-renderizacao.php</a></p>';
?>
