# Automations

## Reminder 30 minutes before a booking starts

Uses the reservations calendar entity
(`calendar.enterprise_car_club_<member_id>_reservations`):

```yaml
automation:
  - alias: "Car club booking reminder"
    trigger:
      - platform: calendar
        entity_id: calendar.enterprise_car_club_10379619_reservations
        event: start
        offset: "-00:30:00"
    action:
      - service: notify.mobile_app
        data:
          message: "Car booked: {{ trigger.calendar_event.summary }} at {{ trigger.calendar_event.location }}"
```

## Notify when a favorite vehicle becomes available

```yaml
# Find your entity ID under Developer tools → States (it looks like
# binary_sensor.ford_transit_custom_ev_blossom_street_ancoats_m4_6aj_54978).
automation:
  - alias: "Favorite car free"
    trigger:
      - platform: state
        entity_id: binary_sensor.<your_favorite_vehicle>_available
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Favorite car is available to book"
```

## Check a future window from an automation

Call the `enterprise_carclub.check_availability` action with a `stack_id`
plus ISO start/end datetimes; the response lists per-slot availability.
Use the returned slots to decide whether to fire `book_vehicle`.
