import sys

import pytest

from quant_brain.harness.paths import (
    PathViolation,
    assert_write_allowed,
    is_write_allowed,
    resolve_write_target,
)

ALLOWED = ("brain/00_Inbox/Raw_Research/", "brain/00_Inbox/Source_Snapshots/")


def test_write_inside_allowed_directory_is_permitted(tmp_path):
    resolved = resolve_write_target(
        tmp_path, "brain/00_Inbox/Raw_Research/RQ-1.md", ALLOWED
    )

    assert resolved == (tmp_path / "brain/00_Inbox/Raw_Research/RQ-1.md").resolve()


def test_nested_write_inside_allowed_directory_is_permitted(tmp_path):
    assert is_write_allowed(
        tmp_path, "brain/00_Inbox/Source_Snapshots/2026-08-28/abc.md", ALLOWED
    )


def test_write_to_the_allowed_directory_itself_is_permitted(tmp_path):
    assert is_write_allowed(tmp_path, "brain/00_Inbox/Raw_Research/", ALLOWED)


def test_sibling_directory_is_blocked(tmp_path):
    with pytest.raises(PathViolation):
        resolve_write_target(tmp_path, "brain/01_Sources/note.md", ALLOWED)


def test_parent_traversal_is_blocked(tmp_path):
    """A path with an allowed prefix but an unallowed destination must fail.

    This is why enforcement resolves paths instead of comparing string prefixes.
    """
    with pytest.raises(PathViolation):
        resolve_write_target(
            tmp_path, "brain/00_Inbox/Raw_Research/../../../escaped.md", ALLOWED
        )


def test_traversal_escaping_the_project_root_is_blocked(tmp_path):
    with pytest.raises(PathViolation):
        resolve_write_target(tmp_path, "../outside.md", ALLOWED)


def test_absolute_path_outside_root_is_blocked(tmp_path):
    outside = tmp_path.parent / "elsewhere.md"

    with pytest.raises(PathViolation):
        resolve_write_target(tmp_path, str(outside), ALLOWED)


def test_empty_allowed_list_blocks_everything(tmp_path):
    with pytest.raises(PathViolation):
        resolve_write_target(tmp_path, "brain/00_Inbox/Raw_Research/x.md", ())


def test_declared_path_escaping_root_cannot_authorize_a_write(tmp_path):
    """A malformed declaration must not become an escape hatch."""
    with pytest.raises(PathViolation):
        resolve_write_target(tmp_path, "../outside.md", ("../",))


@pytest.mark.skipif(
    sys.platform == "win32", reason="symlink creation needs elevation on Windows"
)
def test_symlink_escaping_allowed_directory_is_blocked(tmp_path):
    allowed_dir = tmp_path / "brain" / "00_Inbox" / "Raw_Research"
    allowed_dir.mkdir(parents=True)
    secret_dir = tmp_path / "brain" / "01_Sources"
    secret_dir.mkdir(parents=True)
    (allowed_dir / "sneaky").symlink_to(secret_dir, target_is_directory=True)

    with pytest.raises(PathViolation):
        resolve_write_target(
            tmp_path, "brain/00_Inbox/Raw_Research/sneaky/leak.md", ALLOWED
        )


def test_assert_write_allowed_raises_with_useful_message(tmp_path):
    with pytest.raises(PathViolation) as exc:
        assert_write_allowed(tmp_path, "brain/01_Sources/x.md", ALLOWED)

    assert "01_Sources" in str(exc.value)
    assert "Raw_Research" in str(exc.value)


def test_windows_style_separators_are_normalized(tmp_path):
    assert is_write_allowed(
        tmp_path, "brain\\00_Inbox\\Raw_Research\\note.md", ALLOWED
    )
