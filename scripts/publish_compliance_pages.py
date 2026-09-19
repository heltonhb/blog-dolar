#!/usr/bin/env python3
"""Publish mandatory compliance pages (Privacy Policy, About Us, Terms of Service, Contact Us) to WordPress."""

from dashboard.services.wordpress import _antibot_session, _env

site_url = _env("SITE_URL", "https://tech-tips.ct.ws").rstrip("/")
wp_user = _env("WP_USER", "")
wp_pass = _env("WP_APP_PASSWORD", "")
auth = (wp_user, wp_pass)
client = _antibot_session(site_url)

pages = [
    {
        "title": "Privacy Policy",
        "slug": "privacy-policy",
        "content": """
<h2>Privacy Policy for Tech Tips</h2>
<p><em>Last Updated: September 18, 2026</em></p>
<p>At <strong>Tech Tips</strong>, accessible from <a href="https://tech-tips.ct.ws">https://tech-tips.ct.ws</a>, one of our main priorities is the privacy of our visitors. This Privacy Policy document outlines the types of information that is collected and recorded by Tech Tips and how we use it.</p>

<h3>1. Log Files</h3>
<p>Tech Tips follows a standard procedure of using log files. These files log visitors when they visit websites. The information collected by log files includes internet protocol (IP) addresses, browser type, Internet Service Provider (ISP), date and time stamp, referring/exit pages, and possibly the number of clicks. These are not linked to any information that is personally identifiable. The purpose of the information is for analyzing trends, administering the site, tracking users movement on the website, and gathering demographic information.</p>

<h3>2. Cookies and Web Beacons</h3>
<p>Like any other website, Tech Tips uses "cookies". These cookies are used to store information including visitors preferences, and the pages on the website that the visitor accessed or visited. The information is used to optimize the users experience by customizing our web page content based on visitors browser type and/or other information.</p>

<h3>3. Advertising Partners Privacy Policies</h3>
<p>Third-party ad servers or ad networks—including <strong>Adsterra</strong> and other advertising partners—use technologies like cookies, JavaScript, or Web Beacons that are used in their respective advertisements and links that appear on Tech Tips, which are sent directly to users browsers. They automatically receive your IP address when this occurs. These technologies are used to measure the effectiveness of their advertising campaigns and/or to personalize the advertising content that you see on websites that you visit.</p>
<p><em>Note that Tech Tips has no access to or control over these cookies that are used by third-party advertisers.</em></p>

<h3>4. Third Party Privacy Policies</h3>
<p>Tech Tips Privacy Policy does not apply to other advertisers or websites. Thus, we are advising you to consult the respective Privacy Policies of these third-party ad servers for more detailed information. It may include their practices and instructions about how to opt-out of certain options.</p>
<p>You can choose to disable cookies through your individual browser options. To know more detailed information about cookie management with specific web browsers, it can be found at the browsers respective websites.</p>

<h3>5. CCPA & GDPR Data Protection Rights</h3>
<p>We would like to make sure you are fully aware of all of your data protection rights. Every user is entitled to the following:</p>
<ul>
    <li><strong>The right to access</strong> – You have the right to request copies of your personal data.</li>
    <li><strong>The right to rectification</strong> – You have the right to request that we correct any information you believe is inaccurate.</li>
    <li><strong>The right to erasure</strong> – You have the right to request that we erase your personal data, under certain conditions.</li>
    <li><strong>The right to restrict processing</strong> – You have the right to request that we restrict the processing of your personal data.</li>
</ul>

<h3>6. Children Information</h3>
<p>Another part of our priority is adding protection for children while using the internet. We encourage parents and guardians to observe, participate in, and/or monitor and guide their online activity. Tech Tips does not knowingly collect any Personal Identifiable Information from children under the age of 13.</p>

<h3>7. Consent & Contact Us</h3>
<p>By using our website, you hereby consent to our Privacy Policy and agree to its terms. If you have additional questions or require more information about our Privacy Policy, do not hesitate to contact us at <a href="mailto:contact@tech-tips.ct.ws">contact@tech-tips.ct.ws</a>.</p>
""",
    },
    {
        "title": "About Us",
        "slug": "about-us",
        "content": """
<h2>About Tech Tips</h2>
<p>Welcome to <strong>Tech Tips</strong> (<a href="https://tech-tips.ct.ws">tech-tips.ct.ws</a>) — your go-to destination for practical, clear, and actionable technology advice, software guides, gadget evaluations, and digital tips.</p>

<h3>Our Mission</h3>
<p>Technology moves fast, but staying informed should not feel overwhelming. Our mission is to simplify complex technological concepts and provide everyday users, creators, and professionals with dependable guides that make computing, gadgets, and internet tools work seamlessly for them.</p>

<h3>What We Cover</h3>
<ul>
    <li><strong>Gadget Guides & Hardware:</strong> In-depth reviews and buyer recommendations on everyday gear, from portable chargers to computing peripherals.</li>
    <li><strong>Digital Productivity & Software:</strong> Step-by-step tutorials to streamline workflows, organize digital clutter, and maximize system performance.</li>
    <li><strong>Privacy & Security:</strong> Practical recommendations to safeguard your online presence, manage sensitive accounts, and protect your digital footprint.</li>
    <li><strong>Emerging Trends:</strong> Insightful breakdowns of cloud infrastructure, artificial intelligence, and smart tech innovations.</li>
</ul>

<h3>Editorial Standards & Independence</h3>
<p>We believe in honest, transparent, and user-centric journalism. Our recommendations are curated independently to prioritize usability, reliability, and value. When we feature products or services, we prioritize real-world utility over marketing hype.</p>

<h3>Get In Touch</h3>
<p>We love hearing from our readers! Whether you have a question about one of our guides, feedback on our content, or an idea for a future topic, please feel free to reach out to our team via our <a href="/contact">Contact Page</a> or by emailing us directly at <a href="mailto:contact@tech-tips.ct.ws">contact@tech-tips.ct.ws</a>.</p>
""",
    },
    {
        "title": "Terms of Service",
        "slug": "terms-of-service",
        "content": """
<h2>Terms of Service</h2>
<p><em>Last Updated: September 18, 2026</em></p>

<h3>1. Acceptance of Terms</h3>
<p>By accessing and using <strong>Tech Tips</strong> (<a href="https://tech-tips.ct.ws">https://tech-tips.ct.ws</a>), you agree to comply with and be bound by these Terms of Service. If you do not agree with any part of these terms, you should discontinue use of this site immediately.</p>

<h3>2. Informational & Educational Disclaimer</h3>
<p>All content provided on Tech Tips is for educational and informational purposes only. While we endeavor to provide accurate and updated information, we make no representations or warranties of any kind regarding completeness, accuracy, or suitability of the information contained on the site. Any reliance you place on such information is strictly at your own risk.</p>

<h3>3. Advertising & Affiliate Disclosure</h3>
<p>Tech Tips participates in advertising programs and may display advertisements served by third-party networks such as Adsterra. Some articles may contain affiliate links, which means we may earn a small commission at no additional cost to you if you make a purchase through those links. This support enables us to continue creating free, high-quality content.</p>

<h3>4. Intellectual Property</h3>
<p>The original content, layout, design, and graphics published on Tech Tips are protected by applicable intellectual property laws. You may not reproduce, distribute, or create derivative works without prior express written permission from Tech Tips.</p>

<h3>5. Limitation of Liability</h3>
<p>In no event shall Tech Tips or its authors be liable for any direct, indirect, incidental, or consequential damages resulting from the use or inability to use the materials on this website, even if advised of the possibility of such damage.</p>

<h3>6. Changes to Terms</h3>
<p>We reserve the right to revise these Terms of Service at any time without prior notice. By continuing to use the site, you agree to be bound by the current version of these Terms.</p>

<h3>7. Contact</h3>
<p>If you have any questions regarding these Terms of Service, please contact us at <a href="mailto:contact@tech-tips.ct.ws">contact@tech-tips.ct.ws</a>.</p>
""",
    },
    {
        "title": "Contact Us",
        "slug": "contact",
        "content": """
<h2>Contact Us</h2>
<p>Have questions, suggestions, or feedback? We are always happy to connect with our readers, collaborators, and technology enthusiasts.</p>

<h3>How to Reach Us</h3>
<ul>
    <li><strong>General Inquiries:</strong> <a href="mailto:contact@tech-tips.ct.ws">contact@tech-tips.ct.ws</a></li>
    <li><strong>Editorial & Corrections:</strong> <a href="mailto:editorial@tech-tips.ct.ws">editorial@tech-tips.ct.ws</a></li>
    <li><strong>Advertising & Partnerships:</strong> <a href="mailto:partners@tech-tips.ct.ws">partners@tech-tips.ct.ws</a></li>
</ul>

<h3>Response Time</h3>
<p>We strive to respond to all inquiries within <strong>24 to 48 business hours</strong>. Please provide as much detail as possible in your message so we can assist you effectively.</p>

<hr/>
<p><em>Tech Tips | Helping you master everyday technology.</em></p>
""",
    },
]

for p in pages:
    payload = {
        "title": p["title"],
        "slug": p["slug"],
        "content": p["content"],
        "status": "publish",
    }
    resp = client.post(f"{site_url}/wp-json/wp/v2/pages", auth=auth, json=payload)
    if resp.status_code in (200, 201):
        data = resp.json()
        print(f"Published '{p['title']}' -> ID: {data.get('id')}, Link: {data.get('link')}")
    else:
        print(f"Failed '{p['title']}': {resp.status_code} - {resp.text[:200]}")
