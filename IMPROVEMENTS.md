# Improvements

## LEGO US affiliate links (Rakuten)

`Build_Website.py` is not in this repository. The files here are its generated output, and that script rebuilds the site about every two hours. `lego_us_affiliate.py` is the hook to call from that script. It does not change sitemaps, redirects, meta descriptions, or the YouTube player.

Paste `RAKUTEN_LEGO_US_ID` to the top of `Build_Website.py` and call `apply_lego_us_buy_link(...)` on each set page immediately before the HTML is written. Pass the set number, name, theme, prices, and product slug when one exists.

`RAKUTEN_LEGO_US_ID` is `5ohbqj7yxzM`, the encrypted affiliate ID from a working Rakuten deep link. The feature is enabled. Publisher Help Center: [Create Deep Links Manually](https://pubhelp.rakutenadvertising.com/hc/en-us/articles/11459139039373-Create-Deep-Links-Manually) and [Affiliate ID or Encrypted ID](https://pubhelp.rakutenadvertising.com/hc/en-us/articles/4412187912845-Affiliate-ID-or-Encrypted-ID). Site ID (SID) `4767557` is a different value and is not used. Clearing the constant, or setting a value that is not 11 letters or digits, turns the call back into a no-op.

The deep link is `https://click.linksynergy.com/deeplink?id=5ohbqj7yxzM&mid=13923&murl=<url-encoded lego.com/en-us URL>`. Advertiser is LEGO Brand Retail US, MID `13923`. Set records have no product slug, so the destination is `https://www.lego.com/en-us/search?q=<set number>` unless a slug is passed through. Magazine gifts, BrickLink and Education IDs, unpriced promotional sets, and unpriced 30xxx polybags are skipped.
