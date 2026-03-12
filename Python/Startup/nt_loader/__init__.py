"""
NukeTimelineLoader - nt_loader package init.

Ensures required third-party dependencies (e.g. requests) are available
before the rest of the package is imported. This handles environments like
Hiero/Nuke 17+ where the bundled Python may not include these packages.

Also patches PySide6.QtCore with Qt5 resource stubs (qRegisterResourceData)
that tk-core expects but PySide6 removed.
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
    directly on PySide6.QtCore AND on any PySide2.QtCore shim already in
    sys.modules (e.g. from menu.py).  This is safe to call multiple times.
    """
    _stub = lambda *args, **kwargs: True

    for mod_name in ("PySide6.QtCore", "PySide2.QtCore"):
        mod = sys.modules.get(mod_name)
        if mod is not None:
            if not hasattr(mod, "qRegisterResourceData"):
                mod.qRegisterResourceData = _stub
            if not hasattr(mod, "qUnregisterResourceData"):
                mod.qUnregisterResourceData = _stub

    # Also patch the real PySide6.QtCore if not yet in sys.modules
    try:
        from PySide6 import QtCore as _qtcore
        if not hasattr(_qtcore, "qRegisterResourceData"):
            _qtcore.qRegisterResourceData = _stub
        if not hasattr(_qtcore, "qUnregisterResourceData"):
            _qtcore.qUnregisterResourceData = _stub
    except ImportError:
        pass


_patch_qt_resource_functions()

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
