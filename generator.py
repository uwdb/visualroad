#!/usr/bin/python3

import time
import os
import subprocess
import random
import time
import glob
import itertools
import carla
import numpy as np
import cv2
import argparse
import yaml
import logging
from common import *


class Configuration:
    def __init__(self, client, id, path, scale, resolution, duration, panorama_fov, vehicle_locations, walker_locations, traffic_camera_locations, panoramic_camera_locations):
        self.client = client
        self.id = id
        self.world = client.get_world()
        self.path = path
        self.scale = scale
        self.resolution = resolution
        self.duration = duration
        self.panorama_fov = panorama_fov or PANORAMIC_FOV
        self.all_walker_locations = self._shuffle([location for location in walker_locations])
        self.remaining_vehicle_locations = self._shuffle(list(vehicle_locations))
        self.remaining_walker_locations = self.all_walker_locations
        self.remaining_traffic_camera_locations = self._shuffle(list(traffic_camera_locations))
        self.remaining_panoramic_camera_locations = self._shuffle(list(panoramic_camera_locations))

        if not os.path.exists(path):
            os.makedirs(path)

    def next_vehicle_location(self):
        return self.remaining_vehicle_locations.pop() if self.remaining_vehicle_locations else None

    def next_walker_location(self):
        return self.remaining_walker_locations.pop()

    def next_traffic_camera_location(self):
        return self.remaining_traffic_camera_locations.pop()

    def next_panoramic_camera_location(self):
        location = self.remaining_panoramic_camera_locations.pop()
        location.z = CAMERA_HEIGHT
        return location

    @staticmethod
    def _shuffle(l):
        random.shuffle(l)
        return l

    @staticmethod
    def draw_n(f, count):
        result = set()
        while len(result) < count:
            result.add(f())
        return result


class Tile:
    def __init__(self, map, weather, vehicles, walkers):
        self.map = map
        self.weather = weather
        self.vehicles = vehicles
        self.walkers = walkers

    def __str__(self):
        return 'Map: {}, Weather: {}, Vehicles: {}, Walkers: {}'.format(
                   self.map, self.weather, self.vehicles, self.walkers)

tile_pool = [Tile(*tuple) for tuple in itertools.product(maps, weather, traffic_density, pedestrian_density)]

SpawnActor = carla.command.SpawnActor
SetAutopilot = carla.command.SetAutopilot
FutureActor = carla.command.FutureActor


def create_listener(configuration, type, id):
    count = [-INITIALIZATION_FRAME_SLACK]
    writer = [cv2.VideoWriter(os.path.join(configuration.path, '_%s-%03d.mp4' % (type, id)),
                             cv2.VideoWriter_fourcc(*'mp4v'), FPS, configuration.resolution)]

    def close():
        count[0] = float("-inf")
        writer[0].release()
        writer.clear()

    def listener(image):
        if 0 <= count[0] <= FPS * configuration.duration:
            if 'semantic' in type:
                image.convert(carla.ColorConverter.CityScapesPalette)
            data = image.raw_data
            image = np.asarray(data, np.uint8).reshape(configuration.resolution[1], configuration.resolution[0], 4)[:,:,:3]
            writer[0].write(image)
        count[0] += 1

    listener.close = close
    listener.count = count

    return listener


def create_camera(configuration, type, id, transform=None, fov=90, yaw=None, location=None,
                  blueprint_name='sensor.camera.rgb'):
    blueprint = configuration.world.get_blueprint_library().find(blueprint_name)

    blueprint.set_attribute('image_size_x', str(configuration.resolution[0]))
    blueprint.set_attribute('image_size_y', str(configuration.resolution[1]))
    blueprint.set_attribute('fov', str(fov))

    if not transform:
        transform = transform or configuration.next_traffic_camera_location()
        transform.location = location or transform.location
        transform.location += carla.Location(z=CAMERA_HEIGHT)
        transform.rotation.yaw = yaw or transform.rotation.yaw
        transform.rotation.yaw += random.randint(-fov/2, fov/2) + random.choice([0, 180])
    else:
        transform.rotation.yaw = yaw or transform.rotation.yaw

    camera = configuration.world.spawn_actor(blueprint, transform)
    listener = create_listener(configuration, type, id)
    camera.count = listener.count
    camera.close = listener.close
    camera.requested_transform = transform
    camera.listen(listener)

    return camera


def create_semantic_camera(configuration, id, transform, prefix='traffic'):
    return create_camera(configuration, 'semantic-' + prefix, id, transform=transform, blueprint_name='sensor.camera.semantic_segmentation')


def create_traffic_cameras(configuration):
    cameras = []
    tile_base_id = configuration.id * TRAFFIC_CAMERAS_PER_TILE
    for id in range(TRAFFIC_CAMERAS_PER_TILE): # scale * TRAFFIC_SCALE_MULTIPLIER):
        cameras.append(create_camera(configuration, 'traffic', tile_base_id + id))
        cameras.append(create_semantic_camera(configuration, tile_base_id + id, transform=cameras[-1].requested_transform))
    return cameras


def create_panoramic_camera(configuration, id):
    cameras = []
    yaw = random.randint(0, 360)
    transform = carla.Transform(location=configuration.next_panoramic_camera_location())
    for sub_id in range(PANORAMIC_COUNT):
        cameras.append(create_camera(configuration, 'panoramic-%03d' % id, sub_id, transform=transform, fov=configuration.panorama_fov, yaw=yaw))
        cameras.append(create_semantic_camera(configuration, sub_id, prefix='panoramic-%03d' % id, transform=transform))
        yaw += 360 / PANORAMIC_COUNT
    return cameras


def create_panoramic_cameras(configuration):
    cameras = []
    for id in range(PANORAMIC_CAMERAS_PER_TILE): #scale * PANORAMIC_SCALE_MULTIPLIER):
        cameras += create_panoramic_camera(configuration, configuration.id + id)
    return cameras


def create_vehicle(configuration):
    blueprint = random.choice(configuration.world.get_blueprint_library().filter('vehicle'))
    if blueprint.has_attribute('color'):
        color = random.choice(blueprint.get_attribute('color').recommended_values)
        blueprint.set_attribute('color', color)

    transform = configuration.next_vehicle_location()
    return SpawnActor(blueprint, transform).then(SetAutopilot(FutureActor, True)) if transform else None


def create_vehicles(configuration, count):
    vehicles = []
    for _ in range(count):
        vehicles.append(create_vehicle(configuration))
    return [actor for actor in configuration.client.apply_batch_sync([v for v in vehicles if not v is None], True) if not actor.error]


def create_walker(configuration, index):
    blueprint = random.choice(configuration.world.get_blueprint_library().filter('walker.pedestrian.*'))
    blueprint.set_attribute('is_invincible', 'false')

    location = configuration.all_walker_locations[index]
    walker = SpawnActor(blueprint, carla.Transform(location=location))

    return walker


def create_walkers(configuration, count):
    batch = [create_walker(configuration, index) for index in range(count)]
    walkers = [response for response in configuration.client.apply_batch_sync(batch, True) if not response.error]

    batch = [create_walker_controller(configuration, walker) for walker in walkers]
    controllers = [response for response in configuration.client.apply_batch_sync(batch, True) if not response.error]
    actors = configuration.world.get_actors([result.actor_id for result in configuration.client.apply_batch_sync(batch, True) if not result.error])

    [start_walker(configuration, controller, index) for index, controller in enumerate(actors)]

    return walkers, controllers


def create_walker_controller(configuration, walker):
    blueprint = configuration.world.get_blueprint_library().find('controller.ai.walker')
    return SpawnActor(blueprint, carla.Transform(), walker.actor_id)


def start_walker(configuration, controller, index):
    controller.start() #configuration.all_walker_locations[index])
    controller.go_to_location(random.choice(configuration.all_walker_locations))
    controller.set_max_speed(1 + random.random())


def is_complete(id, scale, cameras, duration, start_time):
    frame_count = max(0, min([camera.count[0] for camera in cameras]))
    total_frames = duration * FPS
    fps = max(frame_count / (time.time() - start_time + 0.00001), 0)
    logging.info('Tile %d of %d: Rendered %d frames; %d remaining (%.1f FPS)', id + 1, scale, frame_count, total_frames - frame_count, fps)
    return frame_count >= duration * FPS


def generate_tile(client, path, id, tile, scale, resolution, duration, panorama_fov):
    traffic_cameras = []
    panoramic_cameras = []
    vehicles = []
    walkers = []
    controllers = []

    client.load_world(tile.map)

    time.sleep(10)

    world = client.get_world()
    world.set_weather(tile.weather)
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = FRAME_DELTA_SECONDS
    world.apply_settings(settings)

    configuration = Configuration(
        client,
        id=id,
        path=path,
        scale=scale,
        resolution=resolution,
        duration=duration,
        panorama_fov=panorama_fov,
        vehicle_locations=world.get_map().get_spawn_points(),
        walker_locations=Configuration.draw_n(world.get_random_location_from_navigation, tile.walkers),
        traffic_camera_locations=world.get_map().get_spawn_points(),
        panoramic_camera_locations=Configuration.draw_n(world.get_random_location_from_navigation, tile.walkers))
    start_time = time.time()

    try:
        walkers, controllers = create_walkers(configuration, tile.walkers)
        vehicles = create_vehicles(configuration, tile.vehicles)
        traffic_cameras = create_traffic_cameras(configuration)
        panoramic_cameras = create_panoramic_cameras(configuration)

        while not is_complete(id, scale, traffic_cameras + panoramic_cameras, duration, start_time):
            [world.tick() for _ in range(10)]

    finally:
        logging.info('Destroying actors')

        try:
            [camera.close() for camera in traffic_cameras + panoramic_cameras]
            [camera.stop() for camera in traffic_cameras + panoramic_cameras]
            #[controller.stop() for controller in world.get_actors([c.actor_id for c in controllers])]

            client.apply_batch_sync([carla.command.DestroyActor(c) for c in traffic_cameras] +
                                    [carla.command.DestroyActor(c) for c in panoramic_cameras] +
                                    [carla.command.DestroyActor(v.actor_id) for v in vehicles] +
                                    [carla.command.DestroyActor(c.actor_id) for c in controllers] +
                                    [carla.command.DestroyActor(w.actor_id) for w in walkers])
        except RuntimeError as e:
            logging.error(e)

    logging.info('Generation complete for tile %d', id)


def write_configuration(path, tiles, scale, resolution, duration, panorama_fov, seed, hostname, port, timeout):
    configuration = {
        'version': VERSION,
        'name': os.path.basename(path),
        'scale': scale,
        'resolution': {'width': resolution[0], 'height': resolution[1]},
        'duration': duration,
        'panorama_fov': panorama_fov,
        'seed': seed,
        'hostname': hostname,
        'port': port,
        'timeout': timeout,
        'tiles': [
            {'id': tileid,
             'map': tile.map,
             'weather': str(tile.weather),
             'vehicles': tile.vehicles,
             'pedestrians': tile.walkers,
             'cameras': [
                {
                    'type': 'traffic',
                    'videos': [os.path.join(path, 'traffic-%03d.mp4' % (tileid * TRAFFIC_CAMERAS_PER_TILE + cameraid))]
                } for cameraid in range(TRAFFIC_CAMERAS_PER_TILE)] + [
                {
                    'type': 'panoramic',
                    'videos': [
                        os.path.join(path, 'panoramic-%03d-%03d.mp4' % (tileid * PANORAMIC_CAMERAS_PER_TILE + panoramicid, index))
                        for index in range(PANORAMIC_COUNT)]
                } for panoramicid in range(PANORAMIC_CAMERAS_PER_TILE)]
            }
            for tileid, tile in enumerate(tiles)],
    }

    filename = os.path.join(path, CONFIGURATION_FILENAME)

    if not os.path.exists(path):
        os.makedirs(path)
    if os.path.exists(filename):
        os.replace(filename, filename + '.bak')

    with open(filename, 'w') as file:
        yaml.dump(configuration, file)


def generate(path, tiles, scale, resolution, duration, panorama_fov, seed=None, vehicles=None, walkers=None, hostname='localhost', port=2000, timeout=150):
    random.seed(seed)

    try:
        start_carla(seed)

        write_configuration(path, [], scale, resolution, duration, panorama_fov, seed, hostname, port, timeout)

        client = carla.Client(hostname, port)
        client.set_timeout(timeout)
        used_tiles = []

        for id in range(scale * TILES_SCALE_MULTIPLIER):
            used_tiles.append(random.choice(tiles))
            if not vehicles is None:
                used_tiles[-1].vehicles = vehicles
            if not walkers is None:
                used_tiles[-1].walkers = walkers
            logging.info(used_tiles[-1])
            write_configuration(path, used_tiles, scale, resolution, duration, panorama_fov, seed, hostname, port, timeout)
            generate_tile(client, path, id, used_tiles[-1], scale, resolution, duration, panorama_fov)

        transcode_videos(path)
    finally:
        stop_carla()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-s', '--scale',
        metavar='S',
        type=int,
        default=1,
        help='Dataset scale value')
    parser.add_argument(
        '-w', '--width',
        metavar='W',
        default=960,
        type=int,
        help='Camera resolution width in pixels')
    parser.add_argument(
        '-t', '--height',
        metavar='H',
        default=540,
        type=int,
        help='Camera resolution height in pixels')
    parser.add_argument(
        '-d', '--duration',
        metavar='D',
        default=30,
        type=int,
        help='Generation duration time in seconds')
    parser.add_argument(
        '-r', '--seed',
        metavar='R',
        default=0,
        type=int,
        help='Random number generator seed')
    parser.add_argument(
        '--vehicles',
        metavar='VEHICLES',
        default=None,
        type=int,
        help='Override tile parameters and force number of vehicles to a specific number')
    parser.add_argument(
        '--pedestrians',
        metavar='PEDESTRIANS',
        default=None,
        type=int,
        help='Override tile parameters and force number of pedestrians to a specific number')
    parser.add_argument(
        '-f', '--fov',
        metavar='FOV',
        default=None,
        type=int,
        help='Field of view of panoramic cameras')
    parser.add_argument(
        '-o', '--hostname',
        default='localhost',
        help='Server engine hostname')
    parser.add_argument(
        '-p', '--port',
        default=2000,
        type=int,
        help='Server engine port')
    parser.add_argument(
        'path',
        help='Dataset output path')
    args = parser.parse_args()

    if not os.path.isabs(args.path):
        args.path = os.path.join(os.environ['OUTPUT_PATH'], args.path)

    generate(args.path, tile_pool, args.scale, (args.width, args.height), args.duration, args.fov, args.seed, args.vehicles, args.pedestrians)
