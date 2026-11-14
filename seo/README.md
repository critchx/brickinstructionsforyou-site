# Automated LEGO page discovery

This optional GitHub-side workflow complements (but does not replace) the MSI laptop's `Build_Website.py`. It runs on every push to `main` that changes set pages, the set sitemap, or this workflow. **The build script itself is not in this repository.**

## What it does

- Reads the generated **`public/sitemap-sets.xml`** with its existing, genuine `lastmod` values; it **does not replace or reset** the site's existing sitemap index, canonical tags, indexing rules, affiliate links or HTML.
- Compares the previous and new sitemap plus changed set-page files to find fresh URLs. A first-run bootstrap covers the last four days of set changes.
- Fetches candidate HTML and only notifies pages whose canonical URL matches and whose robots meta tag is indexable. Reports skipped pages in the Actions log. It does not force-enable `noindex` pages.
- Publishes `public/lego-updates.xml`, an RSS feed describing actual published and *coming-soon* pages accurately, with WebSub hub discovery.
- Keeps an RSS sitemap reference in `public/robots.txt` even when the local generator rewrites that file; the original sitemap index remains.
- Sends **IndexNow** notifications to its participating search engines when a URL is new/changed. This is not a Google indexing service.
- Sends a WebSub publish notification for the new RSS feed after it is visible on the public domain. WebSub is a discovery signal, not an indexing guarantee.
- Uses only Python's standard library and GitHub's automatic workflow token. The public IndexNow key lives at `public/52fdcd9f9582abe35aadda14d1e33718.txt` and is intentionally public for verification. No user API key is required.

## After merging

1. Check the **Search engine discovery after website publish** GitHub Actions run for `Found ... candidate` and success/warnings. If GitHub Actions are disabled or workflow token writes are restricted, enable Actions and allow the workflow `contents: write` permissions.
2. Confirm `https://www.brickinstructionsforyou.com/lego-updates.xml` and the public key file are available after deployment. The first run adds the feed and `robots.txt` link automatically.
3. In **Google Search Console**, select the property for `brickinstructionsforyou.com` (not the unrelated Blogspot property), submit `https://www.brickinstructionsforyou.com/sitemap-index.xml` once, and optionally submit `/lego-updates.xml` as another sitemap/feed. Subsequent URL discoveries do not need individual manual requests.
4. In the local `Build_Website.py`, preserve correct per-page canonical, indexability and genuine `lastmod` values. Do **not** re-stamp every unchanged page on every build. Continue publishing the existing sitemap index and linking recent set pages from the website's Latest section. The GitHub workflow restores its RSS robots entry after the local build runs.

**Limits:** Google can take days or weeks to crawl and index; Google's restricted Indexing API is not authorised for these ordinary LEGO set pages. An IndexNow/WebSub HTTP success confirms delivery, not indexing. GitHub Compare's changed-file listing is capped, so the workflow also compares the complete sitemap. A page with an `X-Robots-Tag` response header set by the host (rather than HTML) needs separate checking in Search Console.
