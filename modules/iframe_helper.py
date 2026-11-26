"""
modules/iframe_helper.py
Safe, zero-layout-shift HTML iframe rendering utility for Streamlit applications.

Provides seamless support for Streamlit >= 1.65 `st.iframe` while maintaining
backward compatibility with `streamlit.components.v1.html` for older installations,
plus `components_shim` to prevent `NameError` or deprecation regressions after git merges.
"""

from __future__ import annotations

import re
from typing import Literal, Union
import streamlit as st

HIDDEN_IFRAME_ALT = "__st_hidden_bridge__"

_HIDDEN_COLLAPSE_SNIPPET = """<script>
(function(){
  try {
    var f = window.frameElement;
    if (f) {
      f.setAttribute('scrolling', 'no');
      f.style.cssText += ';width:0px!important;height:0px!important;border:none!important;opacity:0!important;pointer-events:none!important;overflow:hidden!important;';
      var doc = (window.parent && window.parent.document) ? window.parent.document : null;
      if (doc && !doc.getElementById('__ecp_hidden_iframe_css__')) {
        var st = doc.createElement('style');
        st.id = '__ecp_hidden_iframe_css__';
        st.textContent = 'div[data-testid="stElementContainer"]:has(> iframe[title="__st_hidden_bridge__"]){position:absolute!important;width:0px!important;height:0px!important;min-width:0px!important;min-height:0px!important;margin:0px!important;padding:0px!important;overflow:hidden!important;opacity:0!important;pointer-events:none!important;border:none!important;}';
        (doc.head || doc.documentElement).appendChild(st);
      }
      var c = f.closest('div[data-testid="stElementContainer"]') || f.closest('div[data-testid="stCustomComponentV1"]') || f.parentElement;
      if (c) {
        c.style.cssText += ';position:absolute!important;width:0px!important;height:0px!important;min-width:0px!important;min-height:0px!important;margin:0px!important;padding:0px!important;overflow:hidden!important;opacity:0!important;pointer-events:none!important;border:none!important;';
      }
    }
  } catch(e) {}
})();
</script>"""

_NO_SCROLL_SNIPPET = """<style>html,body{overflow:hidden!important;}</style><script>
(function(){
  try {
    var f = window.frameElement;
    if (f) {
      f.setAttribute('scrolling', 'no');
      f.style.overflow = 'hidden';
    }
  } catch(e) {}
})();
</script>"""

_HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.IGNORECASE)
_BODY_CLOSE_RE = re.compile(r"</body\s*>", re.IGNORECASE)


def _inject_before_close(html: str, snippet: str) -> str:
    """Injects `snippet` without ever placing content before `<!DOCTYPE html>`."""
    m = _HEAD_CLOSE_RE.search(html)
    if m:
        return html[: m.start()] + snippet + html[m.start() :]
    m = _BODY_CLOSE_RE.search(html)
    if m:
        return html[: m.start()] + snippet + html[m.start() :]
    return html + snippet


def render_html_iframe(
    html: str,
    height: Union[int, Literal["stretch", "content"], None] = None,
    width: Union[int, Literal["stretch", "content"], None] = None,
    scrolling: bool = False,
    alt: str | None = None,
    *,
    tab_index: int | None = None,
    hidden: bool = False,
):
    """
    Renders HTML inside an iframe using `st.iframe` (Streamlit >= 1.65)
    or `streamlit.components.v1.html` on older versions.
    """
    is_hidden = hidden or (
        isinstance(height, (int, float))
        and height <= 1
        and (width is None or (isinstance(width, (int, float)) and width <= 1))
    )

    if hasattr(st, "iframe"):
        html_out = html if isinstance(html, str) else str(html)
        is_url_src = html_out.lstrip().startswith(("http://", "https://", "data:"))
        if not is_url_src:
            if is_hidden:
                html_out = _inject_before_close(html_out, _HIDDEN_COLLAPSE_SNIPPET)
            elif not scrolling:
                html_out = _inject_before_close(html_out, _NO_SCROLL_SNIPPET)

            if html_out.startswith("/"):
                html_out = " " + html_out

        kwargs: dict = {}
        if is_hidden:
            kwargs["height"] = 1
            kwargs["width"] = 1
            kwargs["alt"] = alt if alt is not None else HIDDEN_IFRAME_ALT
            kwargs["tab_index"] = -1 if tab_index is None else tab_index
        else:
            if height is not None:
                kwargs["height"] = max(1, int(height)) if isinstance(height, (int, float)) else height
            if width is not None:
                kwargs["width"] = max(1, int(width)) if isinstance(width, (int, float)) else width
            if alt is not None:
                kwargs["alt"] = alt
            if tab_index is not None:
                kwargs["tab_index"] = tab_index

        return st.iframe(html_out, **kwargs)
    else:
        import streamlit.components.v1 as _st_comp_v1
        kwargs = {}
        if height is not None:
            kwargs["height"] = 0 if is_hidden else height
        if width is not None:
            kwargs["width"] = 0 if is_hidden else width
        if tab_index is not None:
            kwargs["tab_index"] = tab_index
        return _st_comp_v1.html(html, scrolling=scrolling, **kwargs)


class _ComponentsShim:
    """
    Drop-in compatibility shim matching `streamlit.components.v1` so any legacy
    `components.html(...)` or `components.iframe(...)` call (e.g. introduced via git merge)
    routes safely through `render_html_iframe` (`st.iframe`) without NameError or warnings.
    """

    @staticmethod
    def html(
        html: str,
        width: Union[int, Literal["stretch", "content"], None] = None,
        height: Union[int, Literal["stretch", "content"], None] = None,
        scrolling: bool = False,
        *,
        tab_index: int | None = None,
    ):
        return render_html_iframe(
            html,
            height=height,
            width=width,
            scrolling=scrolling,
            tab_index=tab_index,
        )

    @staticmethod
    def iframe(
        src: str,
        width: Union[int, Literal["stretch", "content"], None] = None,
        height: Union[int, Literal["stretch", "content"], None] = None,
        scrolling: bool = False,
        *,
        tab_index: int | None = None,
    ):
        return render_html_iframe(
            src,
            height=height,
            width=width,
            scrolling=scrolling,
            tab_index=tab_index,
        )

    def __getattr__(self, name: str):
        import streamlit.components.v1 as _st_comp_v1
        return getattr(_st_comp_v1, name)


components_shim = _ComponentsShim()
