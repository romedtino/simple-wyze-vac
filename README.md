# Simple Wyze Vacuum for Home Assistant

- [Simple Wyze Vacuum for Home Assistant](#simple-wyze-vacuum-for-home-assistant)
  * [General](#general)
  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
  * [Supported Features](#supported-features)
  * [Polling](#polling)
  * [Misc](#misc)
  * [TOTP](#totp)
  * [Implementing vacuum-card](#implementing-vacuum-card)
    + [Adding map to vacuum card](#adding-map-to-vacuum-card)
  * [Shoutouts](#shoutouts)

## General

Simple implementation of the Wyze Vacuum right into Home Assistant. I have only tested this against the official firmware version - **1.6.202** If you run into issues against a different firmware **please be extra descriptive of the problem when filing an issue.**

**NOTE** 

By default, this integration **DOES NOT** automatically update your vacuum entity. This is due to Wyze applying a rate limit on integrations. For more details you can read the [reddit thread here](https://www.reddit.com/r/wyzecam/comments/p6bgj2/wyze_rate_limiting_requests_wyzeapi_likely_will/). However, there is an option to enable polling with a configuration change. This leaves this integration with two options to address this issue:

- To update the state of the device, you can do a `vacuum.send_command` with command `update` which will update the state of the vacuum. See [vacuum-card example](#implementing-vacuum-card) below for an implementation.
- Enable [Polling](#polling)

## Prerequisites
- Home Assistant 😅
- [HACS](https://hacs.xyz/) Installed in Home Assistant
- Wyze Account (either with 2FA disabled or TOTP authentication setup when integrating Simple Wyze Vac. Note: This is NOT the same thing as the 6 digit code you get from your Authenticator app. Please see [TOTP](#totp) section)

## Installation
1. On Home Assistant go to HACS -> Integration
2. Click menu on the top right
3. Click on custom repositories
4. Add https://github.com/romedtino/simple-wyze-vac as an Integration
5. Install/Add simple-wyze-vac
6. Restart Home Assistant
7. Navigate to `Configuration`
8. Navigate to `Devices & Services`
9. Click `ADD INTEGRATION` on the bottom right
10. Select `Simple Wyze Vac`
11. Enter your `username` and `password`

If it all worked out, you should now have Wyze vacuum entity(ies)

## Supported Features
- TOTP (Note: This is NOT the same thing as the 6 digit code you get from your Authenticator app. Please see [TOTP](#totp) section)
- Start
- Stop / Pause
- Return to Base
- Filter lifespan information (Main filter, main brush and side brush)
- Camera entity to show last vacuum map
- Room names as toggleable switches (For area cleaning)
- Room names as vacuum attributes
- Optional [Polling](#polling)
- Sweep Rooms as a service using `simple_wyze_vac.sweep_rooms` or `vacuum.send_command` with command `sweep_auto`
  - Using built-in service and choosing the switch entities/rooms you want to do a sweep
    ![image](https://user-images.githubusercontent.com/18567128/166072534-58fb8999-c328-4220-9a73-99fe312e1192.png)
    or in YAML
    ```yaml
    service: simple_wyze_vac.sweep_rooms
    data:
      entity_id: vacuum.theovac
      rooms:
        - switch.swv_kitchen
        - switch.swv_entryway
    ```
  - Using `sweep_auto` - Automatically run area cleaning ![image](https://user-images.githubusercontent.com/18567128/165417724-b3ef20af-381f-4135-9f6c-53f55310c50c.png) based on the rooms (switch entities provided by Simple Wyze Vac) that are 'ON'. For example, in the attached screenshot, invoking a `sweep_auto` will do an area cleaning of the Living Room.
- ![image](https://user-images.githubusercontent.com/18567128/165418261-bed10bb4-472e-43d8-903f-fa1dff13bb06.png)

```yaml
service: vacuum.send_command
data:
  command: sweep_auto
target:
  entity_id: vacuum.theovac
```
- Manually designate area cleaning (Must use serivce call) Example: ![image](https://user-images.githubusercontent.com/18567128/127786476-ec3dbfcd-66f4-40e6-bfe5-fda0edad191d.png)
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

## Polling

To enable polling
1. Navigate to the Simple Wyze Vac `Devices & Services` page under `Configuration`
2. Select `Configure` ![image](https://user-images.githubusercontent.com/18567128/165417969-f10f96c0-7db3-4539-9b5b-726541bb5275.png)
3. Check `Enable polling` and provide the interval. The interval value is in `HH:MM:SS` format. For example `00:01:00` would poll every 1 minute.


## Misc
- Location is currently not supported but it is considered "supported" by HA so the button doesn't crash the component when using vacuum-card defaults if you use it.

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
There is support for at showing the last sweep map. With the exposed camera entity, in your vacuum-card (if you're using it) you can add `camera.{vacuum_name}_camera` e.g.

```
map: camera.wyzevac_camera

```

which should then show the last sweep map 

![image](https://user-images.githubusercontent.com/18567128/161214208-b9de5906-ee86-4bce-97dc-f4a02a1fa15c.png)

**TIP** - Wrap your vacuum card in a 'conditional' card and use the vacuum state of 'docked' to test if it is docked and undocked. This way, you can still have the vacuum logo and not the map when the vacuum is not running. Another option is to create a helper `input_boolean` and use that instead to toggle between showing the map and showing the vacuum like so:

![vac_sample3](https://user-images.githubusercontent.com/18567128/161217759-762a70f2-3a1e-4f9f-ad86-5b8a80209173.gif)

```yaml
type: conditional
conditions:
  - entity: input_boolean.map_toggle
    state: 'off'
card:
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
        subtitle: Side Brush
      - attribute: main_brush
        unit: hours
        subtitle: Main Brush
  shortcuts:
    - name: Toggle Map
      service: input_boolean.toggle
      service_data:
        entity_id: input_boolean.map_toggle
      icon: mdi:map
  view_layout:
    position: sidebar
view_layout:
  position: sidebar

```

## TOTP

`wyze_sdk` implemented support for using TOTP (Time-Based One-Time Password). Specifically, [mintotp](https://github.com/susam/mintotp) which works great! 

### How to Setup TOTP

1. If you already have 2FA setup on your Wyze account you will have to reapply it. If you already have Simple Wyze Vac integrated, you will have to remove it and readd it.
  1. To remove it, navigate to the Wyze app and go - `Accounts -> Security -> Two-Factor Authentication` and remove verification
2. Back in `Accounts -> Security -> Two-Factor Authentication`, select Verification by Authenticator app.
3. Read the instructions from Wyze BUT make sure to copy and KEEP the value in step 3. This is your Base32 SECRET used to generate TOTP.
4. Go ahead and setup your TOTP on the Authenticator of your choosing.
5. Re-add `Simple Wyze Vac` under `Add Integration` of Home Assistant.
6. Enter your `username`, `password` and for TOTP, copy the Base32 SECRET you got from the Wyze app
7. `Submit` and you should now be authenticated with 2FA enabled!


## Shoutouts
- [@shauntarves/wyze-sdk](https://github.com/shauntarves/wyze-sdk) - This would not be possible without this awesomesauce
- [aarongodfrey](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_1/) - Helped figuring out what in the world I am doing
- [Samuel](https://blog.thestaticturtle.fr/creating-a-custom-component-for-homeassistant/) - More info on how custom components work
- [markdown-toc](http://ecotrust-canada.github.io/markdown-toc/) - For markdown TOC generator
