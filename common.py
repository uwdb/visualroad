import os
import carla
import yaml

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
LICENSEPLATE_TEXTURE_PATH = '~/carla/Unreal/CarlaUE4/Content/Carla/Static/GenericMaterials/Licenseplates/Textures'
LOSSLESS_PSNR_THRESHOLD = 40

maps = ['Town01', 'Town02', 'Town03', 'Town04', 'Town05', 'Town07']
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
