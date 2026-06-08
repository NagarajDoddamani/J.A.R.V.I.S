from __future__ import annotations

from typing import Protocol

from backend.settings.domain.model import Setting, SettingId, SettingsProfile


class SettingsRepositoryPort(Protocol):
    """Repository port for ``SettingsProfile`` persistence.

    An implementation persists the full ``SettingsProfile`` aggregate
    to a concrete store. The profile is the aggregate root; individual
    ``Setting`` values are accessible through the profile or via the
    convenience query ``find_by_key``.

    All methods are synchronous. Adapters that require async should
    use ``asyncio.to_thread`` or wrap in an async adapter class.
    """

    def save(self, profile: SettingsProfile) -> None:
        """Persist (insert or update) a settings profile.

        If a profile with the same ``profile_id`` already exists the
        implementation replaces it (upsert semantics). The profile
        carries its own schema version; version conflicts between the
        stored and incoming profile may raise an adapter-level
        ``SchemaVersionMismatchError``.

        Parameters
        ----------
        profile:
            The ``SettingsProfile`` aggregate to persist. Must have
            a valid ``profile_id`` and at least zero settings.
        """
        ...

    def find_by_id(self, profile_id: SettingId) -> SettingsProfile | None:
        """Retrieve a settings profile by its unique identifier.

        Parameters
        ----------
        profile_id:
            The ``SettingId`` to look up.

        Returns
        -------
        The matching ``SettingsProfile``, or ``None`` if no profile
        exists with the given identifier.
        """
        ...

    def find_by_key(self, key: str) -> Setting | None:
        """Retrieve a single setting value by its key.

        This is a convenience query that searches across all stored
        profiles. If key uniqueness is guaranteed per-profile, the
        implementation should return the first match.

        Parameters
        ----------
        key:
            The dotted setting key (e.g. ``"ui.theme"``).

        Returns
        -------
        The matching ``Setting``, or ``None`` if no setting exists
        with the given key.
        """
        ...

    def get_all(self) -> list[Setting]:
        """List all settings across all profiles.

        Returns
        -------
        A flat list of every ``Setting`` known to the store.
        """
        ...
