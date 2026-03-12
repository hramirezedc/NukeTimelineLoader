"""
NukeTimelineLoader - nt_loader package init.

Ensures required third-party dependencies (e.g. requests) are available
before the rest of the package is imported. This handles environments like
Hiero/Nuke 17+ where the bundled Python may not include these packages.
"""

import subprocess
import sys
import os

# Dependencies that must be importable for nt_loader to work.
_REQUIRED_PACKAGES = {
    "requests": "requests",
    "PIL": "pillow",
    "fileseq": "fileseq",
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
        subprocess.check_call(
            [
                sys.executable, "-m", "pip", "install",
                "--target", target,
                "--upgrade",
            ]
            + missing,
            timeout=120,
        )
        print("[NukeTimelineLoader] Dependencies installed successfully.")
    except Exception as exc:
        print(
            f"[NukeTimelineLoader] WARNING: Could not auto-install dependencies: {exc}\n"
            f"  Please install manually: pip install {' '.join(missing)}\n"
            f"  Or use ntl_pip_dependency_installer.py"
        )


_ensure_dependencies()
