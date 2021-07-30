# Simple Wyze Vacuum for Home Assistant

Simple implementation of the Wyze Vacuum right into Home Assistant. 

## Prerequisites
- Home Assistant 😅
- [HACS](https://hacs.xyz/) Installed in Home Assistant
- Wyze Account without 2FA

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
7. NOTE: As of the time of this writing (7/3/2021) Wyze had updated their protocol for logging in. This has caused an issue in the `wyze_sdk 1.2.1` version that this component is dependent on. To fix this, I followed the temporary work around [here](https://github.com/shauntarves/wyze-sdk/issues/35#issuecomment-885325398). The location of where Home Assistant installs python packages will depend on your installation. For example, I am running off of a Docker container, so I have to remote into my container and modify the file in `/usr/lib/share/python3.9/site-packages/...`. Tip: If you visit the Home Assistant logs, it usually shows you where wyze_sdk error'ed out and it outputs the full path.
    1. Once you restart, Home Assistant should have pulled a copy of wyze_sdk in some site-packages directory. Find the wyze_sdk/ installation location. 
    2. Modify wyze_sdk/service/auth_service.py under `_get_headers` there's this line
    ```python
     request_specific_headers.update({
            'x-api-key': self.api_key,
        })
    ```
    modify it to
    ```python
     request_specific_headers.update({
            "user-agent": "wyze_android_2.11.40",
            'x-api-key': self.api_key,
        })
    ```
    3. Restart Home Assistant again

If it all worked out, you should now have Wyze vacuum entity(ies)

## Supported Features
- Start
- Stop / Pause
- Return to Base

## Misc
- Location is not supported but it is considered "supported" by HA so the button doesn't crash the component when using vacuum-card if you use it.

## TODO / Maybe in the Future
- Room Clean
- In theory everything from wyze-sdk should be possible?


## Shoutouts
- [@shauntarves/wyze-sdk](https://github.com/shauntarves/wyze-sdk) - Underlying base of this process
- [aarongodfrey](https://aarongodfrey.dev/home%20automation/building_a_home_assistant_custom_component_part_1/) - Helped figuring out what in the world I am doing
- [Samuel](https://blog.thestaticturtle.fr/creating-a-custom-component-for-homeassistant/) - More info on how custom components work
