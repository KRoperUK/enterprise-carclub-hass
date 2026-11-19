# Research: HA developer docs + peer integrations

Sources are primary only: `contributors.home-assistant.io` docs and `github.com` repos.
No blog evidence. All URLs verified live during research (Nov 2026).

## Part 1a — Quality scale: Silver rules (10)

Full list: <https://contributors.home-assistant.io/core/quality-scale/rules/> ·
Tiers: <https://contributors.home-assistant.io/core/quality-scale/tiers/>

| Rule | Ask (one line) | Verdict for carclub |
|---|---|---|
| `action-exceptions` | Actions raise `ServiceValidationError`/`HomeAssistantError`, never error codes | Do: wrap booking actions; no bool/error-code returns |
| `config-entry-unloading` | Unload/reload without restart | Do: implement `async_unload_entry` from day one |
| `docs-configuration-parameters` | Docs describe every options-flow field | Do: document polling interval, station filter, etc. |
| `docs-installation-parameters` | Docs describe every setup field | Do: document API key / member ID fields |
| `entity-unavailable` | Entities `unavailable` when API unreachable | Do: drive via coordinator (`available` from last-success) |
| `integration-owner` | ≥1 code owner in manifest | Do: add `codeowners` |
| `log-when-unavailable` | Log once on lost return, once on recovery | Do: rely on coordinator default, no per-poll logs |
| `parallel-updates` | Each platform sets `PARALLEL_UPDATES` | Do: set `PARALLEL_UPDATES = 1` (shared fleet API) |
| `reauthentication-flow` | Re-auth from UI, no re-add | Do: OAuth/token refresh + `async_step_reauth` (Silver gate) |
| `test-coverage` | >95% coverage per module | Do: keep tests beside every module; blocks Silver |

## Part 1a — Quality scale: Gold rules (21)

| Rule | Ask (one line) | Verdict for carclub |
|---|---|---|
| `devices` | Entities grouped in devices w/ full `DeviceInfo` | Do: one device per vehicle (VIN identifiers) |
| `diagnostics` | Redacted diagnostics download | Do: `diagnostics.py` + `async_redact_data` (tokens, plate, GPS) |
| `discovery` | Auto-discover where possible | Exempt w/ reason: cloud fleet API has no local discovery |
| `discovery-update-info` | Update address on rediscovery | Exempt: same reason (no discovery) |
| `docs-data-update` | Docs: how/often data updates | Do: document poll interval + webhook/push if added |
| `docs-examples` | Automation examples/blueprints | Do: "booking starts in 15 min" notify example |
| `docs-known-limitations` | Known limitations listed | Do: rate limits, station coverage |
| `docs-supported-devices` | Supported/unsupported list | Do: vehicle classes supported by fleet API |
| `docs-supported-functions` | Entities + functions documented | Do: per-platform table |
| `docs-troubleshooting` | Self-serve troubleshooting | Do: auth-expired, rate-limit sections |
| `docs-use-cases` | What users can do with it | Do: 2–3 use cases (pre-trip check, billing sensor) |
| `dynamic-devices` | New devices appear without reload | Do: add vehicles via coordinator listener |
| `entity-category` | Config/diagnostic entities categorized | Do: API-quota, raw-payload sensors = `diagnostic` |
| `entity-device-class` | Device class wherever one fits | Do: `battery`, `timestamp`, `distance`, `enum` |
| `entity-disabled-by-default` | Noisy/niche entities off by default | Do: disable per-station debug sensors |
| `entity-translations` | Names from `strings.json` via key | Do: `has_entity_name` + `translation_key` everywhere |
| `exception-translations` | User errors from `strings.json` | Do: translate `invalid_auth`, booking-failed errors |
| `icon-translations` | Icons in `icons.json`, not Python | Do: no hardcoded `icon=` |
| `reconfiguration-flow` | Change setup (host/region) from UI | Do: `async_step_reconfigure` for endpoint/region |
| `repair-issues` | `issue_registry` issues for user-fixable problems | Do: API-sunset / plan-quota warnings |
| `stale-devices` | Removed vehicles cleaned up | Do: prune devices absent from API |

Platinum (`async-dependency`, `inject-websession`, `strict-typing`) is out of scope;
note `inject-websession` anyway: pass HA's `aiohttp` session into the API client.
Rule details: <https://contributors.home-assistant.io/core/quality-scale/>

## Part 1b — Key rules from developer docs

| Area | Key rule | Verdict |
|---|---|---|
| Config flow | UI-only setup; `data_description` per field; credentials in `data`, behavior in `options`; `unique_id` + `_abort_if_unique_id_configured`; test connection before entry. <https://contributors.home-assistant.io/core/integrations/config-flow/> | Do all five; options hold poll interval, never tokens |
| Options flow | `OptionsFlowWithReload`; `add_suggested_values_to_schema`; never host/credentials; polling interval is NOT an option. <https://contributors.home-assistant.io/core/integrations/options-flow/> | Do: reload-on-save options for filters only |
| Reauth | Raise `ConfigEntryAuthFailed` from `async_setup_entry`/coordinator → flow starts; `async_step_reauth` + `async_update_reload_and_abort`. Reconfigure = separate `reconfigure` step for host/region. <https://contributors.home-assistant.io/core/integrations/reauth-reconfigure/> | Do: map 401/token-expiry → `ConfigEntryAuthFailed` |
| Diagnostics | `diagnostics.py`: `async_get_config_entry_diagnostics` (+ per-device variant); redact tokens/keys/GPS/PII with `async_redact_data`; snapshot-test output. <https://contributors.home-assistant.io/core/integrations/diagnostics/> | Do: redact member ID, plate, coords; add snapshot test |
| Repairs | `issue_registry.async_create_issue` with `translation_key`, severity, `is_fixable` + repair flow; tie to `config_entry_id`. <https://contributors.home-assistant.io/core/integrations/repairs/> | Do: quota/deprecation warnings as WARNING issues |
| Entity naming/i18n | `has_entity_name=True` (Bronze); name via `_attr_translation_key` → `strings.json` `entity.<platform>.<key>.name`; device-class names need no key; icons in `icons.json`; action/exception strings translated. <https://contributors.home-assistant.io/core/quality-scale/entity-translations/> <https://contributors.home-assistant.io/core/integrations/translations/> | Do: no hardcoded English names/icons |
| device_tracker | `TrackerEntity` for GPS-reporting things (car): set `latitude`/`longitude` (+`location_accuracy`) OR `in_zones`; `SourceType.GPS`; battery via separate `sensor` (device class `battery`). <https://contributors.home-assistant.io/core/entities/device-tracker/> | Do: one `TrackerEntity` per vehicle, GPS source |
| Services + responses | Register in `async_setup` via `services.py::async_setup_services` (Bronze `action-setup`); target entity/device/`config_entry_id` explicitly; `SupportsResponse.NONE/OPTIONAL/ONLY`; response = JSON dict, errors = exceptions; describe in `services.yaml` (+ translations). <https://contributors.home-assistant.io/core/integrations/actions/> | Do: booking lookup = `ONLY` response; book/cancel = `OPTIONAL` |
| DataUpdateCoordinator | One poll for all entities in `coordinator.py`; always pass `config_entry`; `update_interval` fits data; `_async_setup` for one-shot fetch; `_async_update_data` maps auth→`ConfigEntryAuthFailed`, transient→`UpdateFailed`. <https://contributors.home-assistant.io/core/integrations/fetching-data/> | Do: single fleet coordinator, 60–300 s interval |
| Brands layout | Core: PR to `home-assistant/brands`, folder `core_integrations/<domain>/` with `icon.png` (+`logo.png`, `dark_*`, `@2x`). Custom: ship `brand/` inside `custom_components/<domain>/` (HA ≥ 2026.3 proxy). PNG, trimmed, transparent, optimized. <https://github.com/home-assistant/brands> <https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/> | Do: add `custom_components/carclub/brand/icon.png` (+`logo.png`, `@2x`) |
| File layout | `manifest.json`, `__init__.py`, `const.py`, `config_flow.py`, `coordinator.py`, `entity.py`, `<platform>.py`, `strings.json`, `icons.json`, `services.yaml`, `diagnostics.py`, `quality_scale.yaml`. <https://contributors.home-assistant.io/core/integrations/file-structure/> | Do: follow exactly; coordinator + base entity from start |

## Part 2 — Peer integrations

**Result: no car-sharing / car-rental / vehicle-booking integration exists.**
Searched GitHub for `zipcar/ubeeqo/communauto/carshare/car-rental custom_components`
and the HACS default catalog (`hacs/default`): zero hits for booking a shared car.
Closest analogues below (all primary sources).

| Analogue | Platforms / auth | Worth copying |
|---|---|---|
| `wbyoung/smartcar` (HACS custom, multi-brand vehicle API). <https://github.com/wbyoung/smartcar> | `device_tracker`, `sensor`, `binary_sensor`, `number`, `switch`, `lock` per vehicle; OAuth2 (Smartcar client ID/secret + vehicle-account login); optional webhooks for push | Per-vehicle device with full entity spread; OAuth + push-webhook pattern; permission-gated entities (plan-dependent signals) |
| `alandtse/tesla` (HACS custom, ex-core fork). <https://github.com/alandtse/tesla> | `device_tracker` (car location + route destination), `binary_sensor`, `button`, `climate`, `cover`, `lock`, `select`, `sensor`, `switch`; refresh-token auth | `TrackerEntity` GPS pattern for a car; `button` for wake/force-refresh; disabled-by-default for niche entities (HomeLink) |
| Core `calendar` entity model (booking analogue; e.g. CalDAV/Google-style). <https://contributors.home-assistant.io/core/entities/calendar/> | `CalendarEntity`, iCalendar RFC 5545, `CREATE_EVENT`/`UPDATE_EVENT`/`DELETE_EVENT` features | Model reservations as `calendar` entities (state = active booking) + `SupportsResponse.ONLY` action for availability search; keep unknown RFC fields on write |

**Honest gap:** nobody has solved shared-fleet booking in HA — no booking-action,
per-member auth, or station-availability sensor to imitate. Our differentiators
(calendar-per-vehicle + book/cancel actions with responses) are novel; copy the
vehicle-entity discipline from smartcar/tesla instead.
