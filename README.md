# Enterprise Car Club (Home Assistant)

Unofficial Home Assistant custom integration for **Enterprise Car Club /
CarShare**, built on
[enterprise-carclub-py](https://github.com/KRoperUK/enterprise-carclub-py).
Cloud polling (`iot_class: cloud_polling`), HACS-installable.

> Unofficial integration, not affiliated with or endorsed by Enterprise
> Holdings / EAN Services. Use at your own risk.

## Status

Built on [enterprise-carclub-py](https://github.com/KRoperUK/enterprise-carclub-py)
(same CI/release discipline as
[dimplex-controller-hass](https://github.com/KRoperUK/dimplex-controller-hass)
and [sungrow-hass](https://github.com/KRoperUK/sungrow-hass)).

- **Sensors**: upcoming-reservation count (next booking's id, times, vehicle,
  plate and cost as attributes), driver-message count, nearby available
  vehicles (per-vehicle distance, size class, fuel, seats, next free slot).
- **Binary sensors**: one per favorite vehicle (picked in Configure), on when
  availability is good.
- **Device trackers**: every nearby vehicle plotted on the map with bay
  location and EV battery where reported.
- **Services**: `check_availability` (timeslots for any stack and future
  window) and `book_vehicle` (creates a real, chargeable reservation).
- **Options**: search location (defaults to home), window hours, market, and
  the favorites list.

## Install (HACS)

1. HACS → Integrations → ⋯ → Custom repositories → add this repo (type
   *Integration*).
2. Install **Enterprise Car Club**, restart Home Assistant.
3. Settings → Devices & Services → Add Integration → Enterprise Car Club,
   enter host (default: the EHI cloud) and credentials.

See [docs/installation.md](docs/installation.md).

## Pre-releases

Dogfood builds ship as semver pre-releases (`vX.Y.Z-pr.N` per PR,
`vX.Y.Z-rc.N` on main) so HACS sorts them above the last stable. Details in
[docs/pre-releases.md](docs/pre-releases.md).

## Develop

```bash
pip install -r requirements_test.txt
pytest
ruff check custom_components tests && ruff format --check custom_components tests
mypy
```

Releases use release-please with conventional commits. The integration version
is stamped into `custom_components/enterprise_carclub/manifest.json` and
`const.py` automatically.

## License

MIT.
