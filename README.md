# Simple Wyze Vacuum for Home Assistant

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
5. Edit your configuration.yaml and add
```yaml
simple_wyze_vac:
  username: your_wyze_email@email.com
  password: your_wyze_password
```
6. Restart Home Assistant

If it all worked out, you should now have Wyze vacuum entity(ies)

## Supported Features
- Start
- Stop / Pause
- Return to Base
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

## Misc
- Location is not supported but it is considered "supported" by HA so the button doesn't crash the component when using vacuum-card if you use it.


## TODO / Maybe in the Future
- In theory everything from wyze-sdk should be possible?
- Currently using a forked version of wyze-sdk which fixes the login issue and showing battery levels. Need to revert back to using pypi release by shauntarves once he's updated his repo.

## Shoutouts
- [@shauntarves/wyze-sdk](https://github.com/shauntarves/wyze-sdk) - Underlying base of this process (Currently forked here: https://github.com/romedtino/wyze-sdk)
- [aarongodfrey](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_1/) - Helped figuring out what in the world I am doing
- [Samuel](https://blog.thestaticturtle.fr/creating-a-custom-component-for-homeassistant/) - More info on how custom components work
