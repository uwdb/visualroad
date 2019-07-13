#!/usr/bin/python3

import os
import subprocess
import glob
import argparse
import logging

def transcode_video(input_filename, output_filename):
    logging.info("Compressing " + input_filename)
    if subprocess.run(['ffmpeg',
                       '-y',
                       '-i', input_filename,
                       '-codec', 'h264',
                       output_filename]).returncode == 0:
        os.remove(input_filename)


def transcode_videos(path):
    logging.info("Compressing dataset %s", path)
    for filename in glob.glob(os.path.join(path, '_*.mp4')):
        transcode_video(filename, filename.replace('_', ''))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        'path',
        help='Dataset output path')
    args, unknown = argparser.parse_known_args()

    transcode_videos(args.path)
