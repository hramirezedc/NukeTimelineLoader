"""
NukeTimelineLoader - nt_loader package init.

Ensures required third-party dependencies (e.g. requests) are available
before the rest of the package is imported. This handles environments like
Hiero/Nuke 17+ where the bundled Python may not include these packages.

Also pre-imports tk-core (tank) using PySide6 natively so its QtImporter
picks the correct code path, and patches Qt resource stubs removed in Qt6.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Qt5 resource function stubs  (must run before any tk-core / tank import)
# ---------------------------------------------------------------------------
def _patch_qt_resource_functions():
    """Ensure qRegisterResourceData / qUnregisterResourceData exist.

    tk-core's compiled Qt resource files call these functions which existed
    in PySide2 (Qt5) but were removed in PySide6 (Qt6).  We add no-op stubs
    directly on PySide6.QtCore.  This is safe to call multiple times.
    """
    _stub = lambda *args, **kwargs: True

    try:
        from PySide6 import QtCore as _qtcore
        if not hasattr(_qtcore, "qRegisterResourceData"):
            _qtcore.qRegisterResourceData = _stub
        if not hasattr(_qtcore, "qUnregisterResourceData"):
            _qtcore.qUnregisterResourceData = _stub
    except ImportError:
        pass

    # Also patch any PySide2.QtCore shim already in sys.modules
    mod = sys.modules.get("PySide2.QtCore")
    if mod is not None:
        if not hasattr(mod, "qRegisterResourceData"):
            mod.qRegisterResourceData = _stub
        if not hasattr(mod, "qUnregisterResourceData"):
            mod.qUnregisterResourceData = _stub


_patch_qt_resource_functions()


# ---------------------------------------------------------------------------
# Pre-import tank using PySide6 natively
# ---------------------------------------------------------------------------
def _import_tank_with_pyside6():
    """Pre-import tank while PySide2 shim is hidden from sys.modules.

    tk-core's QtImporter tries PySide2 first, then PySide6.  The PySide2
    shim from menu.py makes the PySide2 path succeed initially, but then
    pyside2_patcher fails because the underlying modules are PySide6
    (e.g. QTextCodec was removed in Qt6).

    By temporarily hiding the PySide2 shim, QtImporter skips the PySide2
    path and uses its native PySide6 support (pyside6_patcher) instead.
    Once tank is imported, we restore the PySide2 shim for any other code
    that may depend on it.
    """
    # Save and temporarily remove PySide2/shiboken2 shim entries
    saved = {}
    for key in list(sys.modules):
        if key == "PySide2" or key.startswith("PySide2.") or key == "shiboken2":
            saved[key] = sys.modules.pop(key)

    try:
        import tank  # noqa: F401 - triggers QtImporter which now uses PySide6
        print("[NukeTimelineLoader] tank imported successfully via PySide6 path")
    except Exception as exc:
        print(f"[NukeTimelineLoader] WARNING: tank pre-import failed: {exc}")
    finally:
        # Restore PySide2 shim for other code that depends on it
        sys.modules.update(saved)


# Only run on PySide6 environments (Hiero 17+) where the PySide2 shim exists
if "PySide2" in sys.modules:
    try:
        import PySide6  # noqa: F401 - check if we're in a PySide6 environment
        _import_tank_with_pyside6()
    except ImportError:
        pass

# ---------------------------------------------------------------------------
# Auto-install missing dependencies
# ---------------------------------------------------------------------------
# Format: { "import_name": "pip_name_or_url" }
_REQUIRED_PACKAGES = {
    "requests": "requests",
    "PIL": "pillow",
    "fileseq": "fileseq",
    "tank_vendor": "git+https://github.com/shotgunsoftware/tk-core.git@v0.21.7",
}


def _ensure_dependencies():
    """Check for required packages and pip-install any that are missing."""
    missing = []
    for import_name, pip_name in _REQUIRED_PACKAGES.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return

    # Determine a target directory for installed packages
    target = os.environ.get("NTL_SITE_PACKAGES")
    if not target:
        # Use user site-packages as a safe default
        import site
        target = site.getusersitepackages()

    os.makedirs(target, exist_ok=True)

    # Ensure target is on sys.path so subsequent imports find the packages
    if target not in sys.path:
        sys.path.insert(0, target)

    print(f"[NukeTimelineLoader] Installing missing dependencies: {missing}")
    try:
        # Use pip._internal instead of subprocess because in Nuke/Hiero 17+
        # sys.executable points to the Nuke binary (not a Python interpreter),
        # which causes SIGSEGV when invoked with "-m pip".
        from pip._internal.cli.main import main as pip_main
        pip_args = ["install", "--target", target, "--upgrade"] + missing
        exit_code = pip_main(pip_args)
        if exit_code == 0:
            print("[NukeTimelineLoader] Dependencies installed successfully.")
            # Refresh sys.path so newly installed packages are importable
            import importlib
            importlib.invalidate_caches()
        else:
            raise RuntimeError(f"pip exited with code {exit_code}")
    except Exception as exc:
        print(
            f"[NukeTimelineLoader] WARNING: Could not auto-install dependencies: {exc}\n"
            f"  Please install manually by running in a terminal:\n"
            f"    pip3 install --target \"{target}\" {' '.join(missing)}\n"
            f"  Or use ntl_pip_dependency_installer.py"
        )


_ensure_dependencies()
