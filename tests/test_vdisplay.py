# Author: Tom Sapletta · Part of the ifURI solution.
from __future__ import annotations

import json

import urirun
from urirun_connector_vdisplay import (
    CONNECTOR_ID,
    urirun_bindings,
    window_find,
    windows_list,
)

ROUTES = {
    "vdisplay://host/windows/query/list",
    "vdisplay://host/monitors/query/list",
    "vdisplay://host/window/query/find",
    "vdisplay://host/diagnose/query/report",
}


def test_connector_id():
    assert CONNECTOR_ID == "vdisplay"


def test_bindings_serializable_and_complete():
    b = urirun_bindings()["bindings"]
    assert set(b) == ROUTES
    json.dumps(urirun_bindings())  # no live-ref leaks
    # read-only enumeration is in-process (light node), not an isolated subprocess spawn
    assert b["vdisplay://host/windows/query/list"]["adapter"] == "local-function"


def test_lazy_import_no_vdisplay_at_module_top():
    # Importing the connector must NOT import vdisplay (which can pull heavy optional deps).
    import sys
    import importlib

    for m in [m for m in list(sys.modules) if m == "vdisplay" or m.startswith("vdisplay.")]:
        del sys.modules[m]
    importlib.reload(importlib.import_module("urirun_connector_vdisplay.core"))
    assert "vdisplay" not in sys.modules, "connector import pulled vdisplay eagerly"


def test_window_find_requires_title():
    r = window_find(title="")
    assert r["ok"] is False


def test_windows_list_returns_envelope():
    # Runs against the live session; on a headless CI this may fail to enumerate — either way
    # it must return a well-formed urirun envelope, never raise.
    r = windows_list()
    assert "ok" in r
    if r["ok"]:
        assert "windows" in r
