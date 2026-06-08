from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.settings.application.use_cases.dto import (
    GetSettingByKeyRequest,
    GetSettingsRequest,
    GetSettingsResponse,
    PatchSettingsRequest,
    PatchSettingsResponse,
    ResetSettingsRequest,
    ResetSettingsResponse,
    SettingResponse,
)
from backend.settings.application.use_cases.exceptions import (
    SettingNotFoundError,
    SettingsProfileNotFoundError,
)
from backend.settings.bootstrap import (
    get_setting_by_key_use_case,
    get_settings_use_case,
    patch_settings_use_case,
    reset_settings_use_case,
)
from backend.settings.domain.exceptions import SettingsDomainError

router = APIRouter()


# -------------------------------------------------------------------
# GET /settings — Get all settings, optionally filtered by category
# -------------------------------------------------------------------


@router.get(
    "/settings",
    response_model=GetSettingsResponse,
)
def get_settings(
    category: str | None = None,
    use_case=Depends(get_settings_use_case),
) -> GetSettingsResponse:
    try:
        return use_case.execute(GetSettingsRequest(category=category))
    except SettingsDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -------------------------------------------------------------------
# GET /settings/{key} — Get a single setting by key
# -------------------------------------------------------------------


@router.get(
    "/settings/{key}",
    response_model=SettingResponse,
)
def get_setting_by_key(
    key: str,
    use_case=Depends(get_setting_by_key_use_case),
) -> SettingResponse:
    try:
        return use_case.execute(GetSettingByKeyRequest(key=key))
    except SettingNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Setting not found: {key}"
        )


# -------------------------------------------------------------------
# PATCH /settings/{key} — Update a single setting
# -------------------------------------------------------------------


@router.patch(
    "/settings/{key}",
    response_model=PatchSettingsResponse,
)
def patch_single_setting(
    key: str,
    body: dict,
    use_case=Depends(patch_settings_use_case),
) -> PatchSettingsResponse:
    value = body.get("value")
    if value is None:
        raise HTTPException(status_code=422, detail="Missing 'value' field")
    try:
        return use_case.execute(
            PatchSettingsRequest(updates={key: value})
        )
    except SettingsDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except SettingsProfileNotFoundError:
        raise HTTPException(status_code=404, detail="Settings profile not found")


# -------------------------------------------------------------------
# PATCH /settings — Bulk-update multiple settings
# -------------------------------------------------------------------


@router.patch(
    "/settings",
    response_model=PatchSettingsResponse,
)
def patch_settings(
    body: dict,
    use_case=Depends(patch_settings_use_case),
) -> PatchSettingsResponse:
    updates = body.get("updates")
    if not updates or not isinstance(updates, dict):
        raise HTTPException(
            status_code=422, detail="Missing or invalid 'updates' field"
        )
    try:
        return use_case.execute(PatchSettingsRequest(updates=updates))
    except SettingsDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except SettingsProfileNotFoundError:
        raise HTTPException(status_code=404, detail="Settings profile not found")


# -------------------------------------------------------------------
# POST /settings/reset — Reset settings to defaults
# -------------------------------------------------------------------


@router.post(
    "/settings/reset",
    response_model=ResetSettingsResponse,
)
def reset_settings(
    body: dict | None = None,
    use_case=Depends(reset_settings_use_case),
) -> ResetSettingsResponse:
    category = (body or {}).get("category")
    try:
        return use_case.execute(ResetSettingsRequest(category=category))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except SettingsDomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except SettingsProfileNotFoundError:
        raise HTTPException(status_code=404, detail="Settings profile not found")
