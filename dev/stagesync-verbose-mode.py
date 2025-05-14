# StageSyncVerboseMode: Klipper plugin for debug-friendly synchronization 
# of secondary heaters with a primary one using temperature multipliers.
#
# #####.#####.#####. DISCLAIMER .#####.#####.#####
# #####.##### ONLY FOR DEVELOPMENT USE! #####.#####
#
# Verbose mode: extensive logging for troubleshooting and insight.
# Rename this file to stagesync.py (or include alongside) to enable.
#
# Copyright (C) 2024 Aten <info@aten3d.com>
# Aten is a registered trademark of Digimaker3D srl
# Distributed under the GNU GPLv3 license.
#
# klippy/extras/stagesync.py

import logging

class StageSyncVerbose:
    """
    Verbose StageSync plugin: synchronizes secondary heaters to a primary heater with detailed logs.
    """
    def __init__(self, config):
        self.printer = config.get_printer()
        self.heater_name = config.get_name().split()[1]
        self.heater = None
        self.stages = []  # list of (heater_obj, ratio)
        self.last_target_temp = None

        # G-code interface
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('STAGESYNC', self.cmd_STAGESYNC,
                                    desc="Force immediate StageSync update (verbose)")

        logging.info(f"[StageSyncVerbose] Initializing for primary heater '{self.heater_name}'")
        self.printer.register_event_handler('klippy:connect', self.handle_connect)
        self.printer.register_event_handler('klippy:ready',   self.handle_ready)

        # Parse configuration
        stage_names = config.get('stages').split(',')
        temp_ratios  = config.get('temp_ratio').split(',')
        for name_str, ratio_str in zip(stage_names, temp_ratios):
            name = name_str.strip()
            try:
                ratio = float(ratio_str)
                if not 0.0 <= ratio <= 2.0:
                    self._fault(f"Invalid ratio {ratio} for stage '{name}'")
                heater_obj = self.printer.lookup_object('heater', name)
                if heater_obj is None:
                    self._fault(f"Stage heater '{name}' not found")
                self.stages.append((heater_obj, ratio))
                logging.info(f"[StageSyncVerbose] Mapped stage '{name}' -> ratio {ratio}")
            except Exception as e:
                self._fault(f"Error mapping stage '{name}': {e}")

    def handle_connect(self):
        try:
            heaters = self.printer.lookup_object('heaters')
            self.heater = heaters.lookup_heater(self.heater_name)
            reactor = self.printer.get_reactor()
            self.check_timer = reactor.register_timer(self.check_event, reactor.NOW)
            logging.info(f"[StageSyncVerbose] Connected to '{self.heater_name}', timer started.")
        except Exception as e:
            self._fault(f"Error initializing primary heater '{self.heater_name}': {e}")

    def handle_ready(self):
        logging.info("[StageSyncVerbose] System ready, performing initial sync.")
        try:
            self._do_sync(self.last_target_temp)
        except Exception as e:
            logging.error(f"[StageSyncVerbose] Initial sync failed: {e}")

    def check_event(self, eventtime):
        try:
            current_temp, target = self.heater.get_temp(eventtime)
            if target is None:
                logging.warning(f"[StageSyncVerbose] No target for '{self.heater_name}', retry.")
            elif target != self.last_target_temp:
                logging.info(f"[StageSyncVerbose] Target changed: {self.last_target_temp} -> {target}")
                self.last_target_temp = target
                self._do_sync(target)
            else:
                logging.debug(f"[StageSyncVerbose] Target unchanged ({target}), skip sync.")
            return eventtime + 1.0
        except Exception as e:
            logging.error(f"[StageSyncVerbose] check_event error: {e}")
            return eventtime + 1.0

    def _do_sync(self, target):
        if self.heater is None or target is None:
            logging.debug("[StageSyncVerbose] No target or heater; aborting sync.")
            return

        logging.info(f"[StageSyncVerbose] Syncing stages to target {target}")
        lines = []
        for heater_obj, ratio in self.stages:
            name = getattr(heater_obj, 'get_name', lambda: str(heater_obj))()
            adjusted = target * ratio
            cmd = f'SET_HEATER_TEMPERATURE HEATER="{name}" TARGET="{adjusted:.2f}"'
            lines.append(cmd)
            logging.debug(f"[StageSyncVerbose] Queued command: {cmd}")

        script = "\n".join(lines)
        try:
            self.gcode.run_script_from_command(script)
            logging.info("[StageSyncVerbose] All stage commands dispatched.")
        except Exception as e:
            self._fault(f"Error dispatching commands: {e}")

    def cmd_STAGESYNC(self, gcmd):
        """
        STAGESYNC: Manual trigger for verbose synchronization.
        """
        gcmd.respond_info("[StageSyncVerbose] Manual sync triggered")
        try:
            target = self.last_target_temp
            if target is None and self.heater:
                _, target = self.heater.get_temp(self.printer.get_reactor().monotonic())
            self._do_sync(target)
            gcmd.respond_info("[StageSyncVerbose] Sync complete")
        except Exception as e:
            gcmd.respond_info(f"[StageSyncVerbose] Sync error: {e}")

    def _fault(self, message):
        logging.error(f"[StageSyncVerbose] {message}")
        self.printer.invoke_shutdown(message)
        return self.printer.get_reactor().NEVER


def load_config_prefix(config):
    logging.info(f"[StageSyncVerbose] load_config_prefix for {config.get_name()}")
    return StageSyncVerbose(config)
