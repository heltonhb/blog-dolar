<?php
// Script para verificar configuracao do Ad Inserter
// Executar via browser: https://tech-tips.byethost4.com/check-ad-inserter.php

$wp_load = dirname(__FILE__) . '/wp-load.php';
if (file_exists($wp_load)) {
    require_once($wp_load);
} else {
    echo 'wp-load.php not found';
    exit;
}

echo '<h2>Verificacao do Ad Inserter</h2>';
echo '<pre>';

// 1. Verificar se o plugin esta ativo
echo "=== STATUS DO PLUGIN ===\n";
if (is_plugin_active('ad-inserter/ad-inserter.php')) {
    echo "STATUS: ATIVO\n";
} else {
    echo "STATUS: INATIVO\n";
    echo "acao necessaria: Ative o plugin em Plugins\n";
}

// 2. Verificar opcoes do Ad Inserter
echo "\n=== OPCOES DO PLUGIN ===\n";
$option_name = 'ai-insert-ads';
$options = get_option($option_name);

if ($options) {
    echo "Configuracao encontrada!\n";
    
    // Verificar blocos
    echo "\n=== BLOCOS DE ANUNCIOS ===\n";
    for ($i = 1; $i <= 16; $i++) {
        $block_key = 'b' . $i;
        if (isset($options[$block_key])) {
            $block = $options[$block_key];
            $has_code = !empty($block['code']);
            $is_enabled = isset($block['enabled']) && $block['enabled'] == 1;
            
            echo "Bloco $i: ";
            if ($is_enabled) {
                echo "HABILITADO";
            } else {
                echo "DESABILITADO";
            }
            
            if ($has_code) {
                echo " | Tem codigo";
            } else {
                echo " | Sem codigo";
            }
            echo "\n";
        }
    }
    
    // Mostrar configuracao completa (parcial)
    echo "\n=== CONFIGURACAO COMPLETA (primeiros 500 chars) ===\n";
    echo substr(print_r($options, true), 0, 500);
    echo "\n...";
} else {
    echo "Nenhuma configuracao encontrada!\n";
    echo "acao necessaria: Configure o plugin em Settings > Ad Inserter\n";
}

// 3. Verificar se ha codigo de anuncio
echo "\n=== VERIFICACAO DE CODIGO ===\n";
if ($options && isset($options['b1']) && !empty($options['b1']['code'])) {
    echo "Bloco 1 tem codigo configurado\n";
    echo "Codigo (primeiros 200 chars): " . substr($options['b1']['code'], 0, 200) . "\n";
} else {
    echo "Bloco 1 SEM codigo - configure em Settings > Ad Inserter\n";
}

echo "\n=== FIM DA VERIFICACAO ===\n";
echo '</pre>';
?>
