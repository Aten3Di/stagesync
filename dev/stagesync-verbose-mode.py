# StageSync is a Klipper plugin to synchronize secondary heaters 
# with a primary one using temperature multipliers.
#
# #####.#####.#####. DISCLAIMER .#####.#####.#####
# #####.##### ONLY FOR DEVELOPMENT USE! #####.#####
#
# Rename this file to stagesync.py to enable it in Klipper.
# This is the verbose-mode version with extensive logging for debugging.
#
# Support for optimizing management of the Aten V-ONE hotend and similar.
# More information at www.aten3d.com
#
# Copyright (C) 2024 Aten <info@aten3d.com>
# Aten is a registered trademark of Digimaker3D srl
#
# Distributed under the GNU GPLv3 license.
#
# klippy/extras/stagesync.py

import logging

class StageSync:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.heater_name = config.get_name().split()[1]
        self.heater = None
        self.stages = []  # associations between stage heaters and temperature ratios
        self.last_target_temp = None
        self.gcode = self.printer.lookup_object('gcode')

        logging.info(f"[StageSync] Loading configuration for heater: {self.heater_name}")
        self.printer.register_event_handler('klippy:connect', self.handle_connect)
        self.printer.register_event_handler('klippy:ready', self.handle_ready)

        stage_names = config.get('stages').split(',')
        temp_ratios = config.get('temp_ratio').split(',')

        for stage_name, temp_ratio in zip(stage_names, temp_ratios):
            name = stage_name.strip()
            try:
                ratio = float(temp_ratio.strip())
                if ratio < 0 or ratio > 2.0:
                    self.ratio_fault(name, ratio)
                heater_obj = self.printer.lookup_object('heater', name)
                if heater_obj is None:
                    self.stages_fault(name)
                self.stages.append((heater_obj, ratio))
                logging.info(f"[StageSync] Mapped stage '{name}' with ratio {ratio}")
            except Exception as e:
                self.mapping_fault(name, e)

    def handle_connect(self):
        try:
            heaters = self.printer.lookup_object('heaters')
            self.heater = heaters.lookup_heater(self.heater_name)
            reactor = self.printer.get_reactor()
            self.check_timer = reactor.register_timer(self.check_event, reactor.NOW)
            logging.info(f"[StageSync] Connected to primary heater '{self.heater_name}' and timer started.")
        except Exception as e:
            self.heater_fault(self.heater_name, e)

    def handle_ready(self):
        logging.info(f"[StageSync] System ready; initial synchronization.")
        try:
            self.sync_temperatures(self.last_target_temp)
        except Exception as e:
            logging.error(f"[StageSync] Error during initial sync: {e}")

    def check_event(self, eventtime):
        try:
            current_temp, target = self.heater.get_temp(eventtime)
            if target is None:
                logging.warning(f"[StageSync] No target temperature for '{self.heater_name}'; retrying.")
                return eventtime + 1.0

            if target != self.last_target_temp:
                logging.info(f"[StageSync] Detected target change: {self.last_target_temp} -> {target}")
                self.last_target_temp = target
                self.sync_temperatures(target)
            else:
                logging.debug(f"[StageSync] Target unchanged ({target}); skipping sync.")

            next_time = eventtime + 1.0
            logging.debug(f"[StageSync] Next check scheduled at {next_time}")
            return next_time

        except Exception as e:
            logging.error(f"[StageSync] Error in check_event for '{self.heater_name}': {e}")
            return eventtime + 1.0

    def sync_temperatures(self, target):
        logging.info(f"[StageSync] Synchronizing stages to target {target}")

        if self.heater is None:
            logging.error(f"[StageSync] Primary heater '{self.heater_name}' not initialized.")
            return
        if target is None:
            logging.error(f"[StageSync] Invalid target; cannot synchronize.")
            return

        for stage, ratio in self.stages:
            name = stage.get_name() if hasattr(stage, 'get_name') else str(stage)
            adjusted = target * ratio
            cmd = f'SET_HEATER_TEMPERATURE HEATER="{name}" TARGET="{adjusted}"'
            try:
                self.gcode.run_script(cmd)
                logging.info(f"[StageSync] Sent: {cmd}")
            except Exception as e:
                self.gcode_fault(name, e)

    def ratio_fault(self, stage_name, ratio):
        msg = f"[StageSync] Ratio {ratio} out of bounds for stage '{stage_name}'"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER

    def stages_fault(self, stage_name):
        msg = f"[StageSync] Stage '{stage_name}' not found"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER

    def heater_fault(self, heater_name, error):
        msg = f"[StageSync] Error initializing heater '{heater_name}': {error}"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER

    def mapping_fault(self, stage_name, error):
        msg = f"[StageSync] Error mapping stage '{stage_name}': {error}"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER

    def gcode_fault(self, stage_name, error):
        msg = f"[StageSync] Error sending G-code to '{stage_name}': {error}"
        logging.error(msg)
        self.printer.invoke_shutdown(msg)
        return self.printer.get_reactor().NEVER


def load_config_prefix(config):
    logging.info(f"[StageSync] load_config_prefix invoked for {config.get_name()}")
    return StageSync(config)
