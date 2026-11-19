# Troubleshooting

## Sign-in fails with "Invalid member ID or password"

- Use the exact member ID from the app (numbers only, no spaces) and the
  current app password. If you can log into the phone app, the same
  details work here.
- Repeated failures lock nothing on our side, but the service may
  throttle you — wait a few minutes between attempts.

## "Failed to connect"

- The Enterprise API occasionally returns 500s. The integration retries
  on the next poll (default every 5 minutes); check
  **Settings → Devices & services → Enterprise Car Club** for the last
  successful update time.

## Re-authentication requested

- If your password changes, Home Assistant prompts you to re-enter it on
  the integration card. Enter the new password; no need to remove and
  re-add the integration.

## A favorite shows "unknown"

- The vehicle left the latest search results (booked out or moved).
  It returns automatically when it reappears.

## Sensor attributes look empty in history

- Per-vehicle timeslot schedules are deliberately excluded from recorded
  state (database size limits). Use the `enterprise_carclub.check_availability`
  action in **Developer tools → Actions** for full schedules.
