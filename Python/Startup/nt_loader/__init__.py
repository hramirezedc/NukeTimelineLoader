"""
NukeTimelineLoader - nt_loader package init.

Ensures required third-party dependencies (e.g. requests) are available
before the rest of the package is imported. This handles environments like
Hiero/Nuke 17+ where the bundled Python may not include these packages.

Also installs a PySide2 → PySide6 compatibility shim so that tk-core
(which expects PySide2) works correctly under Hiero 17+ (PySide6).
"""

import sys
import os

# ---------------------------------------------------------------------------
# PySide2 → PySide6 shim  (must run before any tk-core / tank import)
# ---------------------------------------------------------------------------
def _install_pyside2_shim():
    """Create a fake 'PySide2' package that redirects to PySide6.

    tk-core compiles Qt resource files against PySide2, calling
    PySide2.QtCore.qRegisterResourceData at import time.  Hiero 17+
    ships only PySide6, so we need this shim to satisfy those imports.
    """
    if "PySide2" in sys.modules:
        return  # already available (Hiero 16 or earlier)

    try:
        import PySide6  # noqa: F401 – just checking availability
    except ImportError:
        return  # neither PySide2 nor PySide6 – nothing we can do

    import types
    import importlib

    # Top-level fake PySide2 package
    pyside2 = types.ModuleType("PySide2")
    pyside2.__path__ = []
    pyside2.__package__ = "PySide2"
    sys.modules["PySide2"] = pyside2

    # Map common PySide2 sub-modules to their PySide6 equivalents
    _submodules = [
        "QtCore", "QtGui", "QtWidgets", "QtNetwork", "QtWebEngineWidgets",
        "QtSvg", "QtOpenGL", "QtPrintSupport", "QtUiTools",
    ]
    for name in _submodules:
        target = f"PySide6.{name}"
        try:
            real = importlib.import_module(target)
            alias = f"PySide2.{name}"
            sys.modules[alias] = real
            setattr(pyside2, name, real)
        except ImportError:
            pass

    # Ensure qRegisterResourceData / qUnregisterResourceData exist on QtCore.
    # In PySide6 these moved or were removed; provide no-op stubs so compiled
    # resource files from tk-core don't crash on import.
    from PySide6 import QtCore as _QtCore
    if not hasattr(_QtCore, "qRegisterResourceData"):
        _QtCore.qRegisterResourceData = lambda *args, **kwargs: None
    if not hasattr(_QtCore, "qUnregisterResourceData"):
        _QtCore.qUnregisterResourceData = lambda *args, **kwargs: None


_install_pyside2_shim()

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
