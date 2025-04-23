# Installation:
Execute the following commands:

- Clone and install the software
```
cd  ~
git clone https://github.com/Aten3Di/stagesync.git
```
- run the installation script.
```
./stagesync/klipper/install_stagesync.sh
```
- Add the following section to moonraker.conf and you can update StageSync automatically.
```
[update_manager stagesync]
type: git_repo
primary_branch: new
channel: dev
path: ~/stagesync
origin: https://github.com/Aten3Di/stagesync.git
install_script: ./klipper/install_stagesync.sh
is_system_service: False
managed_services: klipper
info_tags:
  desc=stagesync
```

# Configuration:

### [stagesync]
Support for additional heaters synced to the temperatures of a primary heater (any number of sections can be defined with a "stagesync" prefix).
```
[stagesync main_heater_name]
#stages: stage1, stage2
#   Define the name of the additional heater to synchronize with the main heater.
#   If there are more than one heaters, they must be divided with a comma.
#   This parameter must be provided.
#temp_ratio: 1.0, 0.9
#   Defines the target temperature multiplier value of each heater synchronized
#   with the master heater. Specifies a percentage of the main heater target
#   temperature to apply to the supplemental heaters. Each value corresponds to
#   the respective heater divided by a comma. The value range is from 0 (0%) to
#   2.00 (200%). This value is optional and if not defined a multiplier of 1.0
#   will be applied.
```
