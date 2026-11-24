from flask import Flask
from pyhead import Head
from pyhead.elements import (
    Favicon,
    OpenGraphWebsite,
    Page,
    ReferrerPolicy,
    Robots,
    ThemeColor,
    TwitterCard,
)

TITLE = "I Do Sets"
DESCRIPTION = "A workout webapp; focused towards doing sets."
SITE_URL = "https://idosets.app"

HEAD = Head(
    [
        Page(
            title=TITLE,
            description=DESCRIPTION,
            viewport="width=device-width, initial-scale=1, viewport-fit=cover",
        ),
        Robots("noindex, nofollow"),
        ThemeColor("#1E242F"),
        ReferrerPolicy("no-referrer"),
        Favicon(ico_icon_href="/favicon.ico"),
        OpenGraphWebsite(
            locale="en_GB",
            site_name=TITLE,
            title=TITLE,
            description=DESCRIPTION,
            url=SITE_URL,
            image=f"{SITE_URL}/img/facebook.jpg",
            image_alt="I Do Sets Logo",
        ),
        TwitterCard(
            card="summary",
            title=TITLE,
            description=DESCRIPTION,
            url=SITE_URL,
            image=f"{SITE_URL}/img/twitter.jpg",
            image_alt="I Do Sets Logo",
        ),
    ]
)


def include(app: Flask):
    @app.context_processor
    def inject_head():
        return {"head": HEAD}
