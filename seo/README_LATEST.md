# Latest released sets — SEO landing page repair

This addon **fixes the existing `/latest/` page** after each publish without modifying the MSI's `Build_Website.py` or the individual set pages. As of 14 November 2026, the generated `/latest/` page had switched to **2027** with only one guide while the homepage still correctly featured many published **2026** instruction videos.

## How it works

- After the MSI publishes new website pages to GitHub `main`, GitHub Actions detects a changed homepage or set HTML file.
- Reads the homepage's **Latest YYYY LEGO instructions** section (current/past year only).
- Checks up to 35 listed set pages for an actual `VideoObject`, matching canonical URL and no `noindex` directive.
- Groups guides whose dates are explicitly verified as released within 90 days under **Recently released LEGO sets**.
- Shows other latest published instruction videos in a separate **Newest instruction videos** section, without claiming unknown or future release dates.
- Refreshes only `public/latest/index.html`: title, descriptions, links, cards and CollectionPage/ItemList structured data. Existing set pages, images, video links, affiliate links, sitemaps and robots settings stay unchanged.
- Refuses to change anything if the homepage data is unexpectedly missing or fewer than five guides pass validation.

Because `Build_Website.py` is on the MSI and generates the website every few hours, changes to generated HTML alone would be overwritten. This separate GitHub workflow re-applies the fix after website pushes. **The best permanent source fix is still to alter `Build_Website.py` once desktop access is available.**

## After installation

1. Go to GitHub Actions: https://github.com/critchx/brickinstructionsforyou-site/actions
2. Look for `Keep latest LEGO video guides current` and check for a green run.
3. Visit https://www.brickinstructionsforyou.com/latest/ to confirm it lists multiple 2026 published guides, not just one 2027 item.
4. In Search Console, inspect `/latest/` in the site's URL Inspection tool after deployment. Google chooses whether and when to index the updated page.

The addon does *not* promise higher Google rankings, change the Search Console reports or automatically request Google indexing. It only improves internal links to current, verified instruction videos and keeps the Latest landing page accurate.
