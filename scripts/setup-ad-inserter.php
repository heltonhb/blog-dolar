<?php
/**
 * Configurar Ad Inserter Automaticamente
 * 
 * COMO USAR:
 * 1. Upload este arquivo via FTP para htdocs/
 * 2. Acesse: https://tech-tips.byethost4.com/setup-ad-inserter.php
 * 3. Siga as instruções na tela
 * 4. DELETE este arquivo após usar!
 */

$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    echo 'ERRO: wp-load.php não encontrado';
    exit;
}

// Verificar se o Ad Inserter está ativo
if (!is_plugin_active('ad-inserter/ad-inserter.php')) {
    echo '<h2>ERRO: Ad Inserter não está ativo</h2>';
    echo '<p>Vá em Plugins e ative o Ad Inserter primeiro.</p>';
    echo '<p><a href="wp-admin/plugins.php">Ir para Plugins</a></p>';
    exit;
}

// Configuração padrão do Ad Inserter
$default_config = array(
    // Bloco 1 - Header Banner
    'b1' => array(
        'name' => 'Header Banner',
        'enabled' => 1,
        'block' => 1,
        'code' => '<!-- AdCash Header Banner -->
<div style="text-align:center; margin:10px 0;">
<script async data-cfasync="false" src="https://cdn.ad-cash.com/adcash.js"></script>
</div>',
        'pages' => array('home' => 1, 'posts' => 1, 'pages' => 1),
        'alignment' => 1,
        'margin' => '',
        'min_width' => '',
        'min_height' => '',
    ),
    // Bloco 2 - Sidebar Rectangle
    'b2' => array(
        'name' => 'Sidebar Rectangle',
        'enabled' => 1,
        'block' => 2,
        'code' => '<!-- AdCash Sidebar Rectangle -->
<div style="width:300px; text-align:center; margin:15px auto;">
<script async data-cfasync="false" src="https://cdn.ad-cash.com/adcash.js"></script>
</div>',
        'pages' => array('home' => 1, 'posts' => 1, 'pages' => 1),
        'widget' => 1,
    ),
    // Bloco 3 - In-Content Ad
    'b3' => array(
        'name' => 'In-Content Ad',
        'enabled' => 1,
        'block' => 3,
        'code' => '<!-- AdCash In-Content -->
<div style="text-align:center; margin:20px 0; clear:both;">
<script async data-cfasync="false" src="https://cdn.ad-cash.com/adcash.js"></script>
</div>',
        'pages' => array('posts' => 1, 'pages' => 1),
        'insertion' => 2, // Após parágrafo 2
    ),
    // Bloco 4 - Footer Banner
    'b4' => array(
        'name' => 'Footer Banner',
        'enabled' => 1,
        'block' => 4,
        'code' => '<!-- AdCash Footer Banner -->
<div style="text-align:center; margin:20px 0; border-top:1px solid #eee; padding-top:15px;">
<script async data-cfasync="false" src="https://cdn.ad-cash.com/adcash.js"></script>
</div>',
        'pages' => array('home' => 1, 'posts' => 1, 'pages' => 1),
        'insertion' => 6, // Antes de </body>
    ),
);

// Verificar se há formulário enviado
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['setup_ad_inserter'])) {
    
    // Salvar configuração
    $option_name = 'ai-insert-ads';
    update_option($option_name, $default_config);
    
    // Verificar se salvou
    $saved = get_option($option_name);
    
    if ($saved) {
        echo '<h2 style="color: green;">✓ Configuração Aplicada com Sucesso!</h2>';
        echo '<h3>Blocos Configurados:</h3>';
        echo '<ul>';
        for ($i = 1; $i <= 4; $i++) {
            echo '<li>Bloco ' . $i . ': ' . $default_config['b' . $i]['name'] . ' - HABILITADO</li>';
        }
        echo '</ul>';
        echo '<h3>Próximos Passos:</h3>';
        echo '<ol>';
        echo '<li><a href="wp-admin/options-general.php?page=ad-inserter.php">Configure o Ad Inserter</a></li>';
        echo '<li>Crie conta no AdCash: <a href="https://adcash.com/publishers/signup" target="_blank">adcash.com</a></li>';
        echo '<li>Substitua o código placeholder pelo código real do AdCash</li>';
        echo '<li>DELETE este arquivo (setup-ad-inserter.php)</li>';
        echo '</ol>';
    } else {
        echo '<h2 style="color: red;">ERRO: Não foi possível salvar a configuração</h2>';
    }
    exit;
}

// Mostrar formulário de configuração
?>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Setup Ad Inserter - Blog em Dolar</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        h2 { color: #555; }
        .config-box { background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .block { background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #0073aa; }
        .btn { background: #0073aa; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .btn:hover { background: #005177; }
        .warning { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Configurar Ad Inserter</h1>
    
    <div class="warning">
        <strong>⚠ IMPORTANTE:</strong> Após configurar, DELETE este arquivo!
    </div>
    
    <h2>Blocos que serão configurados:</h2>
    
    <div class="config-box">
        <div class="block">
            <h3>Bloco 1: Header Banner</h3>
            <p>Posição: Topo do site (728x90)</p>
            <p>Páginas: Home, Posts, Páginas</p>
        </div>
        
        <div class="block">
            <h3>Bloco 2: Sidebar Rectangle</h3>
            <p>Posição: Barra lateral (300x250)</p>
            <p>Páginas: Home, Posts, Páginas</p>
        </div>
        
        <div class="block">
            <h3>Bloco 3: In-Content Ad</h3>
            <p>Posição: Após o 2º parágrafo</p>
            <p>Páginas: Posts, Páginas</p>
        </div>
        
        <div class="block">
            <h3>Bloco 4: Footer Banner</h3>
            <p>Posição: Rodapé (728x90)</p>
            <p>Páginas: Home, Posts, Páginas</p>
        </div>
    </div>
    
    <form method="POST">
        <input type="hidden" name="setup_ad_inserter" value="1">
        <button type="submit" class="btn">✓ Aplicar Configuração</button>
    </form>
</body>
</html>
