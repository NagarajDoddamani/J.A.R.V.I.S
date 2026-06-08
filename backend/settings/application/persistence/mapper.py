from __future__ import annotations

from typing import Protocol

from backend.settings.application.persistence.dto import (
    SettingStorageDto,
    SettingsOutboxStorageDto,
    SettingsProfileStorageDto,
)
from backend.settings.domain.model import (
    Setting,
    SettingsProfile,
    SettingsReset,
    SettingUpdated,
)


class SettingMapperProtocol(Protocol):
    """Bidirectional mapping between ``Setting`` value objects and ``SettingStorageDto``.

    Flattens the ``SettingDefinition`` metadata (category, scope,
    value_type) into the DTO's primitive fields and reconstructs
    them on the reverse path.
    """

    def domain_to_dto(self, setting: Setting, profile_id: str) -> SettingStorageDto:
        """Convert a domain ``Setting`` to its storage DTO.

        Parameters
        ----------
        setting:
            The domain value object.
        profile_id:
            The owning profile's ID as a string.

        Returns
        -------
        A flat ``SettingStorageDto``.
        """
        ...

    def dto_to_domain(self, dto: SettingStorageDto) -> Setting:
        """Reconstruct a domain ``Setting`` from its storage DTO.

        Parameters
        ----------
        dto:
            The flat storage representation.

        Returns
        -------
        A fully reconstructed ``Setting`` value object.
        """
        ...


class SettingsProfileMapperProtocol(Protocol):
    """Bidirectional mapping between ``SettingsProfile`` and storage DTOs.

    A single profile maps to one ``SettingsProfileStorageDto`` and
    zero or more ``SettingStorageDto`` instances (one per setting).
    Implementations coordinate the split and merge.
    """

    def domain_to_dto(
        self, profile: SettingsProfile
    ) -> SettingsProfileStorageDto:
        """Convert a domain ``SettingsProfile`` to its profile-level DTO.

        Parameters
        ----------
        profile:
            The domain aggregate root.

        Returns
        -------
        A flat ``SettingsProfileStorageDto`` containing identity
        and metadata only (no settings).
        """
        ...

    def dto_to_domain(
        self, dto: SettingsProfileStorageDto, settings: list[Setting]
    ) -> SettingsProfile:
        """Reconstruct a domain ``SettingsProfile`` from storage DTOs.

        Parameters
        ----------
        dto:
            The profile-level storage DTO.
        settings:
            The list of ``Setting`` value objects that belong to this
            profile, already reconstructed via ``SettingMapperProtocol``.

        Returns
        -------
        A fully reconstructed ``SettingsProfile`` aggregate.
        """
        ...

    def domain_settings_to_dtos(
        self, profile: SettingsProfile
    ) -> list[SettingStorageDto]:
        """Convert all settings in a profile to storage DTOs.

        Parameters
        ----------
        profile:
            The domain aggregate root whose settings should be
            flattened.

        Returns
        -------
        A list of ``SettingStorageDto`` instances, one per setting
        in the profile.
        """
        ...


class SettingsOutboxMapperProtocol(Protocol):
    """Mapping between settings domain events and ``SettingsOutboxStorageDto``.

    Converts ``SettingUpdated`` and ``SettingsReset`` events into a
    flattened outbox row and reconstructs them on the reverse path.
    """

    def domain_to_dto(self, event: SettingUpdated | SettingsReset) -> SettingsOutboxStorageDto:
        """Convert a domain event to its outbox storage DTO.

        Parameters
        ----------
        event:
            Either a ``SettingUpdated`` or ``SettingsReset`` event.

        Returns
        -------
        A flat ``SettingsOutboxStorageDto``.  The ``published``
        flag is always ``False``.
        """
        ...

    def dto_to_domain(self, dto: SettingsOutboxStorageDto) -> SettingUpdated | SettingsReset:
        """Reconstruct a domain event from its outbox storage DTO.

        Parameters
        ----------
        dto:
            The flat outbox storage representation.

        Returns
        -------
        Either a ``SettingUpdated`` or ``SettingsReset`` event,
        as determined by ``dto.event_type``.
        """
        ...
