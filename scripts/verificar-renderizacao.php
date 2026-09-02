<?php
/**
 * Verificar se o código AdCash está no HTML renderizado
 */
$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    die('wp-load.php não encontrado');
}

echo '<h1>Verificação de Renderização do AdCash</h1>';

// Iniciar buffer para capturar a saída
ob_start();

// Carregar o tema e renderizar uma página
include(ABSPATH . 'wp-blog-header.php');

// Capturar o HTML gerado
$html = ob_get_clean();

echo '<h2>1. Procurando código AdCash no HTML</h2>';

// Procurar por diferentes variações do código AdCash
$search_terms = array(
    'acscdn.com' => 'Script ACLIB (acscdn.com)',
    'aclib.js' => 'Arquivo aclib.js',
    'aclib.runAutoTag' => 'Função runAutoTag',
    'suhf5fqztw' => 'Zone ID do AdCash',
    'adcash' => 'Menção a AdCash',
    'ad-inserter' => 'Marca do Ad Inserter',
);

$found_any = false;
foreach ($search_terms as $term => $description) {
    if (strpos($html, $term) !== false) {
        echo '<p>✅ ' . $description . ' encontrado no HTML</p>';
        $found_any = true;
    } else {
        echo '<p>❌ ' . $description . ' NÃO encontrado no HTML</p>';
    }
}

if (!$found_any) {
    echo '<h2 style="color:red">PROBLEMA: Nenhum código de anúncio encontrado!</h2>';
    echo '<p>O Ad Inserter está configurado, mas não está inserindo o código no HTML.</p>';
}

echo '<h2>2. Verificar configuração do Ad Inserter</h2>';

// Verificar se o Ad Inserter está configurado para inserir no header
$ai_config = get_option('ai-insert-ads', array());
if (!empty($ai_config)) {
    echo '<p>Configuração encontrada com ' . count($ai_config) . ' blocos</p>';
    
    // Verificar se há blocos habilitados para a página atual
    $enabled_blocks = 0;
    foreach ($ai_config as $key => $block) {
        if (isset($block['enabled']) && $block['enabled'] == 1) {
            $enabled_blocks++;
        }
    }
    echo '<p>Blocos habilitados: ' . $enabled_blocks . '</p>';
} else {
    echo '<p style="color:red">Nenhuma configuração do Ad Inserter encontrada!</p>';
}

echo '<h2>3. Teste Manual - Inserir código no header</h2>';
echo '<p>Se o Ad Inserter não estiver funcionando, podemos inserir o código diretamente no tema.</p>';

// Verificar se o código está no header do tema
$theme_header = file_get_contents(get_stylesheet_directory() . '/header.php');
if (strpos($theme_header, 'acscdn.com') !== false || strpos($theme_header, 'aclib') !== false) {
    echo '<p>✅ Código AdCash encontrado no header.php do tema</p>';
} else {
    echo '<p>❌ Código AdCash NÃO encontrado no header.php do tema</p>';
    echo '<p>→ O Ad Inserter deveria inserir automaticamente, mas pode não estar funcionando.</p>';
}

echo '<hr>';
echo '<h2>Solução: Inserir código diretamente no tema</h2>';
echo '<p>Se os anúncios não aparecerem, precisamos inserir o código manualmente no tema Astra.</p>';
echo '<p>Execute: <a href="/inserir-adcash-tema.php">/inserir-adcash-tema.php</a></p>';
?>
