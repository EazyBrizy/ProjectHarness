"""Capability-specific test prerequisites; never emulate Windows privileges."""
import os


def symlink_or_skip(test, link, target, *, directory=False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        if os.name == 'nt' and getattr(exc, 'winerror', None) == 1314:
            test.skipTest('NOT RUN: native file symlink creation requires a Windows privilege unavailable to this non-admin user')
        raise
