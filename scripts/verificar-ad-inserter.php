<?php
/**
 * Verificar Configuração do Ad Inserter
 * 
 * Acesse: https://tech-tips.byethost4.com/verificar-ad-inserter.php
 */

$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    echo 'ERRO: wp-load.php não encontrado';
    exit;
}

$option_name = 'ai-insert-ads';
$options = get_option($option_name);

?>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Verificação Ad Inserter</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .ok { background: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #28a745; }
        .erro { background: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #dc3545; }
        .aviso { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #ffc107; }
        h1 { color: #333; }
        h2 { color: #555; margin-top: 30px; }
        .status { font-size: 18px; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Verificação do Ad Inserter</h1>
    
    <?php if ($options): ?>
        <div class="ok">
            <span class="status">✓ CONFIGURAÇÃO ENCONTRADA!</span>
        </div>
        
        <h2>Blocos Configurados:</h2>
        
        <?php for ($i = 1; $i <= 4; $i++): ?>
            <?php 
            $block_key = 'b' . $i;
            $has_block = isset($options[$block_key]);
            $has_code = $has_block && !empty($options[$block_key]['code']);
            $is_enabled = $has_block && isset($options[$block_key]['enabled']) && $options[$block_key]['enabled'] == 1;
            ?>
            
            <?php if ($has_block): ?>
                <div class="ok">
                    <span class="status">✓ Bloco <?= $i ?></span>
                    <?php if ($is_enabled): ?>
                        - HABILITADO
                    <?php else: ?>
                        - DESABILITADO
                    <?php endif; ?>
                    
                    <?php if ($has_code): ?>
                        <br>Código: CONFIGURADO
                    <?php else: ?>
                        <br>Código: SEM CÓDIGO
                    <?php endif; ?>
                </div>
            <?php else: ?>
                <div class="erro">
                    <span class="status">✗ Bloco <?= $i ?></span> - NÃO CONFIGURADO
                </div>
            <?php endif; ?>
        <?php endfor; ?>
        
        <h2>Próximos Passos:</h2>
        <ol>
            <li>Acesse o <a href="wp-admin/options-general.php?page=ad-inserter.php">Ad Inserter</a></li>
            <li>Crie conta no <a href="https://adcash.com/publishers/signup" target="_blank">AdCash</a></li>
            <li>Cole o código real do AdCash nos blocos</li>
            <li>Delete este arquivo: verificacao-ad-inserter.php</li>
        </ol>
        
    <?php else: ?>
        <div class="erro">
            <span class="status">✗ NENHUMA CONFIGURAÇÃO ENCONTRADA!</span>
        </div>
        
        <div class="aviso">
            Execute o script de configuração primeiro:<br>
            <a href="setup-ad-inserter.php">setup-ad-inserter.php</a>
        </div>
    <?php endif; ?>
    
    <hr>
    <p><small>Delete este arquivo após a verificação!</small></p>
</body>
</html>
