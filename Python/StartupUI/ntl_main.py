import os
import sys

import hiero
import nt_loader.fn_sg_func
from nt_loader.fn_ui import LoadingDialog, ShotgridLoaderWidget
from qtpy.QtCore import QTimer

# Default schema mapping node types to their child-fetching functions
# This approach is to provide a customizable QT treeview that can be
# simply adapted to differing structures and fields used in production
# databases. This can be adapted to structures other than Shotgrid/Flow
DEFAULT_SCHEMA = {
    "root": {"Project": nt_loader.fn_sg_func.sg_tree_get_projects},
    "Project": {
        "Playlist": nt_loader.fn_sg_func.sg_tree_get_playlists,
        "Cut": nt_loader.fn_sg_func.sg_tree_get_cuts,
    },
    "Playlist": {
        "Version": nt_loader.fn_sg_func.sg_tree_get_versions
    },  # Last child is Version
    "Cut": {"Version": nt_loader.fn_sg_func.sg_tree_get_versions},
    # 'Version' nodes have no children
}

# __CUSTOMIZE__ Alternate Schema which needs downstream handling customized by studio
# in nt_loader.fn_sg_func there is also an example of assets
SEQUENCE_SHOT = {
    "root": {"Project": nt_loader.fn_sg_func.sg_tree_get_projects},
    "Project": {
        "Sequence": nt_loader.fn_sg_func.sg_tree_get_sequences,
    },
    "Sequence": {"Shot": nt_loader.fn_sg_func.sg_tree_get_shots},
    "Shot": {"Task": nt_loader.fn_sg_func.sg_tree_get_tasks},
    "Task": {
        "Version": nt_loader.fn_sg_func.sg_tree_get_versions,
        "_searchable": False,
    },  # Last child is Version
    # 'Version' nodes have no children
}
# Schemas mapped by fn_globals.py OPTIONS_BASE
SCHEMA_MAP = {"Playlist and Cuts": DEFAULT_SCHEMA, "Shot and Sequence": SEQUENCE_SHOT}


def after_project_load(event):
    """This sets up NT loader for the new project by hooking into the callback
    "kAfterNewProjectCreated"

    BLACKSHIP OVERRIDE:
        Into the callback "kAfterProjectLoad" instead.

        With ayon, there is a Project called 'Tag Presets'
        which is loaded first, then when we open/create a project,
        'Tag Presets' is updated as a Startup Project.
        Because of that the kAfterProjectLoad event is called multiple times.
        That's why we added a condition for that callback happens after the
        Tag Presets setup.

    Args:
        event (object): Hiero callback event object . Unused in this function
    """
    # BLACKSHIP OVERRIDE
    projects = hiero.core.projects(hiero.core.Project.kStartupProjects)
    if not projects:
        return

    loading_dialog = LoadingDialog("Initializing\nNuke Timeline Loader")
    loading_dialog.show()

    def on_load():
        try:
            session_token, sg = nt_loader.fn_sg_func.session_handler()
            widget = ShotgridLoaderWidget(sg, session_token, SCHEMA_MAP)
            # widget.show()
            wm = hiero.ui.windowManager()
            wm.addWindow(widget)
        finally:
            loading_dialog.close()

    QTimer.singleShot(3000, on_load)


# Register the NTL after_project_load function to be triggered on hiero callback
hiero.core.events.registerInterest("kAfterProjectLoad", after_project_load)
