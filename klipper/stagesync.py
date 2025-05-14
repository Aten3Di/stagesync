# StageSync is a Klipper plugin to synchronize secondary heaters 
# with a primary one using temperature multipliers.
#
# Support for optimizing management of the Aten V-ONE hotend and similar devices.
# more information at www.aten3d.com
#
# Copyright (C) 2024 Aten <info@aten3d.com>
# Aten is a registered trademark of Digimaker3D srl
#
# This file may be distributed under the terms of the GNU GPLv3 license.
#
# klippy/extras/stagesync.py

import logging

class stagesync:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.heater_name = config.get_name().split()[1]
        self.heater = None
        self.stages = []  # list of (heater_object, ratio)
        self.last_target_temp = None  # last applied temperature

        # Obtain G-code handler and register manual trigger command
        self.gcode = self.printer.lookup_object('gcode')
        # Register custom G-code 'STAGESYNC' for manual sync
        self.gcode.register_command('STAGESYNC', self.cmd_STAGESYNC, desc="Force immediate StageSync update")

        # Event handlers for automatic sync
        self.printer.register_event_handler("klippy:connect", self.handle_connect)
        self.printer.register_event_handler("klippy:ready",   self.handle_ready)

        # Parse configuration for stages and ratios
        stage_names = config.get('stages').split(',')
        temp_ratios = config.get('temp_ratio').split(',')
        for stage_name, temp_ratio in zip(stage_names, temp_ratios):
            name = stage_name.strip()
            try:
                ratio = float(temp_ratio)
                if not (0.0 <= ratio <= 2.0):
                    self._ratio_fault(name, ratio)
                heater_obj = self.printer.lookup_object('heater', name)
                if heater_obj is None:
                    self._stages_fault(name)
                self.stages.append((heater_obj, ratio))
                logging.info(f"stagesync: mapped '{name}' with ratio {ratio}")
            except Exception as e:
                self._mapping_fault(name, e)

    def handle_connect(self):
        try:
            heaters = self.printer.lookup_object('heaters')
            self.heater = heaters.lookup_heater(self.heater_name)
            reactor = self.printer.get_reactor()
            # schedule periodic check every second
            self.check_timer = reactor.register_timer(self.check_event, reactor.NOW)
        except Exception as e:
            self._heater_fault(self.heater_name, e)

    def handle_ready(self):
        # on ready, force initial sync
        self._do_sync(self.last_target_temp)

    def check_event(self, eventtime):
        # periodic polling for target changes
        try:
            _, target = self.heater.get_temp(eventtime)
            if target is not None and target != self.last_target_temp:
                self.last_target_temp = target
                self._do_sync(target)
            return eventtime + 1.0
        except Exception:
            return eventtime + 1.0

    def _do_sync(self, target):
        if not self.heater or target is None:
            return
        # Build multi-line script for all stage updates
        lines = []
        for heater_obj, ratio in self.stages:
            adjusted = target * ratio
            name = heater_obj.get_name() if hasattr(heater_obj, 'get_name') else heater_obj
            lines.append(f'SET_HEATER_TEMPERATURE HEATER="{name}" TARGET="{adjusted:.2f}"')
        script = "\n".join(lines)
        try:
            # Use run_script_from_command to avoid deadlock on the G-code mutex
            self.gcode.run_script_from_command(script)
        except Exception as e:
            logging.error(f"stagesync: failed to sync secondary heaters: {e}")

    def cmd_STAGESYNC(self, gcmd):
        """
        STAGESYNC
        Force an immediate update of all secondary heaters.
        """
        gcmd.respond_info("stagesync: manual trigger…")
        try:
            # use last known or poll current target
            target = self.last_target_temp
            if target is None and self.heater:
                _, target = self.heater.get_temp(self.printer.get_reactor().monotonic())
            self._do_sync(target)
            gcmd.respond_info("stagesync: update completed")
        except Exception as e:
            gcmd.respond_info(f"stagesync: error: {e}")

    # Fault handlers
    def _ratio_fault(self, name, ratio):
        msg = f"stagesync: invalid ratio for '{name}': {ratio}"  
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER

    def _stages_fault(self, name):
        msg = f"stagesync: unknown stage '{name}'"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER

    def _heater_fault(self, name, error):
        msg = f"stagesync: heater init error '{name}': {error}"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER

    def _mapping_fault(self, name, error):
        msg = f"stagesync: mapping error '{name}': {error}"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER


def load_config_prefix(config):
    """Entry point for Klipper to load this plugin"""
    return stagesync(config)
