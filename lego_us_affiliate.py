#!/usr/bin/env python3
"""LEGO Brand Retail US "Buy this set" links for set pages.

Build_Website.py is not in this repository. Paste the constants below to the
top of that script and call apply_lego_us_buy_link() on a set page's HTML
immediately before the file is written. RAKUTEN_LEGO_US_ID is set, so the
feature is on. Clearing that constant turns the call back into a no-op.

Rakuten deep-link format (Publisher Help Center, "Create Deep Links Manually"):
https://click.linksynergy.com/deeplink?id=<encrypted affiliate id>&mid=<advertiser MID>&murl=<url-encoded destination>

The id parameter is the publisher's 11-character encrypted affiliate ID from a
dashboard link. It is not the site ID (SID). SID 4767557 must not be used here.
Advertiser: LEGO Brand Retail US, MID 13923.
"""

import html
import os
import re
import sys
from urllib.parse import quote

# Encrypted Rakuten affiliate ID (the id= value). Not site ID (SID) 4767557.
# Clear this constant to disable LEGO US buy links without other code changes.
RAKUTEN_LEGO_US_ID = "5ohbqj7yxzM"
RAKUTEN_LEGO_US_MID = "13923"

_DEEPLINK = "https://click.linksynergy.com/deeplink"
_DISCLOSURE = "Affiliate link – we may earn a commission."
_RETAIL_NUMBER = re.compile(r"^[1-9][0-9]{3,4}$")
_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,180}$")
_AFFILIATE_ID = re.compile(r"^[A-Za-z0-9]{11}$")
_SKIP_THEMES = {"bricklink", "education"}


def rakuten_lego_us_enabled(publisher_id=None):
    """True only for a filled-in 11-character encrypted affiliate ID."""
    value = RAKUTEN_LEGO_US_ID if publisher_id is None else publisher_id
    return _AFFILIATE_ID.fullmatch(str(value or "").strip()) is not None


def _has_price(*values):
    for value in values:
        digits = re.sub(r"\D", "", str(value or ""))
        if digits and set(digits) != {"0"}:
            return True
    return False


def is_lego_retail_set(set_number, name="", theme="", msrp_us="", msrp_uk="", msrp_eu="", msrp=""):
    """Retail set numbers LEGO Brand Retail can sell.

    Keeps ordinary 4- and 5-digit set numbers. Skips magazine gifts, BrickLink
    Designer Program sets, Education products, 6- and 7-digit promo/item IDs,
    named make-and-take IDs, promotional sets with no retail price, and
    unpriced 30xxx polybags.
    """
    number = str(set_number or "").strip()
    if _RETAIL_NUMBER.fullmatch(number) is None:
        return False
    label = str(name or "").casefold()
    if "magazine" in label or "polybag" in label or "gift with purchase" in label:
        return False
    if str(theme or "").strip().casefold() in _SKIP_THEMES:
        return False
    priced = _has_price(msrp_us, msrp_uk, msrp_eu, msrp)
    if str(theme or "").strip().casefold() == "promotional" and not priced:
        return False
    # 30xxx with no catalogue price are gift/polybag-only IDs, not shop sets.
    if number.startswith("30") and not priced:
        return False
    return True


def lego_us_target_url(set_number, product_slug=""):
    """Product URL when a slug is known, otherwise LEGO's set-number search."""
    slug = str(product_slug or "").strip().strip("/")
    if _SLUG.fullmatch(slug) and ".." not in slug:
        return "https://www.lego.com/en-us/product/" + slug
    return "https://www.lego.com/en-us/search?q=" + quote(str(set_number).strip(), safe="")


def lego_us_deeplink(set_number, product_slug="", publisher_id=None):
    """Rakuten deep link, or "" when the affiliate ID is not configured."""
    if not rakuten_lego_us_enabled(publisher_id):
        return ""
    affiliate_id = (RAKUTEN_LEGO_US_ID if publisher_id is None else publisher_id).strip()
    target = lego_us_target_url(set_number, product_slug)
    return (
        _DEEPLINK
        + "?id=" + quote(affiliate_id, safe="")
        + "&mid=" + quote(RAKUTEN_LEGO_US_MID, safe="")
        + "&murl=" + quote(target, safe="")
    )


def lego_us_buy_anchor(set_number, name="", theme="", msrp_us="", msrp_uk="", msrp_eu="", msrp="", product_slug="", publisher_id=None):
    """One buy button, or "" when the feature is off or the set is not retail."""
    if not is_lego_retail_set(set_number, name, theme, msrp_us, msrp_uk, msrp_eu, msrp):
        return ""
    href = lego_us_deeplink(set_number, product_slug, publisher_id)
    if not href:
        return ""
    number = html.escape(str(set_number).strip(), quote=True)
    return (
        '<a class="buy-btn" href="' + html.escape(href, quote=True) + '" '
        'rel="sponsored nofollow noopener" target="_blank" '
        'data-retailer="lego_us" data-set="' + number + '">Buy this set</a>'
    )


def apply_lego_us_buy_link(page_html, set_number, name="", theme="", msrp_us="", msrp_uk="", msrp_eu="", msrp="", product_slug="", publisher_id=None):
    """Insert the LEGO US button into an existing buy box. No-op when disabled.

    Does not add a buy box to pages that do not already have one, and does not
    touch meta tags, video markup, sitemaps, or redirects.
    """
    anchor = lego_us_buy_anchor(
        set_number,
        name=name,
        theme=theme,
        msrp_us=msrp_us,
        msrp_uk=msrp_uk,
        msrp_eu=msrp_eu,
        msrp=msrp,
        product_slug=product_slug,
        publisher_id=publisher_id,
    )
    if not anchor or 'data-retailer="lego_us"' in page_html:
        return page_html
    section = page_html.find('class="buy-this-set"')
    if section < 0:
        return page_html
    links = page_html.find('<div class="buy-links">', section)
    if links < 0:
        return page_html
    disclosure = page_html.find('<p class="affiliate-disclosure">', section)
    if 0 <= disclosure < links and _DISCLOSURE not in page_html[disclosure:links]:
        learn_more = page_html.find('<a href="/affiliate-disclosure/">', disclosure)
        if 0 <= learn_more < links:
            page_html = page_html[:learn_more] + _DISCLOSURE + " " + page_html[learn_more:]
        else:
            end_p = page_html.find("</p>", disclosure)
            if 0 <= end_p < links:
                page_html = page_html[:end_p] + " " + _DISCLOSURE + page_html[end_p:]
        links = page_html.find('<div class="buy-links">', section)
    insert_at = links + len('<div class="buy-links">')
    return page_html[:insert_at] + anchor + page_html[insert_at:]


def _meta_description(page_html):
    match = re.search(r'<meta name="description" content="[^"]*">', page_html)
    return match.group(0) if match else ""


def _self_check():
    root = os.path.dirname(os.path.abspath(__file__))
    retail = os.path.join(root, "public/lego-instructions/10316-icons-the-lord-of-the-rings-rivendell/index.html")
    magazine = os.path.join(root, "public/lego-instructions/l0002228-city-adventurer-with-airplane-magazine-gift/index.html")
    rivendell = open(retail, encoding="utf-8").read()
    gift = open(magazine, encoding="utf-8").read()

    assert RAKUTEN_LEGO_US_ID == "5ohbqj7yxzM"
    assert rakuten_lego_us_enabled() is True
    assert rakuten_lego_us_enabled("") is False
    assert rakuten_lego_us_enabled("4767557") is False
    assert lego_us_buy_anchor("10316", name="Rivendell", theme="Icons", msrp_us="$499.99", publisher_id="") == ""
    assert apply_lego_us_buy_link(
        rivendell, "10316", name="The Lord of the Rings: Rivendell", theme="Icons", msrp_us="$499.99", publisher_id="",
    ) == rivendell

    cases = [
        ("10316", "The Lord of the Rings: Rivendell", "Icons", "$499.99", "", "", "", True),
        ("75313", "AT-AT", "Star Wars", "$849.99", "", "", "", True),
        ("40574", "LEGO Brand Store", "Promotional", "$36.99", "", "", "", True),
        ("30638", "Police Bike Training", "City", "", "£3.50", "", "3.5", True),
        ("40450", "Amelia Earhart Tribute", "Promotional", "", "", "", "", False),
        ("30343", "McLaren Elva", "Speed Champions", "", "", "", "", False),
        ("912170", "V-wing", "Star Wars", "", "", "", "", False),
        ("L0002228", "Magazine Gift", "City", "", "", "", "", False),
        ("910065", "Coconut Cape", "Bricklink", "$209.99", "", "", "", False),
        ("11962", "Creator Magazine - Robot", "Creator", "$9.99", "", "", "", False),
        ("2000471", "BricQ Motion", "Education", "", "", "", "", False),
        ("", "Mystery", "City", "$10", "", "", "", False),
    ]
    for number, name, theme, us, uk, eu, raw, expect in cases:
        got = is_lego_retail_set(number, name, theme, us, uk, eu, raw)
        if got != expect:
            raise SystemExit("retail filter mismatch for %s: %s" % (number, got))

    anchor = lego_us_buy_anchor("10316", name="Rivendell", theme="Icons", msrp_us="$499.99")
    if 'rel="sponsored nofollow noopener"' not in anchor or 'target="_blank"' not in anchor:
        raise SystemExit("missing link attributes")
    if ">Buy this set</a>" not in anchor or 'data-retailer="lego_us"' not in anchor:
        raise SystemExit("missing button label")
    href = html.unescape(re.search(r'href="([^"]+)"', anchor).group(1))
    expected = (
        "https://click.linksynergy.com/deeplink?id=5ohbqj7yxzM&mid=13923&murl="
        "https%3A%2F%2Fwww.lego.com%2Fen-us%2Fsearch%3Fq%3D10316"
    )
    if href != expected:
        raise SystemExit("unexpected href:\n" + href)

    slug_href = html.unescape(re.search(
        r'href="([^"]+)"',
        lego_us_buy_anchor("10316", name="Rivendell", theme="Icons", msrp_us="$499.99", product_slug="rivendell-10316"),
    ).group(1))
    if "murl=https%3A%2F%2Fwww.lego.com%2Fen-us%2Fproduct%2Frivendell-10316" not in slug_href:
        raise SystemExit("slug target missing")

    updated = apply_lego_us_buy_link(
        rivendell, "10316", name="The Lord of the Rings: Rivendell", theme="Icons",
        msrp_us="$499.99", msrp_uk="£429.99", msrp_eu="€499.99",
    )
    if updated == rivendell or updated.count('data-retailer="lego_us"') != 1:
        raise SystemExit("sample page was not updated once")
    if _meta_description(updated) != _meta_description(rivendell):
        raise SystemExit("meta description changed")
    if "youtube" in rivendell.lower() and rivendell.lower().count("youtube") != updated.lower().count("youtube"):
        raise SystemExit("youtube markup changed")
    if _DISCLOSURE not in updated.split('class="buy-this-set"', 1)[1].split("</section>", 1)[0]:
        raise SystemExit("disclosure missing beside the buy link")
    again = apply_lego_us_buy_link(
        updated, "10316", name="The Lord of the Rings: Rivendell", theme="Icons", msrp_us="$499.99",
    )
    if again != updated:
        raise SystemExit("second apply changed the page")

    gift_updated = apply_lego_us_buy_link(
        gift, "L0002228", name="City - Adventurer with Airplane - Magazine Gift", theme="City",
    )
    if gift_updated != gift:
        raise SystemExit("magazine gift page changed")

    print("ok")
    print(href)
    return updated


def _preview(argv):
    """Write one rendered set page to disk using a preview ID. Does not edit the source page."""
    if "--html" not in argv:
        raise SystemExit("usage: lego_us_affiliate.py --preview --html PAGE --set NUMBER [--out FILE]")
    page_path = argv[argv.index("--html") + 1]
    preview_id = argv[argv.index("--id") + 1] if "--id" in argv else None
    set_number = argv[argv.index("--set") + 1] if "--set" in argv else ""
    out_path = argv[argv.index("--out") + 1] if "--out" in argv else "/tmp/lego-us-buy-preview.html"

    def opt(flag):
        return argv[argv.index(flag) + 1] if flag in argv else ""

    page = open(page_path, encoding="utf-8").read()
    updated = apply_lego_us_buy_link(
        page,
        set_number,
        name=opt("--name"),
        theme=opt("--theme"),
        msrp_us=opt("--msrp-us"),
        msrp_uk=opt("--msrp-uk"),
        msrp_eu=opt("--msrp-eu"),
        product_slug=opt("--slug"),
        publisher_id=preview_id,
    )
    if updated == page:
        raise SystemExit("preview did not add a link (check the set number, prices, and preview ID)")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(updated)
    print(out_path)


if __name__ == "__main__":
    if "--preview" in sys.argv:
        _preview(sys.argv)
    else:
        _self_check()
