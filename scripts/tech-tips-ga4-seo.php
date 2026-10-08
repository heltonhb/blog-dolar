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
 * 2. AdSense — global site tag (publisher ID do site)
 *    Alcunha do script: ca-pub-6258036451330976
 * ------------------------------------------------------------------------- */
function tech_tips_adsense_head()
{
    ?>
    <!-- AdSense global site tag via mu-plugin -->
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6258036451330976" crossorigin="anonymous"></script>
    <meta name="google-adsense-account" content="ca-pub-6258036451330976">
    <?php
}
add_action("wp_head", "tech_tips_adsense_head", 4);

/* ---------------------------------------------------------------------------
 * 2b. Pinterest Domain Verification
 * ------------------------------------------------------------------------- */
function tech_tips_pinterest_verification()
{
    if (is_admin()) {
        return;
    }
    ?>
    <!-- Pinterest domain verification -->
    <meta name="p:domain_verify" content="7c1931644caa7c83f03544d37d48d8f7">
    <?php
}
add_action("wp_head", "tech_tips_pinterest_verification", 0);

/* ---------------------------------------------------------------------------
 * 3. SEO meta description + og tags
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

/* ---------------------------------------------------------------------------
 * 4. Canonical na home + noindex nos arquivos (category/author)
 *    O WP core só emite rel_canonical em páginas singulares; a home fica sem
 *    canonical e os arquivos de taxonomia/autor ficam indexáveis apesar de
 *    serem páginas finas. Cede o lugar a um plugin SEO, como acima.
 * ------------------------------------------------------------------------- */
function tech_tips_front_canonical()
{
    if (is_admin()) {
        return;
    }
    if (defined("WPSEO_VERSION") || defined("RANK_MATH_VERSION")) {
        return;
    }
    if (!(is_front_page() || is_home()) || is_paged() || is_singular()) {
        return;
    }
    $canonical = is_front_page()
        ? home_url("/")
        : (int) get_option("page_for_posts");
    $canonical = is_front_page() ? home_url("/") : get_permalink($canonical);
    if ($canonical) {
        echo '<link rel="canonical" href="' . esc_url($canonical) . '">' . "\n";
    }
}
add_action("wp_head", "tech_tips_front_canonical", 3);

function tech_tips_archive_robots($robots)
{
    if (defined("WPSEO_VERSION") || defined("RANK_MATH_VERSION")) {
        return $robots;
    }
    if (is_category() || is_author()) {
        $robots["noindex"] = true;
        $robots["follow"] = true;
    }
    return $robots;
}
add_filter("wp_robots", "tech_tips_archive_robots");

/* ---------------------------------------------------------------------------
 * 5. Affiliate Cards Styling & FTC Disclosure
 *    Renderiza caixas responsivas de recomendação (Amazon / VPN / Tech)
 * ------------------------------------------------------------------------- */
function tech_tips_affiliate_styles()
{
    if (is_admin()) {
        return;
    }
    ?>
    <style id="tech-tips-affiliate-css">
      .tech-affiliate-disclosure {
        background: #f8fafc;
        border-left: 4px solid #10b981;
        padding: 10px 16px;
        margin: 15px 0 25px 0;
        border-radius: 6px;
        font-size: 0.88rem;
        color: #475569;
        line-height: 1.5;
      }
      .tech-affiliate-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 25px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }
      .tech-affiliate-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
      }
      .affiliate-card-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 0 0 8px 0 !important;
        flex-wrap: wrap;
      }
      .affiliate-badge {
        display: inline-block;
        background: #10b981;
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        padding: 4px 10px;
        border-radius: 6px;
        text-transform: uppercase;
      }
      .affiliate-badge.vpn-badge {
        background: #2563eb;
      }
      .affiliate-title {
        display: inline-block;
        margin: 0 !important;
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        line-height: 1.3 !important;
        color: #0f172a !important;
      }
      .affiliate-desc {
        color: #475569 !important;
        font-size: 0.95rem !important;
        line-height: 1.5 !important;
        margin: 8px 0 14px 0 !important;
      }
      .affiliate-specs {
        list-style: none !important;
        padding: 0 !important;
        margin: 0 0 16px 0 !important;
        display: flex;
        flex-wrap: wrap;
        gap: 8px 16px;
      }
      .affiliate-specs li {
        font-size: 0.85rem !important;
        color: #334155 !important;
        background: #f1f5f9;
        padding: 4px 10px;
        border-radius: 4px;
        border-left: 3px solid #10b981;
      }
      .affiliate-action {
        display: flex;
        align-items: center;
        gap: 15px;
        flex-wrap: wrap;
        margin: 0 !important;
        padding-top: 12px;
        border-top: 1px solid #f1f5f9;
      }
      .tech-affiliate-disclosure p {
        margin: 0 !important;
      }
      .affiliate-btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-weight: 700;
        font-size: 0.95rem;
        padding: 10px 22px;
        border-radius: 8px;
        text-decoration: none !important;
        transition: all 0.2s ease;
        cursor: pointer;
      }
      .amazon-btn {
        background: #ff9900;
        background: linear-gradient(180deg, #ff9900 0%, #e68a00 100%);
        color: #111111 !important;
        box-shadow: 0 2px 5px rgba(255, 153, 0, 0.3);
      }
      .amazon-btn:hover {
        background: #f08c00;
        color: #000000 !important;
        box-shadow: 0 4px 10px rgba(255, 153, 0, 0.4);
      }
      .vpn-btn {
        background: #0052cc;
        color: #ffffff !important;
        box-shadow: 0 2px 5px rgba(0, 82, 204, 0.3);
      }
      .vpn-btn:hover {
        background: #003d99;
        color: #ffffff !important;
      }
      .affiliate-subtext {
        font-size: 0.82rem;
        color: #64748b;
      }
      /* Quick Recommendations Box (Above the Fold) */
      .tech-quick-picks {
        background: #f8fafc;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 22px;
        margin: 25px 0 32px 0;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
      }
      .quick-picks-header {
        margin-bottom: 16px;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 10px;
      }
      .quick-picks-tag {
        display: inline-block;
        background: #0f172a;
        color: #ffffff;
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        padding: 3px 8px;
        border-radius: 4px;
        text-transform: uppercase;
        margin-bottom: 6px;
      }
      .quick-picks-title {
        margin: 4px 0 0 0 !important;
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
      }
      .quick-picks-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
        gap: 16px;
      }
      .quick-pick-item {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }
      .quick-pick-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
      }
      .quick-pick-badge {
        font-size: 0.70rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        color: #059669;
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        padding: 3px 8px;
        border-radius: 4px;
        align-self: flex-start;
        margin-bottom: 10px;
        text-transform: uppercase;
      }
      .quick-pick-title {
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
        line-height: 1.3 !important;
        margin: 0 0 8px 0 !important;
      }
      .quick-pick-desc {
        font-size: 0.88rem !important;
        color: #475569 !important;
        line-height: 1.45 !important;
        margin: 0 0 16px 0 !important;
        flex-grow: 1;
      }
      .quick-pick-btn {
        display: inline-block;
        text-align: center;
        font-weight: 700;
        font-size: 0.88rem;
        padding: 10px 14px;
        border-radius: 6px;
        text-decoration: none !important;
      }
      @media (prefers-color-scheme: dark) {
        .tech-affiliate-card {
          background: #1e293b;
          border-color: #334155;
        }
        .affiliate-title {
          color: #f8fafc !important;
        }
        .affiliate-desc {
          color: #cbd5e1 !important;
        }
        .affiliate-specs li {
          background: #0f172a;
          color: #e2e8f0 !important;
        }
        .tech-affiliate-disclosure {
          background: #0f172a;
          color: #94a3b8;
          border-left-color: #10b981;
        }
        .affiliate-action {
          border-top-color: #334155;
        }
        .tech-quick-picks {
          background: #0f172a;
          border-color: #334155;
        }
        .quick-picks-header {
          border-bottom-color: #334155;
        }
        .quick-picks-title {
          color: #f8fafc !important;
        }
        .quick-pick-item {
          background: #1e293b;
          border-color: #334155;
        }
        .quick-pick-title {
          color: #f8fafc !important;
        }
        .quick-pick-desc {
          color: #cbd5e1 !important;
        }
        .quick-pick-badge {
          background: #064e3b;
          color: #6ee7b7;
          border-color: #047857;
        }
      }
    </style>
    <?php
}
add_action("wp_head", "tech_tips_affiliate_styles", 5);

/* ---------------------------------------------------------------------------
 * 6. Monetag (Display Ads - Native / Push)
 *    Ativação condicionada a constante MONETAG_TAG_ID ou opção do banco
 * ------------------------------------------------------------------------- */
function tech_tips_monetag_head()
{
    if (is_admin()) {
        return;
    }
    $tag_id = defined("MONETAG_TAG_ID") ? MONETAG_TAG_ID : get_option("monetag_tag_id", "");
    if (!empty($tag_id)) {
        ?>
        <!-- Monetag Tag via mu-plugin -->
        <script src="https://alwingulla.com/88/tag.min.js" data-zone="<?php echo esc_attr($tag_id); ?>" async data-cfasync="false"></script>
        <?php
    }
}
add_action("wp_head", "tech_tips_monetag_head", 6);

/* ---------------------------------------------------------------------------
 * 7. Infolinks (InText Contextual Ads)
 *    Ativação condicionada a constante INFOLINKS_PID ou opção do banco
 * ------------------------------------------------------------------------- */
function tech_tips_infolinks_footer()
{
    if (is_admin()) {
        return;
    }
    $pid = defined("INFOLINKS_PID") ? INFOLINKS_PID : get_option("infolinks_pid", "");
    if (!empty($pid)) {
        ?>
        <!-- Infolinks via mu-plugin -->
        <script type="text/javascript">
          var infolinks_pid = <?php echo json_encode($pid); ?>;
          var infolinks_wsid = 0;
        </script>
        <script type="text/javascript" src="//resources.infolinks.com/js/infolinks_main.js" async></script>
        <?php
    }
}
add_action("wp_footer", "tech_tips_infolinks_footer", 20);

/* ---------------------------------------------------------------------------
 * 8. Affiliate click tracking (GA4 events)
 *    Fires `affiliate_click` on every outbound click to amazon.com or a
 *    nordvpn/go link, so GA4 shows which article actually drives revenue.
 *    Delegated listener: works with cards injected later and with both
 *    .affiliate-btn buttons and plain in-text links.
 * ------------------------------------------------------------------------- */
function tech_tips_affiliate_tracking_footer()
{
    if (is_admin()) {
        return;
    }
    ?>
    <!-- Affiliate click tracking via mu-plugin -->
    <script>
      (function () {
        if (typeof gtag !== "function") {
          return;
        }
        function networkOf(href) {
          if (href.indexOf("amazon.") !== -1) { return "amazon"; }
          if (href.indexOf("nordvpn") !== -1 || href.indexOf("go.nordvpn") !== -1) { return "nordvpn"; }
          return "other";
        }
        document.addEventListener("click", function (e) {
          var el = e.target && e.target.closest ? e.target.closest("a[href]") : null;
          if (!el) { return; }
          var href = el.getAttribute("href") || "";
          var network = networkOf(href);
          if (network === "other") { return; }
          var card = el.closest ? el.closest(".tech-affiliate-card, .quick-pick-item") : null;
          var titleEl = card ? card.querySelector(".affiliate-title, .quick-pick-title") : null;
          gtag("event", "affiliate_click", {
            affiliate_network: network,
            link_url: href,
            product_title: titleEl ? titleEl.textContent.trim().slice(0, 100) : "",
            page_path: window.location.pathname
          });
        }, { passive: true });
      })();
    </script>
    <?php
}
add_action("wp_footer", "tech_tips_affiliate_tracking_footer", 21);
