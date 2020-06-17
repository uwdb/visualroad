import time
import os
import subprocess
import signal
import psutil
import carla
import yaml
import logging
import glob

VERSION = 1.0
QUERIES_PER_TILE = 4
TILES_SCALE_MULTIPLIER = 1
TRAFFIC_CAMERAS_PER_TILE = 4
PANORAMIC_CAMERAS_PER_TILE = 1
CAMERA_HEIGHT = 4
FPS = 30
INITIALIZATION_FRAME_SLACK = 90
PANORAMIC_COUNT = 4
PANORAMIC_FOV = 120
CONFIGURATION_FILENAME = 'configuration.yml'
LOSSLESS_PSNR_THRESHOLD = 40
FRAME_DELTA_SECONDS = 0.04
JITTER_LIMIT = 3.0

CARLA_PROCESS_NAME = 'CarlaUE4'
LICENSEPLATE_TEXTURE_PATH = '~/carla/Unreal/CarlaUE4/Content/Carla/Static/GenericMaterials/Licenseplates/Textures'

maps = ['Town01', 'Town02', 'Town03', 'Town04', 'Town05']
traffic_density = [50, 100, 200]
pedestrian_density = [100, 250, 400]
weather = [
    carla.WeatherParameters.Default,
    carla.WeatherParameters.ClearNoon,
    carla.WeatherParameters.CloudyNoon,
    carla.WeatherParameters.WetNoon,
    carla.WeatherParameters.WetCloudyNoon,
    carla.WeatherParameters.MidRainyNoon,
    carla.WeatherParameters.HardRainNoon,
    carla.WeatherParameters.SoftRainNoon,
    carla.WeatherParameters.ClearSunset,
    carla.WeatherParameters.CloudySunset,
    carla.WeatherParameters.WetSunset,
    carla.WeatherParameters.WetCloudySunset,
    carla.WeatherParameters.MidRainSunset,
    carla.WeatherParameters.HardRainSunset,
    carla.WeatherParameters.SoftRainSunset]


def load_configuration(path):
    with open(os.path.join(path, CONFIGURATION_FILENAME), 'r') as stream:
        configuration = yaml.safe_load(stream)
        configuration['path'] = path
        return configuration


def is_carla_running():
    return any([p for p in psutil.process_iter(attrs=['name'])
                if p.info['name'] == 'CarlaUE4'])


def start_carla(seed, fps=30, quality='Epic', executable=None):
    if is_carla_running():
        stop_carla()

    executable = executable or os.environ['CARLA_EXECUTABLE']
    subprocess.Popen([executable,
                      '-benchmark',
                      '-fps=%d' % fps,
                      '-quality-level=%s' % quality,
                      '-fixedseed=%d' % int(seed)], cwd=os.path.dirname(executable))
    time.sleep(360)


def stop_carla():
    if is_carla_running():
        process = next(p for p in psutil.process_iter(attrs=['name'])
                       if p.info['name'] == os.path.basename(os.environ['CARLA_EXECUTABLE']))
        process.send_signal(signal.SIGINT)
        time.sleep(360)


def transcode_video(input_filename, output_filename):
    logging.info("Compressing " + input_filename)

    try:
        if subprocess.call(['ffmpeg',
                            '-y',
                            '-i', input_filename,
                            '-codec', 'h264',
                            output_filename]) == 0:
            os.remove(input_filename)
    except e:
        logging.error(e)


def transcode_videos(path):
    logging.info("Compressing dataset %s", path)
    for filename in glob.glob(os.path.join(path, '*.mp4')):
        transcode_video(filename, filename.replace('_', ''))
