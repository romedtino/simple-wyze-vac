# Simple Wyze Vacuum for Home Assistant

## NOTE As of 8/20/2021 

Wyze has recently implemented a rate limit on accessing their private APIs. Due to this change, ~~I cannot recommend installing this integration in HA until this all gets sorted out. I might resort to adding a "send_command" that maybe you can use to query Wyze servers. This way it's more event based and it will be on you to make sure you don't hit the rate limits.~~ I have **disabled polling** on this integration.

To update the state of the device, you can do a `vacuum.send_command` with command `update` which will update the state of the vacuum. See vacuum-card example for an implementation.

## General

Simple implementation of the Wyze Vacuum right into Home Assistant. 

## Prerequisites
- Home Assistant 😅
- [HACS](https://hacs.xyz/) Installed in Home Assistant
- Wyze Account without 2FA - Tip: Create a new account that you share just the vacuum with that doesn't have 2FA enabled.

## Installation
1. On Home Assistant go to HACS -> Integration
2. Click menu on the top right
3. Click on custom repositories
4. Add https://github.com/romedtino/simple-wyze-vac as an Integration
5. Install/Add simple-wyze-vac
6. Restart Home Assistant
7. Edit your configuration.yaml and add
```yaml
simple_wyze_vac:
  username: your_wyze_email@email.com
  password: your_wyze_password
```
6. Verify your configuration file is valid
7. Restart Home Assistant

If it all worked out, you should now have Wyze vacuum entity(ies)

## Supported Features
- Start
- Stop / Pause
- Return to Base
- Filter lifespan information (Main filter, main brush and side brush)
- Room Clean (Must use serivce call) Example: ![image](https://user-images.githubusercontent.com/18567128/127786476-ec3dbfcd-66f4-40e6-bfe5-fda0edad191d.png)

```yaml
service: vacuum.send_command
data:
  command: sweep_rooms
  params:
    rooms:
      - Hallway
      - Kitchen
target:
  entity_id: vacuum.theovac
```

- Fan Speed control - `quiet` `standard` `strong` Example: ![image](https://user-images.githubusercontent.com/18567128/128625430-29f77538-b638-481e-8221-0e10ff8618a9.png)

```yaml
service: vacuum.set_fan_speed
data:
  fan_speed: quiet
target:
  entity_id: vacuum.your_vac
```
- Battery Level
- Update status - Since the integration no longer polls, you can query the status of the vacuum by sending a custom command `update`

```yaml
service: vacuum.send_command
data:
  command: update
target:
  entity_id: vacuum.theovac
```

- Refresh Login Token - You can also refresh the login token if it has been awhile since you queried status and your login token has expired

```yaml
service: vacuum.send_command
data:
  command: refresh_token
target:
  entity_id: vacuum.theovac
```

## Misc
- Location is not supported but it is considered "supported" by HA so the button doesn't crash the component when using vacuum-card if you use it.

## Implementing vacuum-card
There's a lovely Lovelace vacuum-card [here](https://github.com/denysdovhan/vacuum-card) in which you can implement your vacuum like so:
![image](https://user-images.githubusercontent.com/18567128/161214101-2224e784-f770-42b3-8fed-fada75d753cc.png)

Here is my YAML configuration of the card

```yaml
type: custom:vacuum-card
entity: vacuum.theovac
image: default
show_toolbar: true
show_status: true
show_name: true
compact_view: false
stats:
    default:
      - attribute: filter
        unit: hours
        subtitle: Filter
      - attribute: side_brush
        unit: hours
        subtitle: Side brush
      - attribute: main_brush
        unit: hours
        subtitle: Main brush
shortcuts:
  - name: Clean living room
    service: script.vacuum_room_clean
    icon: mdi:sofa
    service_data:
      rooms:
        - Living Room
  - name: Update
    service: script.vacuum_update_state
    icon: mdi:update

```
and the contents of the scripts it invokes
```yaml
alias: Vacuum Room Clean
variables:
  rooms:
    - Living Room
sequence:
  - service: vacuum.send_command
    data:
      command: sweep_rooms
      params:
        rooms: ' {{ rooms }} '
    target:
      entity_id: vacuum.theovac
mode: single

```
```yaml
alias: Vacuum Update State
sequence:
  - service: vacuum.send_command
    data:
      command: update
    target:
      entity_id: vacuum.theovac
mode: single
```

### Adding map to vacuum card
There is support for at least showing the last sweep map. To add it add a camera entity like shown below:

```
camera:
- platform: local_file
  file_path: /config/www/simple_wyze_vac/vacuum_last_map.jpg
  name: "My Vaccuum Map"
```

With a camera entity, in your vacuum-card (if you're using it) you can add

```
map: camera.my_vacuum_map

```

which should then show the last sweep map 

![image](https://user-images.githubusercontent.com/18567128/161214208-b9de5906-ee86-4bce-97dc-f4a02a1fa15c.png)

**TIP** - Wrap your vacuum card in a 'conditional' card and use the vacuum state of 'docked' to test if it is docked and undocked. This way, you can still have the vacuum logo and not the map when the vacuum is not running

## TODO / Maybe in the Future
- In theory everything from wyze-sdk should be possible?

## Shoutouts
- [@shauntarves/wyze-sdk](https://github.com/shauntarves/wyze-sdk)
- [aarongodfrey](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_1/) - Helped figuring out what in the world I am doing
- [Samuel](https://blog.thestaticturtle.fr/creating-a-custom-component-for-homeassistant/) - More info on how custom components work
