#!/usr/bin/python3

import subprocess
import cv2
import tempfile
import logging
import argparse
import numpy as np
from sklearn.metrics import jaccard_similarity_score
from itertools import zip_longest
from common import *


ALL_QUERIES = "1,2a,2b,2c,2d,3,4,5,6a,6b".split(',')

def load_yaml(filename):
    with open(filename, 'r') as stream:
        return yaml.safe_load(stream)


def load_queries(filename):
    return load_yaml(filename)


def load_results(filename):
    return load_yaml(filename)


def get_queries(queries, query_id):
    queries = next(batch for batch in queries['batches'] if batch['query'] == str(query_id))['batch']
    return [q['query'] for q in queries]


def get_results(results, query_id):
    return next(result for result in results if result['query'] == str(query_id))['result']


def get_writer(filename, reader, width=None, height=None):
    fps = reader.get(cv2.CAP_PROP_FPS)
    width = width or int(reader.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = height or int(reader.get(cv2.CAP_PROP_FRAME_HEIGHT))

    return cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height), True)


def assert_psnr(filename, reference_filename, threshold):
    subprocess.run(['./assert-psnr.sh', filename, reference_filename, str(threshold)])


def validate_query(query_id, queries, dataset, results, validator):
    logging.info('Validating Q%s', query_id)

    for i, (query, result_filename) in enumerate(zip_longest(get_queries(queries, query_id), get_results(results, query_id))):
        logging.info('Instance %d', i)

        validator(dataset, query, result_filename)


def validate_q1(dataset, query, result_filename):
    with tempfile.NamedTemporaryFile(suffix='.mp4') as output:
        index = 0
        result = True
        reader = cv2.VideoCapture(os.path.join(dataset['path'], query['path']))
        writer = get_writer(output.name, reader,
                            width=query['x'][1] - query['x'][0] + 1,
                            height=query['y'][1] - query['y'][0] + 1)

        while result:
            index += 1
            result, frame = reader.read()
            if result and index in range(*query['t']):
                cropped = frame[query['y'][0]:query['y'][1] + 1, query['x'][0]:query['x'][1] + 1, :]
                writer.write(cropped)

        writer.release()

        assert_psnr(result_filename, output.name, LOSSLESS_PSNR_THRESHOLD)


def validate_q2a(dataset, query, result_filename):
    with tempfile.NamedTemporaryFile(suffix='.mp4') as output:
        reader = cv2.VideoCapture(os.path.join(dataset['path'], query['path']))
        writer = get_writer(output.name, reader)
        result = True

        while result:
            result, frame = reader.read()
            if result:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                writer.write(gray)

        writer.release()

        assert_psnr(result_filename, output.name, LOSSLESS_PSNR_THRESHOLD)


def validate_q2b(dataset, query, result_filename):
    with tempfile.NamedTemporaryFile(suffix='.mp4') as output:
        reader = cv2.VideoCapture(os.path.join(dataset['path'], query['path']))
        writer = get_writer(output.name, reader)
        kernel = query['d']
        result = True

        while result:
            result, frame = reader.read()
            if result:
                blurred = cv2.blur(frame, (kernel, kernel))
                writer.write(blurred)

        writer.release()

        assert_psnr(result_filename, output.name, LOSSLESS_PSNR_THRESHOLD)


def validate_q2c(dataset, query, result_filename):
    segment_colors = {'pedestrian': (60, 20, 220), 'vehicle': (142, 0, 0)}  # BGR
    objects = query['objects'] if 'objects' in query else ['pedestrian', 'vehicle']
    threshold = 50

    truth_reader = cv2.VideoCapture(os.path.join(dataset['path'], query['path']))
    result_reader = cv2.VideoCapture(result_filename)
    segmented_result = True
    index = 0
    iou_total = 0

    while segmented_result:
        segmented_result, segmented_frame = truth_reader.read()
        result_result, result_frame = result_reader.read()
        truth_frame= np.full_like(segmented_result, 0)
        index += 1

        if not result_result and segmented_result:
            raise RuntimeError("Unexpected EOF in result video.")
        elif not segmented_result and result_result:
            raise RuntimeError("Too many frames in result video.")
        elif segmented_result:
            # Generate truth frame
            for object in objects:
                color = segment_colors[object]
                thresholded = cv2.inRange(segmented_frame, tuple(t - threshold for t in color),
                                                           tuple(t + threshold for t in color))
                _, contours, hierarchy = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(truth_frame, (x, y), (x + w, y + h), color, cv2.FILLED)

            # For each class, compare to result frame
            for object in objects:
                color = segment_colors[object]
                thresholded_result = cv2.inRange(result_frame, color, color)
                thresholded_truth = cv2.inRange(truth_frame, color, color)
                iou = jaccard_similarity_score(thresholded_result, thresholded_truth)
                iou_total += iou
                if iou < JACCARD_THRESHOLD:
                    print('FAIL: calculated Jaccard {} below limit of {} on frame {}'.format(
                        iou, JACCARD_THRESHOLD, index))
                    return

    print('PASS: Mean Jaccard {}'.format(iou_total / index))


def validate_q2d(dataset, query, result_filename):
    with tempfile.NamedTemporaryFile(suffix='.mp4') as output:
        reader = cv2.VideoCapture(os.path.join(dataset['path'], query['path']))
        writer = get_writer(output.name, reader)

        window_size = query['m']
        epsilon = query['epsilon']
        omega = 0
        result = True
        queue = []

        def write_frame():
            mean = np.average(queue, axis=0)
            current = queue.pop(0)
            current[np.abs(current - mean) < epsilon] = omega
            writer.write(current)

        while result:
            result, frame = reader.read()
            if result:
                queue.append(frame)
            if len(queue) >= window_size:
                write_frame()

        while queue:
            write_frame()

        writer.release()

        assert_psnr(result_filename, output.name, LOSSLESS_PSNR_THRESHOLD)


def validate_q3(dataset, query, result_filename):
    raise RuntimeError("Unimplemented")


def validate_q4(dataset, query, result_filename):
    with tempfile.NamedTemporaryFile(suffix='.mp4') as output:
        reader = cv2.VideoCapture(os.path.join(dataset['path'], query['path']))
        writer = get_writer(output.name, reader)

        alpha = query['alpha']
        beta = query['beta']
        width = int(reader.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(reader.get(cv2.CAP_PROP_FRAME_HEIGHT))
        result = True

        while result:
            result, frame = reader.read()
            if result:
                resized = cv2.resize(frame, (height*beta, width*alpha), cv2.INTER_LINEAR)
                writer.write(resized)

        writer.release()

        assert_psnr(result_filename, output.name, LOSSLESS_PSNR_THRESHOLD)


def validate_q5(dataset, query, result_filename):
    with tempfile.NamedTemporaryFile(suffix='.mp4') as output:
        reader = cv2.VideoCapture(os.path.join(dataset['path'], query['path']))
        writer = get_writer(output.name, reader)

        alpha = query['alpha']
        beta = query['beta']
        width = int(reader.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(reader.get(cv2.CAP_PROP_FRAME_HEIGHT))
        result = True

        while result:
            result, frame = reader.read()
            if result:
                resized = cv2.resize(frame, (int(height / beta), int(width / alpha)), cv2.INTER_LINEAR)
                writer.write(resized)

        writer.release()

        assert_psnr(result_filename, output.name, LOSSLESS_PSNR_THRESHOLD)


def validate_q6a(dataset, query, result_filename):
    raise RuntimeError("Unimplemented")


def validate_q6b(dataset, query, result_filename):
    raise RuntimeError("Unimplemented")


VERIFIERS = {
    '1':  validate_q1,
    '2a': validate_q2a,
    '2b': validate_q2b,
    '2c': validate_q2c,
    '2d': validate_q2d,
    '3':  validate_q3,
    '4':  validate_q4,
    '5':  validate_q5,
    '6a': validate_q6a,
    '6b': validate_q6b
}


def validate(validate_set, queries_filename, dataset_path, results_filename):
    queries = load_queries(queries_filename)
    dataset = load_configuration(dataset_path or queries['source'])
    results = load_results(results_filename)

    for q in validate_set:
        if q in VERIFIERS:
            validate_query(q, queries, dataset, results, VERIFIERS[q])
        else:
            print('Unsupported query {} in verifier'.format(q))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v', '--validate',
        metavar='V',
        default='all',
        type=str,
        help='Comma-separated list of queries to verify (e.g., "1,2a") or "all"')
    parser.add_argument(
        '-q', '--queries',
        metavar='Q',
        required=True,
        type=str,
        help='Query metadata YAML filename')
    parser.add_argument(
        '-d', '--dataset',
        metavar='D',
        required=False,
        default=None,
        type=str,
        help='Video dataset path')
    parser.add_argument(
        '-r', '--results',
        metavar='R',
        required=True,
        type=str,
        help='Query result YAML filename')
    args = parser.parse_args()

    validate(map(str.strip, args.validate.split(',')) if args.validate != 'all' else ALL_QUERIES,
             args.queries, args.dataset, args.results)
