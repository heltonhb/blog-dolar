<?php
/**
 * Configurar Ad Inserter com código REAL do AdCash
 * 
 * Execute: https://tech-tips.byethost4.com/config-ad-cash.php
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
    echo '<p><a href="wp-admin/plugins.php">Ative o plugin</a></p>';
    exit;
}

// Código REAL do AdCash
$adcash_lib = '<script id="aclib" type="text/javascript" src="//acscdn.com/script/aclib.js"></script>';

$adcash_tag = '<script type="text/javascript">
    aclib.runAutoTag({
        zoneId: \'suhf5fqztw\',
    });
</script>';

// Código completo (lib + tag)
$adcash_full = $adcash_lib . "\n" . $adcash_tag;

// Configuração com código REAL do AdCash
$config = array(
    // Bloco 1 - Header Banner
    'b1' => array(
        'name' => 'Header Banner',
        'enabled' => 1,
        'block' => 1,
        'code' => '<!-- AdCash Header -->' . "\n" . $adcash_full,
        'pages' => array('home' => 1, 'posts' => 1, 'pages' => 1),
        'alignment' => 1,
    ),
    // Bloco 2 - Sidebar Rectangle
    'b2' => array(
        'name' => 'Sidebar Rectangle',
        'enabled' => 1,
        'block' => 2,
        'code' => '<!-- AdCash Sidebar -->' . "\n" . $adcash_full,
        'pages' => array('home' => 1, 'posts' => 1, 'pages' => 1),
    ),
    // Bloco 3 - In-Content
    'b3' => array(
        'name' => 'In-Content Ad',
        'enabled' => 1,
        'block' => 3,
        'code' => '<!-- AdCash In-Content -->' . "\n" . $adcash_full,
        'pages' => array('posts' => 1, 'pages' => 1),
        'insertion' => 2,
    ),
    // Bloco 4 - Footer
    'b4' => array(
        'name' => 'Footer Banner',
        'enabled' => 1,
        'block' => 4,
        'code' => '<!-- AdCash Footer -->' . "\n" . $adcash_full,
        'pages' => array('home' => 1, 'posts' => 1, 'pages' => 1),
        'insertion' => 6,
    ),
);

// Processar formulário
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['config_adcash'])) {
    
    update_option('ai-insert-ads', $config);
    $saved = get_option('ai-insert-ads');
    
    if ($saved) {
        echo '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Sucesso</title></head><body>';
        echo '<h1 style="color:green">✓ AdCash Configurado com Sucesso!</h1>';
        echo '<h2>Código AdCash instalado em 4 blocos:</h2>';
        echo '<ul>';
        echo '<li>✓ Bloco 1: Header Banner</li>';
        echo '<li>✓ Bloco 2: Sidebar Rectangle</li>';
        echo '<li>✓ Bloco 3: In-Content Ad</li>';
        echo '<li>✓ Bloco 4: Footer Banner</li>';
        echo '</ul>';
        echo '<h2>Zone ID: suhf5fqztw</h2>';
        echo '<h3>Próximos passos:</h3>';
        echo '<ol>';
        echo '<li><a href="https://tech-tips.byethost4.com" target="_blank">Verificar o site</a></li>';
        echo '<li><a href="wp-admin/options-general.php?page=ad-inserter.php">Configurações Ad Inserter</a></li>';
        echo '<li>DELETE este arquivo: config-ad-cash.php</li>';
        echo '</ol>';
        echo '</body></html>';
    } else {
        echo '<h1 style="color:red">ERRO ao salvar configuração</h1>';
    }
    exit;
}
?>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Configurar AdCash no Ad Inserter</title>
    <style>
        body { font-family: Arial; max-width: 700px; margin: 50px auto; padding: 20px; }
        .code { background: #f5f5f5; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 12px; overflow-x: auto; margin: 10px 0; }
        .btn { background: #28a745; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 18px; }
        .btn:hover { background: #218838; }
    </style>
</head>
<body>
    <h1>Configurar AdCash no Ad Inserter</h1>
    
    <h2>Código que será instalado:</h2>
    
    <h3>Step 1 - Library:</h3>
    <div class="code">
        &lt;script id="aclib" type="text/javascript" src="//acscdn.com/script/aclib.js"&gt;&lt;/script&gt;
    </div>
    
    <h3>Step 2 - Tag:</h3>
    <div class="code">
        &lt;script type="text/javascript"&gt;<br>
        &nbsp;&nbsp;&nbsp;&nbsp;aclib.runAutoTag({<br>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;zoneId: 'suhf5fqztw',<br>
        &nbsp;&nbsp;&nbsp;&nbsp;});<br>
        &lt;/script&gt;
    </div>
    
    <h2>Blocos que serão configurados:</h2>
    <ul>
        <li>Bloco 1: Header Banner</li>
        <li>Bloco 2: Sidebar Rectangle</li>
        <li>Bloco 3: In-Content Ad</li>
        <li>Bloco 4: Footer Banner</li>
    </ul>
    
    <form method="POST">
        <input type="hidden" name="config_adcash" value="1">
        <button type="submit" class="btn">✓ Aplicar Configuração AdCash</button>
    </form>
</body>
</html>
