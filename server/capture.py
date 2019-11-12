import cv2
import time
import os
import sys
import json
import base64
import functools
from multiprocessing import Pool
from multiprocessing import cpu_count
from google.cloud import vision
from google.cloud import storage
from pydub import AudioSegment

video_path = '../FACIAL_EXPR.mp4'
google_bucket = 'audio-hackprinceton19'
client = vision.ImageAnnotatorClient()
debug_mode = 1

def video_to_mp3(file_name):
    """ Transforms video file into a MP3 file """
    try:
        file, extension = os.path.splitext(file_name)
        # Convert video into .wav file
        os.system('ffmpeg -y -ac 1 -i {file}{ext} {file}.wav'.format(file=file, ext=extension))
        print("Grabbing %s.wav" % file)
        sound = AudioSegment.from_wav("%s.wav" % file)
        sound = sound.set_channels(1)
        sound.export("%s.wav" % file, format="wav")
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(google_bucket)
        blob = bucket.blob('video.wav')
        blob.upload_from_filename("%s.wav" % file)
    except OSError as err:
        print(err.reason)
        exit(1)


def analyze_frame(frame):
    print("Analyzing frame %d" % frame)
    # Success - indicates a succesful read on frame
    success = False
    # image - raw data when reading a frame
    image = None
    # VidCap object
    vid = cv2.VideoCapture(video_path)
    # Seek to specific time, frame, in milliseconds
    vid.set(cv2.CAP_PROP_POS_MSEC, frame)
    success, image = vid.read()
    vid.release()
    if(success):
        print("Successful read on frame %d" % frame)
        response = None
        filename = 'opencv%d.png' % frame
        # Write image data to file and read to base64encode and send to google
        cv2.imwrite(filename, image)
        with open(filename, 'rb') as image:
            content = image.read()
            encoded = base64.b64encode(content)
            response = client.face_detection({
                'content': content,
            })
        print("Succesfully returned from google on frame %d" % frame)
        joy = 1
        sorrow = 1
        surprise = 1
        anger = 1
        # Response.face_annotations is a list of sentiment analysis
        # for faces it detects. We assume the main face in frame will always be
        # patients so we take face_annotations[0]
        if(len(response.face_annotations) > 0):
            joy = response.face_annotations[0].joy_likelihood
            sorrow = response.face_annotations[0].sorrow_likelihood
            surprise = response.face_annotations[0].surprise_likelihood
            anger = response.face_annotations[0].anger_likelihood
        data = {
            'image': encoded.decode("utf-8"),
            'joy': joy,
            'sorrow': sorrow,
            'surprise': surprise,
            'anger': anger,
        }
        # Dump useful metadata for debuggin purposes
        if(debug_mode):
            data['file'] = filename
    print("Done frame analysis on frame %d" % frame)
    return data


def main(intervals = 5000):
    # Extract WAV file to transcribing
    video_to_mp3(video_path)
    # Figure out duration of video
    vid = cv2.VideoCapture(video_path)
    vid.set(cv2.CAP_PROP_POS_AVI_RATIO,1)
    duration = vid.get(cv2.CAP_PROP_POS_MSEC)
    vid.release()
    # Create list of timestamps in milliseconds of which frames we need to analyze
    frames_needed = [i for i in range(0, int(duration), intervals)]
    # Multiprocessing!!!!
    workers = min(len(frames_needed), cpu_count() * 2)
    print("Initialized a pool of %d workers" % workers)
    with Pool(workers) as p:
        results = p.map(analyze_frame, frames_needed)
    print("Analyzed %d frames" % len(results))
    # Dump list of responses to json file
    with open('data.json', 'w') as file:
        json.dump(results, file, indent=4)

if __name__ == "__main__":
    start = time.time()
    if len(sys.argv) > 1:
        main(int(sys.argv[1]))
    print("Processing time: %f seconds" % (time.time() - start))
