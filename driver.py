import random
import os
import glob
import yaml

QUERIES_PER_SCALE = 4
TRAFFIC_CAMERAS_PER_SCALE = 4
PANORAMIC_CAMERAS_PER_SCALE = 1
PANORAMIC_CAMERAS_PER_POINT = 4
LICENSEPLATE_TEXTURE_PATH = '~/carla/Unreal/CarlaUE4/Content/Carla/Static/GenericMaterials/Licenseplates/Textures'


def remove_key(d, key):
    del d[key]
    return d


def get_license_plates(cache=[]):
    if len(cache) == 0:
        cache += map(lambda fn: os.path.splitext(os.path.basename(fn))[0],
                     glob.glob(os.path.join(os.path.expanduser(LICENSEPLATE_TEXTURE_PATH), '*.uasset')))
    return cache


def get_all_traffic_video_paths(path, scale):
    return [os.path.join(path, '%03d.mp4' % id) for id in range(scale * TRAFFIC_CAMERAS_PER_SCALE)]


def get_random_traffic_video_path(path, scale):
    return random.choice(get_all_traffic_video_paths(path, scale))


def get_panoramic_video_paths(path, id):
    return [os.path.join(path, 'p%03d-%03d.mp4' % (id, index)) for index in range(PANORAMIC_CAMERAS_PER_POINT)]


def get_random_caption_path(path):
    return os.path.join(path, 'captions')


def get_random_license_plate():
    return random.choice(get_license_plates()).strip()


def query1(path, scale, resolution, duration):
    x1 = random.randint(0, resolution[0] - 1)
    y1 = random.randint(0, resolution[1] - 1)
    t1 = random.randint(0, duration - 1)
    return {
        'path': get_random_traffic_video_path(path, scale),
        'x': (x1, random.randint(x1+1, resolution[0])),
        'y': (y1, random.randint(y1+1, resolution[1])),
        't': (t1, random.randint(t1+1, duration))
    }


def query2a(path, scale, *args):
    return {
        'path': get_random_traffic_video_path(path, scale),
    }


def query2b(path, scale, *args):
    return {
        'path': get_random_traffic_video_path(path, scale),
        'd': random.randint(3, 20)
    }


def query2c(path, scale, *args):
    return {
        'path': get_random_traffic_video_path(path, scale),
        'A': 'YOLO',
        'O': ['Pedestrian', 'Vehicle']
    }


def query2d(path, scale, *args):
    return {
        'path': get_random_traffic_video_path(path, scale),
        'm': random.randint(2, 60),
        'epsilon': random.random()
    }


def query3(path, scale, *args):
    return {
        'path': get_random_traffic_video_path(path, scale),
        'dx': int(resolution[0] / (2 ** random.randint(1, 3))),
        'dy': int(resolution[1] / (2 ** random.randint(1, 3))),
        'B': int(2 ** random.randint(16, 22)),
    }


def query4(path, scale, *args):
    return {
        'path': get_random_traffic_video_path(path, scale),
        'alpha': 2 ** random.randint(1, 5),
        'beta': 2 ** random.randint(1, 5)
    }


def query5(path, scale, *args):
    return {
        'path': get_random_traffic_video_path(path, scale),
        'alpha': 2 ** random.randint(1, 5),
        'beta': 2 ** random.randint(1, 5)
    }


def query6a(path, scale, *args):
    return query2c(path, scale)


def query6b(path, scale, *args):
    return {
        'path': get_random_traffic_video_path(path, scale),
        'caption_path': get_random_caption_path(path)
    }


def query7(path, scale, *args):
    return {
        'paths': get_all_traffic_video_paths(path, scale),
        'q2c': remove_key(query2c(path, scale), "path"),
        'q6a': remove_key(query6a(path, scale), "path"),
        'q2d': remove_key(query2d(path, scale), "path")
    }


def query8(path, scale, *args):
    return {
        'paths': get_all_traffic_video_paths(path, scale),
        'l': get_random_license_plate(),
        'L': 'OpenAPLR'
    }


def query9(path, scale, *args):
    return {
        'panorama' + str(id): get_panoramic_video_paths(path, id)
        for id in range(scale * PANORAMIC_CAMERAS_PER_SCALE)
    }

def query10(path, scale, *args):
    bl = random.randint(16, 21)
    return {**{'bl': bl,
               'bh': random.randint(bl + 1, 22),
               'q5': remove_key(query5(path, scale), "path")},
            **{'panorama' + str(id): get_panoramic_video_paths(path, id)
               for id in range(scale * PANORAMIC_CAMERAS_PER_SCALE)}
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


def create_batch(id, path, scale, resolution, duration):
    batch = {
        'query': id,
        'instances': [{'instance': queries[id](path, scale, resolution, duration)}
                      for _ in range(scale * QUERIES_PER_SCALE)]
    }

    return yaml.safe_dump({'batch': batch})


def benchmark(path, scale, resolution, duration):
    for id in queries.keys():
        print(create_batch(id, path, scale, resolution, duration))


if __name__ == '__main__':
    path = '/app'
    scale = 1
    resolution = (1920, 1080)
    duration = 60
    benchmark(path, scale, resolution, duration)
