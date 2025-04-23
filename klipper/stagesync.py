# StageSync allows you to define a main heater and synchronize additional
# heaters to it by adding a temperature multiplier to each one.
#
# Support for optimizing management of the Aten V-ONE hotend and similar.
# more information at www.aten3d.com
#
# Copyright (C) 2024 Aten <info@aten3d.com>
# Aten is a registered trademark of Digimaker3D srl
#
# This file may be distributed under the terms of the GNU GPLv3 license.
#
# klippy/extras/stagesync.py

import logging

class StageSync:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.heater_name = config.get_name().split()[1]
        self.heater = None
        self.stages = []  # Used to maintain the association between stages and temp_ratio
        self.last_target_temp = None  # Stores the last target temperature for comparison
        self.gcode = self.printer.lookup_object('gcode')  # Lookup the gcode object
        self.printer.register_event_handler("klippy:connect", self.handle_connect)

        stage_names = config.get('stages').split(',')
        temp_ratios = config.get('temp_ratio').split(',')

        # Save the names and temp_ratios for future mapping
        for stage_name, temp_ratio in zip(stage_names, temp_ratios):
            try:
                temp_ratio_value = float(temp_ratio.strip())
                
                # Validate temp_ratio
                if temp_ratio_value < 0 or temp_ratio_value > 2.0:
                    self.ratio_fault(stage_name.strip(), temp_ratio_value)

                # Attempt to look up the heater object by name using general object lookup
                stage = self.printer.lookup_object('heater', stage_name.strip())
                if stage is None:
                    self.stages_fault(stage_name.strip())
                
                self.stages.append((stage, temp_ratio_value))
                logging.info(f"StageSync stages: {stage_name.strip()} with temp_ratio: {temp_ratio.strip()}")
            except Exception as e:
                self.mapping_fault(stage_name.strip(), e)

        # Register the handler for synchronization when the system is ready
        self.printer.register_event_handler("klippy:ready", self.handle_ready)

    def handle_connect(self):
        try:
            pheaters = self.printer.lookup_object('heaters')
            self.heater = pheaters.lookup_heater(self.heater_name)
            reactor = self.printer.get_reactor()
            self.check_timer = reactor.register_timer(self.check_event, reactor.NOW)
        except Exception as e:
            self.heater_fault(self.heater_name, e)

    def handle_ready(self):
        try:
            # Synchronize temperatures on the first run
            self.sync_temperatures(self.last_target_temp)
        except Exception:
            pass  # Removed logging of temperature synchronization error

    def check_event(self, eventtime):
        try:
            temp, target = self.heater.get_temp(eventtime)
            # Only skip if target is None. Allow target == 0 to pass through and sync stages to 0.
            if target is None:
                return eventtime + 1.0  # Retry after 1 second

            if target != self.last_target_temp:
                self.last_target_temp = target
                self.sync_temperatures(target)

            # Schedule the next check in 1 second
            return eventtime + 1.0

        except Exception:
            return eventtime + 1.0  # Retry after 1 second

    def sync_temperatures(self, target):
        if not self.heater or target is None:
            return

        # Apply the temperature to the stages using a G-code command
        for stage, temp_ratio in self.stages:
            adjusted_temp = target * temp_ratio
            stage_name = stage.get_name() if hasattr(stage, 'get_name') else stage
            gcode_command = f'SET_HEATER_TEMPERATURE HEATER="{stage_name}" TARGET="{adjusted_temp}"'
            try:
                self.gcode.run_script(gcode_command)  # Use gcode object to send the command
            except Exception as e:
                logging.error(f"Temperature synchronization via G-code failed! {stage_name}: {e}")

    def ratio_fault(self, stage_name, temp_ratio_value):
        msg = f"StageSync: temp_ratio for stage '{stage_name}' is out of bounds: {temp_ratio_value}"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER

    def stages_fault(self, stage_name):
        msg = f"StageSync: stage '{stage_name}' not found"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER

    def heater_fault(self, heater_name, error):
        msg = f"StageSync: Error initializing heater '{heater_name}': {error}"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER

    def mapping_fault(self, stage_name, error):
        msg = f"StageSync: Error mapping stage '{stage_name}': {error}"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER


def load_config_prefix(config):
    return StageSync(config)
