import argparse
import os
import glob
import random
import time
import cv2
import numpy as np
import darknet
from pathlib import Path
from datetime import datetime
os.umask(0)

class FishDetector:
    def __init__(self):
        self.network = None
        self.class_names = None 
        self.class_colors = None
        self.input = None
        self.save_labels = None
        self.thresh = None
        self.ext_output = None
        self.dont_show = None
        self.load_model()

    def load_model(self):
        share_root = '/dnshare' # TODO your own path from the container
        config_path = f'/home/yolo/darknet/cfg/yolo-fish-cfg/yolo-fish-4.cfg' # TODO your own path from the container
        data_path = f'/home/yolo/darknet/cfg/coco.data' # TODO your own path from the container
        weights_path = f'{share_root}/server/weights/merge_yolo-fish-4.weights' # TODO your own path from the container
        batch_size = 1
        self.input = f'{share_root}/server/images/in/' # TODO your own path from the container
        self.save_labels = True
        self.thresh = .25
        self.ext_output = True
        self.dont_show = True
        random.seed(3)  # deterministic bbox colors

        # load model
        self.network, self.class_names, self.class_colors = darknet.load_network(
            config_path,
            data_path,
            weights_path,
            batch_size=batch_size
        )

    def detect_fishes(self):
        # load model
        timestamp = datetime.now().strftime("%Y.%m.%d-%H:%M:%S")
        images = self.load_images(self.input)
        os.makedirs(f'/dnshare/server/images/out/{timestamp}', exist_ok=True, mode=0o777)
        os.makedirs(f'/dnshare/server/images/count/{timestamp}', exist_ok=True, mode=0o777)
        index = 0
        while True:
            # loop asking for new image paths if no list is given
            if self.input:
                if index >= len(images):
                    break
                image_name = images[index]
            else:
                image_name = input("Enter Image Path: ")
            prev_time = time.time()
            image, detections = self.image_detection(image_name)
            if self.save_labels:
                self.save_annotations(image_name, image, detections, timestamp)
            darknet.print_detections(detections, self.ext_output)
            if not self.dont_show:
                cv2.imshow('Inference', image)
                if cv2.waitKey() & 0xFF == ord('q'):
                    break
            index += 1
            out_path = os.path.join('/dnshare/server/images/out', timestamp, os.path.basename(image_name)) # TODO your own path from the container
            cv2.imwrite(out_path, image) # save image
            os.chmod(out_path, 0o0777)
            
    def save_annotations(self, name, image, detections, timestamp):
        """
        Files saved with image_name.txt and relative coordinates
        """
        file_name = os.path.splitext(name)[0].replace('/in/', f'/count/{timestamp}/') + ".txt" # your own path from the container
        descriptor = os.open(
            path=file_name,
            flags=(
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            ),
            mode=0o777
        )
        with open(descriptor, "w") as f:
            f.write(f'{len(detections)}\n')

    def image_detection(self, image_or_path):
        # Darknet doesn't accept numpy images.
        # Create one with image we reuse for each detect
        width = darknet.network_width(self.network)
        height = darknet.network_height(self.network)
        darknet_image = darknet.make_image(width, height, 3)

        if isinstance(image_or_path, str):
            image = cv2.imread(image_or_path)
        else:
            image = image_or_path
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_resized = cv2.resize(image_rgb, (width, height),
                                interpolation=cv2.INTER_LINEAR)

        darknet.copy_image_from_bytes(darknet_image, image_resized.tobytes())
        detections = darknet.detect_image(self.network, self.class_names, darknet_image, thresh=self.thresh)
        darknet.free_image(darknet_image)
        image = darknet.draw_boxes(detections, image_resized, self.class_colors)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB), detections

    def convert2relative(self, image, bbox):
        """
        YOLO format use relative coordinates for annotation
        """
        x, y, w, h = bbox
        height, width, _ = image.shape
        return x/width, y/height, w/width, h/height

    def load_images(self, images_path):
        """
        If image path is given, return it directly
        For txt file, read it and return each line as image path
        In other case, it's a folder, return a list with names of each
        jpg, jpeg and png file
        """
        input_path_extension = images_path.split('.')[-1]
        if input_path_extension in ['jpg', 'jpeg', 'png']:
            return [images_path]
        elif input_path_extension == "txt":
            with open(images_path, "r") as f:
                return f.read().splitlines()
        else:
            return glob.glob(
                os.path.join(images_path, "*.jpg")) + \
                glob.glob(os.path.join(images_path, "*.png")) + \
                glob.glob(os.path.join(images_path, "*.jpeg"))
            

if __name__ == "__main__":
    # unconmment next line for an example of batch processing
    # batch_detection_example()
    model = FishDetector()
    model.detect_fishes()
