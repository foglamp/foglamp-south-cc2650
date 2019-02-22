# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Module for Sensortag CC2650 plugin """

import copy
import time
import uuid

from foglamp.common import logger
from foglamp.plugins.common import utils
from foglamp.plugins.south.cc2650.sensortag_cc2650 import *
from foglamp.services.south import exceptions

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'TI SensorTag South Plugin',
        'type': 'string',
        'default': 'cc2650',
        'readonly': 'true'
    },
    'bluetoothAddress': {
        'description': 'Bluetooth address',
        'type': 'string',
        'default': 'B0:91:22:EA:79:04',
        'order': '1',
        'displayName': 'Bluetooth Address'
    },
    'assetNamePrefix': {
        'description': 'Asset name prefix, %M will be replaced by bluetooth address',
        'type': 'string',
        'default': 'CC2650/%M/',
        'order': '2',
        'displayName': 'Asset Name Prefix'
    },
    'shutdownThreshold': {
        'description': 'Time in seconds allowed for shutdown to complete the pending tasks',
        'type': 'integer',
        'default': '10',
        'order': '4',
        'displayName': 'Shutdown Threshold'
    },
    'connectionTimeout': {
        'description': 'BLE connection timeout value in seconds',
        'type': 'integer',
        'default': '3',
        'minimum': '2',
        'maximum': '5',
        'order': '5',
        'displayName': 'Connection Timeout'
    },
    'temperatureSensor': {
        'description': 'Enable temperature sensor',
        'type': 'boolean',
        'default': 'true',
        'order': '6',
        'displayName': 'Temperature Sensor'
    },
    'temperatureSensorName': {
        'description': 'Name of temperature sensor',
        'type': 'string',
        'default': 'temperature',
        'order': '7',
        'displayName': 'Temperature Sensor Name'
    },
    'luminanceSensor': {
        'description': 'Enable luminance sensor',
        'type': 'boolean',
        'default': 'false',
        'order': '8',
        'displayName': 'Luminance Sensor'
    },
    'luminanceSensorName': {
        'description': 'Name of luminance sensor',
        'type': 'string',
        'default': 'luminance',
        'order': '9',
        'displayName': 'Luminance Sensor Name'
    },
    'humiditySensor': {
        'description': 'Enable humidity sensor',
        'type': 'boolean',
        'default': 'false',
        'order': '10',
        'displayName': 'Humidity Sensor'
    },
    'humiditySensorName': {
        'description': 'Name of humidity sensor',
        'type': 'string',
        'default': 'humidity',
        'order': '11',
        'displayName': 'Humidity Sensor Name'
    },
    'pressureSensor': {
        'description': 'Enable pressure sensor',
        'type': 'boolean',
        'default': 'false',
        'order': '12',
        'displayName': 'Pressure Sensor'
    },
    'pressureSensorName': {
        'description': 'Name of pressure sensor',
        'type': 'string',
        'default': 'pressure',
        'order': '13',
        'displayName': 'Pressure Sensor Name'
    },
    'movementSensor': {
        'description': 'Enable gyroscope, accelerometer and magnetometer sensors',
        'type': 'boolean',
        'default': 'false',
        'order': '14',
        'displayName': 'Movement Sensor'
    },
    'gyroscopeSensorName': {
        'description': 'Name of gyroscope sensor',
        'type': 'string',
        'default': 'gyroscope',
        'order': '15',
        'displayName': 'Gyroscope Sensor Name'
    },
    'accelerometerSensorName': {
        'description': 'Name of accelerometer sensor',
        'type': 'string',
        'default': 'accelerometer',
        'order': '16',
        'displayName': 'Accelerometer Sensor Name'
    },
    'magnetometerSensorName': {
        'description': 'Name of magnetometer sensor',
        'type': 'string',
        'default': 'magnetometer',
        'order': '17',
        'displayName': 'Magnetometer Sensor Name'
    },
    'batteryData': {
        'description': 'Get battery data',
        'type': 'boolean',
        'default': 'false',
        'order': '18',
        'displayName': 'Battery Data'
    },
    'batterySensorName': {
        'description': 'Name of battery sensor',
        'type': 'string',
        'default': 'battery',
        'order': '19',
        'displayName': 'Battery Sensor Name'
    }
}
_restart_config = None
_handle = None
_LOGGER = logger.setup(__name__, level=logger.logging.INFO)


def plugin_info():
    """ Returns information about the plugin.

    Args:
    Returns:
        dict: plugin information
    Raises:
    """

    return {
        'name': 'TI SensorTag CC2650 plugin',
        'version': '1.5.0',
        'mode': 'poll',
        'type': 'south',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """ Initialise the plugin.

    Args:
        config: JSON configuration document for the plugin configuration category
    Returns:
        handle: JSON object to be used in future calls to the plugin
    Raises:
    """
    global _restart_config, _handle

    sensortag_characteristics = copy.deepcopy(characteristics)
    data = copy.deepcopy(config)
    _restart_config = copy.deepcopy(config)

    bluetooth_adr = config['bluetoothAddress']['value']
    timeout = int(config['connectionTimeout']['value'])
    tag = SensorTagCC2650(bluetooth_adr, timeout)
    if tag.is_connected is True:
        # The GATT table can change for different firmware revisions, so it is important to do a proper characteristic
        # discovery rather than hard-coding the attribute handles.
        for char in sensortag_characteristics.keys():
            for _type in ['data', 'configuration', 'period']:
                handle = tag.get_char_handle(sensortag_characteristics[char][_type]['uuid'])
                sensortag_characteristics[char][_type]['handle'] = handle

        # Get Battery handle
        handle = tag.get_char_handle(battery['data']['uuid'])
        battery['data']['handle'] = handle
        sensortag_characteristics['battery'] = battery

        data['characteristics'] = sensortag_characteristics
        _LOGGER.info('SensorTagCC2650 {} Polling initialized'.format(bluetooth_adr))

        # Enable sensor
        if data['temperatureSensor']['value'] == 'true':
            tag.char_write_cmd(data['characteristics']['temperature']['configuration']['handle'], char_enable)
        if data['luminanceSensor']['value'] == 'true':
            tag.char_write_cmd(data['characteristics']['luminance']['configuration']['handle'], char_enable)
        if data['humiditySensor']['value'] == 'true':
            tag.char_write_cmd(data['characteristics']['humidity']['configuration']['handle'], char_enable)
        if data['pressureSensor']['value'] == 'true':
            tag.char_write_cmd(data['characteristics']['pressure']['configuration']['handle'], char_enable)
        if data['movementSensor']['value'] == 'true':
            tag.char_write_cmd(data['characteristics']['movement']['configuration']['handle'], movement_enable)

    _handle = copy.deepcopy(data)
    _handle['tag'] = tag
    data['tag'] = tag
    return data


def plugin_poll(handle):
    """ Extracts data from the sensor and returns it in a JSON document as a Python dict.

    Available for poll mode only.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        returns a sensor reading in a JSON document, as a Python dict, if it is available
        None - If no reading is available
    Raises:
        DataRetrievalError
    """
    global _handle, _restart_config

    bluetooth_adr = _handle['bluetoothAddress']['value']
    tag = _handle['tag']
    asset_prefix = '{}'.format(_handle['assetNamePrefix']['value']).replace('%M', bluetooth_adr)

    try:
        if not tag.is_connected:
            raise RuntimeError("SensorTagCC2650 {} not connected".format(bluetooth_adr))

        time_stamp = utils.local_timestamp()
        data = list()

        # In this method, cannot use "handle" as it might have changed due to restart. Hence use "_handle".

        if _handle['temperatureSensor']['value'] == 'true':
            count = 0
            while count < SensorTagCC2650.reading_iterations:
                object_temp_celsius, ambient_temp_celsius = tag.hex_temp_to_celsius(
                    tag.char_read_hnd(_handle['characteristics']['temperature']['data']['handle'], "temperature"))
                time.sleep(0.5)  # wait for a while
                count = count + 1
            data.append({
                'asset': '{}{}'.format(asset_prefix, _handle['temperatureSensorName']['value']),
                'timestamp': time_stamp,
                'key': str(uuid.uuid4()),
                'readings': {"object": object_temp_celsius, 'ambient': ambient_temp_celsius}
            })

        if _handle['luminanceSensor']['value'] == 'true':
            lux_luminance = tag.hex_lux_to_lux(
                tag.char_read_hnd(_handle['characteristics']['luminance']['data']['handle'], "luminance"))
            data.append({
                'asset': '{}{}'.format(asset_prefix, _handle['luminanceSensorName']['value']),
                'timestamp': time_stamp,
                'key': str(uuid.uuid4()),
                'readings': {"lux": lux_luminance}
            })

        if _handle['humiditySensor']['value'] == 'true':
            rel_humidity, rel_temperature = tag.hex_humidity_to_rel_humidity(
                tag.char_read_hnd(_handle['characteristics']['humidity']['data']['handle'], "humidity"))
            data.append({
                'asset': '{}{}'.format(asset_prefix, _handle['humiditySensorName']['value']),
                'timestamp': time_stamp,
                'key': str(uuid.uuid4()),
                'readings': {"humidity": rel_humidity, "temperature": rel_temperature}
            })

        if _handle['pressureSensor']['value'] == 'true':
            bar_pressure = tag.hex_pressure_to_pressure(
                tag.char_read_hnd(_handle['characteristics']['pressure']['data']['handle'], "pressure"))
            data.append({
                'asset': '{}{}'.format(asset_prefix, _handle['pressureSensorName']['value']),
                'timestamp': time_stamp,
                'key': str(uuid.uuid4()),
                'readings': {"pressure": bar_pressure}
            })

        if _handle['movementSensor']['value'] == 'true':
            gyro_x, gyro_y, gyro_z, acc_x, acc_y, acc_z, mag_x, mag_y, mag_z, acc_range = tag.hex_movement_to_movement(
                tag.char_read_hnd(_handle['characteristics']['movement']['data']['handle'], "movement"))
            data.append({
                'asset': '{}{}'.format(asset_prefix, _handle['gyroscopeSensorName']['value']),
                'timestamp': time_stamp,
                'key': str(uuid.uuid4()),
                'readings': {"x": gyro_x, "y": gyro_y, "z": gyro_z}
            })
            data.append({
                'asset': '{}{}'.format(asset_prefix, _handle['accelerometerSensorName']['value']),
                'timestamp': time_stamp,
                'key': str(uuid.uuid4()),
                'readings': {"x": acc_x, "y": acc_y, "z": acc_z}
            })
            data.append({
                'asset': '{}{}'.format(asset_prefix, _handle['magnetometerSensorName']['value']),
                'timestamp': time_stamp,
                'key': str(uuid.uuid4()),
                'readings': {"x": mag_x, "y": mag_y, "z": mag_z}
            })

        if _handle['batteryData']['value'] == 'true':
            battery_level = tag.get_battery_level(
                tag.char_read_hnd(_handle['characteristics']['battery']['data']['handle'], "battery"))
            data.append({
                'asset': '{}{}'.format(asset_prefix, _handle['batterySensorName']['value']),
                'timestamp': time_stamp,
                'key': str(uuid.uuid4()),
                'readings': {"percentage": battery_level}
            })
    except RuntimeError as ex:
        _plugin_restart(bluetooth_adr)
        raise exceptions.QuietError(str(ex))
    except (Exception, pexpect.exceptions.TIMEOUT) as ex:
        _plugin_restart(bluetooth_adr)
        raise exceptions.DataRetrievalError(str(ex))

    return data


def plugin_reconfigure(handle, new_config):
    """  Reconfigures the plugin

    it should be called when the configuration of the plugin is changed during the operation of the South service;
    The new configuration category should be passed.

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    Raises:
    """
    # In this method, cannot use "handle" as it might have changed due to restart. Hence use "_handle".
    global _handle

    bluetooth_adr = _handle['bluetoothAddress']['value']
    _LOGGER.info("Old config for CC2650 {} plugin {} \n new config {}".format(bluetooth_adr, _handle, new_config))

    # Find diff between old config and new config
    diff = utils.get_diff(_handle, new_config)

    # Plugin should re-initialize and restart if key configuration is changed
    if 'bluetoothAddress' in diff:
        plugin_shutdown(_handle)
        new_handle = plugin_init(new_config)
        _LOGGER.info("Restarting CC2650 {} plugin due to change in configuration keys [{}]".format(bluetooth_adr, ', '.join(diff)))
    else:
        # If tag remains unchanged, just update _handle with new_config values and return the same
        for h in diff:
            _handle[h] = new_config[h]
        new_handle = {}
        for i, v in _handle.items():
            if i != 'tag':
                new_handle[i] = copy.deepcopy(v)
        new_handle['tag'] = _handle['tag']  # tag copied separately as it does not behave well with copy.deepcopy()
    return new_handle


def _plugin_stop(handle):
    """ Stops the plugin doing required cleanup

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
    Raises:
    """
    if 'tag' in handle:
        bluetooth_adr = handle['bluetoothAddress']['value']
        tag = handle['tag']

        if tag.is_connected:
            # Disable sensors
            tag.char_write_cmd(handle['characteristics']['temperature']['configuration']['handle'], char_disable)
            tag.char_write_cmd(handle['characteristics']['luminance']['configuration']['handle'], char_disable)
            tag.char_write_cmd(handle['characteristics']['humidity']['configuration']['handle'], char_disable)
            tag.char_write_cmd(handle['characteristics']['pressure']['configuration']['handle'], char_disable)
            tag.char_write_cmd(handle['characteristics']['movement']['configuration']['handle'], movement_disable)
            tag.disconnect()
        handle.pop('tag', None)
        _LOGGER.info('SensorTagCC2650 {} stopped.'.format(bluetooth_adr))


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup, to be called prior to the South service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
    Raises:
    """
    bluetooth_adr = handle['bluetoothAddress']['value']
    _plugin_stop(handle)
    _LOGGER.info('CC2650 {} plugin shut down.'.format(bluetooth_adr))


def _plugin_restart(bluetooth_adr):
    """ Restarts plugin"""
    global _handle, _restart_config
    _LOGGER.info("Restarting SensorTagCC2650 {} after timeout failure...".format(bluetooth_adr))
    _plugin_stop(_handle)
    plugin_init(_restart_config)

