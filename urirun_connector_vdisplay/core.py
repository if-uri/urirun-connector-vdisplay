# Author: Tom Sapletta · Part of the ifURI solution.
"""urirun-connector-vdisplay — native URI surface over the vdisplay package.

vdisplay already enumerates windows/monitors across OS backends (X11, Wayland, vision)
and describes each with a natural-language ``nl`` field. It shipped only a thin
``uri2vdisplay`` string bridge, not a served connector — so a urirun node/flow/readiness
kernel could not consume it. This connector wraps vdisplay's programmatic API
(``payloads``/``discovery``) as first-class ``vdisplay://`` routes.

Why this exists: the kvm connector's atspi window list could not see Chrome windows on
GNOME-Wayland; vdisplay's multi-backend enumeration can. The readiness kernel consumes
``vdisplay://host/windows/query/list`` instead of the ad-hoc atspi path.

Design rules followed (the template for URI-native library wrappers):
  * LAZY imports — ``import vdisplay`` only inside handlers, never at module top, so the
    connector import, bindings generation and the node stay light (vdisplay pulls heavy
    optional deps like playwright on some paths).
  * read-only queries run in-process (``isolated=False``); no mutation of the host.
  * every route returns a urirun envelope; failures are ``urirun.fail`` with the reason.
"""
from __future__ import annotations

from typing import Any

import urirun

CONNECTOR_ID = "vdisplay"
conn = urirun.connector(CONNECTOR_ID, scheme="vdisplay")


def _ok(**kw: Any) -> dict[str, Any]:
    return urirun.ok(connector=CONNECTOR_ID, **kw)


def _fail(msg: str, action: str) -> dict[str, Any]:
    return urirun.fail(msg, connector=CONNECTOR_ID, action=action)


def _discovery() -> Any:
    """Lazy accessor for the LIGHT enumeration path. Deliberately ``discovery`` (not
    ``payloads``): payloads.windows_payload pulls playwright via its nl/session enrichment,
    while discovery.list_windows/list_monitors return the same nl-tagged records WITHOUT it —
    so the connector (and node) never load a browser engine just to list windows."""
    from vdisplay import discovery
    return discovery


@conn.handler("windows/query/list", isolated=False,
              meta={"label": "List windows (multi-backend, each with an nl description)"})
def windows_list(display: str = "", apps_only: bool = False, match_app: str = "",
                 min_width: int = 0, min_height: int = 0) -> dict[str, Any]:
    """Enumerate windows via vdisplay's best backend for the live session. Unlike a single
    atspi/X11 probe this sees app windows (incl. Chrome on Wayland) and tags each with
    ``nl`` — the grounding a resolver needs to pick an unambiguous window."""
    try:
        d = _discovery()
        wins = d.list_windows(
            display or None, apps_only=bool(apps_only),
            min_width=int(min_width), min_height=int(min_height),
            match_app=match_app or None,
        )
        resolved = d.resolve_host_display(display or None)
    except Exception as exc:  # noqa: BLE001
        return _fail(str(exc), "vdisplay-windows")
    return _ok(action="vdisplay-windows", resolved_display=resolved,
               window_count=len(wins), windows=wins)


@conn.handler("monitors/query/list", isolated=False,
              meta={"label": "List monitors/outputs (geometry + nl description)"})
def monitors_list(display: str = "") -> dict[str, Any]:
    try:
        d = _discovery()
        mons = d.list_monitors(display or None)
        resolved = d.resolve_host_display(display or None)
    except Exception as exc:  # noqa: BLE001
        return _fail(str(exc), "vdisplay-monitors")
    return _ok(action="vdisplay-monitors", resolved_display=resolved,
               monitor_count=len(mons), monitors=mons)


@conn.handler("window/query/find", isolated=False,
              meta={"label": "Find windows whose title matches (unambiguous-window grounding)"})
def window_find(title: str = "", display: str = "") -> dict[str, Any]:
    """Resolve a window by title so a plan targets an UNAMBIGUOUS window instead of typing
    into whatever happens to hold focus. Returns matches with their nl + geometry."""
    if not title:
        return _fail("title is required", "vdisplay-window-find")
    try:
        from vdisplay import discovery
        disp = discovery.resolve_host_display(display or None)
        matches = discovery.find_window_suggestions(disp, title)
    except Exception as exc:  # noqa: BLE001
        return _fail(str(exc), "vdisplay-window-find")
    return _ok(action="vdisplay-window-find", title=title, count=len(matches), windows=matches)


@conn.handler("diagnose/query/report", isolated=False,
              meta={"label": "Diagnose the display/session (which enumeration backend is live)"})
def diagnose(display: str = "") -> dict[str, Any]:
    """Honest top-line: resolved display, session type, and whether window enumeration is
    healthy — so a readiness kernel knows if the window signal can be trusted here."""
    try:
        from vdisplay import discovery
        rep = discovery.diagnose_display(display or None)
    except Exception as exc:  # noqa: BLE001
        return _fail(str(exc), "vdisplay-diagnose")
    return _ok(action="vdisplay-diagnose", **rep)


def urirun_bindings() -> dict[str, Any]:
    """Serializable v2 bindings (entry point: urirun.bindings)."""
    return conn.bindings()


def connector_manifest() -> dict[str, Any]:
    return urirun.load_manifest(__package__) or {}


def main(argv: list[str] | None = None) -> int:
    return conn.cli(argv, manifest_prose=urirun.load_manifest(__package__))


if __name__ == "__main__":
    raise SystemExit(main())
