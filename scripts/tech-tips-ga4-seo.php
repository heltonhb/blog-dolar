<?php
/**
 * Plugin Name: Tech Tips GA4 + SEO Meta
 * Description: Injects GA4 (gtag.js) and meta description/og tags (from post excerpt) into the front-end. Skips if an SEO plugin takes over.
 * Version: 1.0.0
 * Author: Tech Tips
 */

if (!defined("ABSPATH")) {
    exit;
}

/* ---------------------------------------------------------------------------
 * 1. GA4 — Google Analytics (gtag.js), propriedade GA4 "Blog-dollar" (554549804)
 * ------------------------------------------------------------------------- */
function tech_tips_ga4_head()
{
    if (is_admin()) {
        return;
    }
    ?>
    <!-- GA4 via mu-plugin -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-G01J573W6J"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-G01J573W6J');
    </script>
    <?php
}
add_action("wp_head", "tech_tips_ga4_head", 1);

/* ---------------------------------------------------------------------------
 * 2. SEO meta description + og tags
 *    Fonte da description: excerpt do post (o pipeline salva o meta_description
 *    lá). Canonical NÃO é emitido aqui — o WP core já emite via rel_canonical.
 *    Se um plugin SEO (Yoast/RankMath) estiver ativo, não emitimos nada.
 * ------------------------------------------------------------------------- */
function tech_tips_seo_meta_head()
{
    if (is_admin()) {
        return;
    }
    // Cede o lugar a qualquer plugin SEO ativo
    if (defined("WPSEO_VERSION") || defined("RANK_MATH_VERSION")) {
        return;
    }

    $description = "";
    $title = wp_get_document_title();
    $url = home_url("/");
    $type = "website";

    if (is_singular()) {
        $post = get_queried_object();
        if ($post) {
            $desc_raw = get_the_excerpt($post);
            if (trim($desc_raw) !== "" && stripos($desc_raw, "Welcome to WordPress") === false) {
                $description = $desc_raw;
            } else {
                // fallback: primeiro bloco de texto do conteúdo
                $text = wp_strip_all_tags($post->post_content ?? "");
                $parts = preg_split('/\R+/', trim($text));
                if (!empty($parts)) {
                    $description = trim($parts[0]);
                }
            }
            $title = get_the_title($post) . " – " . get_bloginfo("name");
            $url = get_permalink($post);
            if ($post->post_type === "post") {
                $type = "article";
            }
        }
    } elseif (is_home() || is_front_page()) {
        $description = "Tech Tips: practical technology guides, software tutorials, gadget reviews and everyday tech advice.";
        $url = home_url("/");
    } elseif (is_category()) {
        $description = wp_strip_all_tags(category_description());
        $url = get_category_link(get_queried_object_id());
    }

    $description = trim(wp_strip_all_tags($description));
    if ($description !== "" && function_exists("mb_substr")) {
        $description = mb_substr($description, 0, 155, "UTF-8");
    }

    $thumb = "";
    if (is_singular() && has_post_thumbnail()) {
        $thumb = get_the_post_thumbnail_url(get_queried_object_id(), "large");
    }

    echo "\n<!-- SEO meta via mu-plugin -->\n";
    if ($description !== "") {
        echo '<meta name="description" content="' . esc_attr($description) . '">' . "\n";
    }
    echo '<meta property="og:type" content="' . esc_attr($type) . '">' . "\n";
    echo '<meta property="og:title" content="' . esc_attr($title) . '">' . "\n";
    if ($description !== "") {
        echo '<meta property="og:description" content="' . esc_attr($description) . '">' . "\n";
    }
    echo '<meta property="og:url" content="' . esc_url($url) . '">' . "\n";
    if ($thumb) {
        echo '<meta property="og:image" content="' . esc_url($thumb) . '">' . "\n";
    }
    echo '<meta name="twitter:card" content="summary_large_image">' . "\n";
}
add_action("wp_head", "tech_tips_seo_meta_head", 2);
