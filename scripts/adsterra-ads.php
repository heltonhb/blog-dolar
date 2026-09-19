<?php
/**
 * Plugin Name: Tech Tips Adsterra Integration
 * Description: Integrates Adsterra advertising network scripts into Tech Tips.
 * Version: 1.0.0
 * Author: Tech Tips
 */

if (!defined("ABSPATH")) {
    exit;
}

function tech_tips_adsterra_head_ads() {
    if (is_admin()) {
        return;
    }
    ?>
    <!-- Adsterra Advertising Network -->
    <script type="text/javascript" src="https://pl31408097.profitableratecpmnetwork.com/d6/70/6e/d6706ee7f73fa1f45feec523fb200195.js"></script>
    <script type="text/javascript" src="https://pl31408098.profitableratecpmnetwork.com/ce/06/df/ce06dff87d5eda92410aec0540a0fd8c.js"></script>
    <!-- End Adsterra Advertising Network -->
    <?php
}
add_action("wp_head", "tech_tips_adsterra_head_ads", 10);
