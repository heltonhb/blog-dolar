<?php
/**
 * Plugin Name: Tech Tips Adsterra Integration
 * Description: Integrates Adsterra advertising network scripts and banners into Tech Tips.
 * Version: 1.1.0
 * Author: Tech Tips
 */

if (!defined("ABSPATH")) {
    exit;
}

/**
 * 1. Head Scripts (Social Bar, Popunder, Network Tags)
 */
function tech_tips_adsterra_head_ads() {
    if (is_admin()) {
        return;
    }
    ?>
    <!-- Adsterra Advertising Network (Head Scripts) -->
    <script type="text/javascript" src="https://pl31408097.profitableratecpmnetwork.com/d6/70/6e/d6706ee7f73fa1f45feec523fb200195.js"></script>
    <script type="text/javascript" src="https://pl31408098.profitableratecpmnetwork.com/ce/06/df/ce06dff87d5eda92410aec0540a0fd8c.js"></script>
    <!-- End Adsterra Advertising Network -->
    <?php
}
add_action("wp_head", "tech_tips_adsterra_head_ads", 10);

/**
 * 2. In-Content Native/Display Banner (Single Articles)
 */
function tech_tips_adsterra_content_banner($content) {
    if (is_admin() || !is_singular('post')) {
        return $content;
    }

    $banner = <<<HTML
<div class="tech-tips-adsterra-banner" style="margin: 25px auto; text-align: center; max-width: 100%; overflow: hidden; clear: both;">
    <script async="async" data-cfasync="false" src="https://pl31408157.profitableratecpmnetwork.com/27e8efa95d52426b90979caf133143b3/invoke.js"></script>
    <div id="container-27e8efa95d52426b90979caf133143b3"></div>
</div>
HTML;

    // Inserir após o 3º parágrafo para melhor CTR
    $paragraphs = explode('</p>', $content);
    if (count($paragraphs) > 3) {
        $new_content = '';
        foreach ($paragraphs as $index => $para) {
            $new_content .= $para;
            if (trim($para)) {
                $new_content .= '</p>';
            }
            if ($index === 2) {
                $new_content .= $banner;
            }
        }
        return $new_content;
    }

    return $content . $banner;
}
add_filter('the_content', 'tech_tips_adsterra_content_banner', 20);
