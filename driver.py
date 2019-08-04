#!/usr/bin/python3

import random
import os
import glob
import argparse
import logging
from common import *

def remove_key(d, key):
    del d[key]
    return d


def get_license_plates(cache=[]):
    if len(cache) == 0:
        cache += map(lambda fn: os.path.splitext(os.path.basename(fn))[0],
                     glob.glob(os.path.join(os.path.expanduser(LICENSEPLATE_TEXTURE_PATH), '*.uasset')))
    return cache


def get_all_traffic_video_paths(scale):
    return ['traffic-%03d.mp4' % id for id in range(scale * TRAFFIC_CAMERAS_PER_TILE)]


def get_random_traffic_video_path(scale):
    return random.choice(get_all_traffic_video_paths(scale))


def get_panoramic_video_paths(id):
    return ['panoramic-%03d-%03d.mp4' % (id, index) for index in range(PANORAMIC_CAMERAS_PER_TILE)]


def get_random_caption_path():
    return 'captions'


def get_random_license_plate():
    return random.choice(get_license_plates()).strip()


def query1(scale, resolution, duration):
    x1 = random.randint(0, resolution[0] - 1)
    y1 = random.randint(0, resolution[1] - 1)
    t1 = random.randint(0, duration - 1)
    return {
        'path': get_random_traffic_video_path(scale),
        'x': (x1, random.randint(x1+1, resolution[0])),
        'y': (y1, random.randint(y1+1, resolution[1])),
        't': (t1, random.randint(t1+1, duration))
    }


def query2a(scale, *args):
    return {
        'path': get_random_traffic_video_path(scale),
    }


def query2b(scale, *args):
    return {
        'path': get_random_traffic_video_path(scale),
        'd': random.randint(3, 20)
    }


def query2c(scale, *args):
    return {
        'path': get_random_traffic_video_path(scale),
        'A': 'YOLO',
        'O': random.choice(['Pedestrian', 'Vehicle'])
    }


def query2d(scale, *args):
    return {
        'path': get_random_traffic_video_path(scale),
        'm': random.randint(2, 60),
        'epsilon': random.random()
    }


def query3(scale, resolution, *args):
    return {
        'path': get_random_traffic_video_path(scale),
        'dx': int(resolution[0] / (2 ** random.randint(1, 3))),
        'dy': int(resolution[1] / (2 ** random.randint(1, 3))),
        'B': int(2 ** random.randint(16, 22)),
    }


def query4(scale, *args):
    return {
        'path': get_random_traffic_video_path(scale),
        'alpha': 2 ** random.randint(1, 5),
        'beta': 2 ** random.randint(1, 5)
    }


def query5(scale, *args):
    return {
        'path': get_random_traffic_video_path(scale),
        'alpha': 2 ** random.randint(1, 5),
        'beta': 2 ** random.randint(1, 5)
    }


def query6a(scale, *args):
    return query2c(scale)


def query6b(scale, *args):
    return {
        'path': get_random_traffic_video_path(scale),
        'caption_path': get_random_caption_path()
    }


def query7(scale, *args):
    return {
        'paths': get_all_traffic_video_paths(scale),
        'q2c': remove_key(query2c(scale), "path"),
        'q6a': remove_key(query6a(scale), "path"),
        'q2d': remove_key(query2d(scale), "path")
    }


def query8(scale, *args):
    return {
        'paths': get_all_traffic_video_paths(scale),
        'l': get_random_license_plate(),
        'L': 'OpenAPLR'
    }


def query9(scale, *args):
    return {
        'panorama' + str(id): get_panoramic_video_paths(id)
        for id in range(scale * PANORAMIC_CAMERAS_PER_TILE)
    }

def query10(scale, *args):
    bl = random.randint(16, 21)
    return {**{'bl': bl,
               'bh': random.randint(bl + 1, 22),
               'q5': remove_key(query5(scale), "path")},
            **{'panorama' + str(id): get_panoramic_video_paths(id)
               for id in range(scale * PANORAMIC_CAMERAS_PER_TILE)}
    }


queries = {
    '1':  query1,
    '2a': query2a,
    '2b': query2b,
    '2c': query2c,
    '2d': query2d,
    '3':  query3,
    '4':  query4,
    '5':  query5,
    '6a': query6a,
    '6b': query6b,
    '7':  query7,
    '8':  query8,
    '9':  query9,
    '10': query10
}


def create_batch(id, scale, resolution, duration):
    batch = {
        'query': id,
        'batch': [{'query': queries[id](scale, resolution, duration)}
                      for _ in range(scale * QUERIES_PER_TILE)]
    }

    return batch #{'batch': batch}


def benchmark(path, scale, resolution, duration):
    result = {'source': path, 'batches': []}
    for id in queries.keys():
        result['batches'].append(create_batch(id, scale, resolution, duration))
    return yaml.safe_dump(result)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-r', '--seed',
        metavar='R',
        default=0,
        type=int,
        help='Random number generator seed')
    parser.add_argument(
        'path',
        type=str,
        help='Video dataset path')
    args = parser.parse_args()

    if args.seed:
        random.seed(args.seed)

    configuration = load_configuration(args.path)
    print(benchmark(args.path,
                    configuration['scale'],
                    (configuration['resolution']['width'], configuration['resolution']['height']),
                    configuration['duration']))
