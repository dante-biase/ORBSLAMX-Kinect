import os
import subprocess
from pathlib import Path

from ruamel.yaml import YAML
from envbash import load_envbash

from config import orbslam, kinect


def exec_cmd(*args):
    return subprocess.check_call(' '.join(args), shell=True, env=os.environ)   # return call result if needed


def main():
    # setup ORB SLAM variables
    orbslam.PATH = os.path.expanduser(orbslam.PATH)
    orbslam.VERSION = os.path.basename(orbslam.PATH)
    orbslam.VOCAB_FILE_PATH = f"{orbslam.PATH}/Vocabulary/ORBvoc.txt"

    # lightly validate configuration
    if not os.path.exists(orbslam.PATH):
        raise FileNotFoundError(f"\"{orbslam.PATH}\" not found")
    if orbslam.MODE not in {"rgb", "rgbd", "rgbdl"}:
        raise ValueError("invalid mode \"{}\", select from [rgb, rgbd, rgbdl]")
    elif orbslam.VERSION == "ORB_SLAM2_CUDA" and orbslam.MODE not in {"rgb", "rgbdl"}:
        raise ValueError("invalid mode \"{}\" for ORB_SLAM2_CUDA, select from [rgb, rgbdl]")

    # automatically select and load the appropriate kinect camera settings file based on the configured MODE
    kinect.SETTINGS_FILE_PATH = os.path.abspath(f"./camera_settings/Kinect_{orbslam.MODE}.yaml")
    settings_file = Path(kinect.SETTINGS_FILE_PATH)
    settings = yaml.load(settings_file)

    # update camera settings based on configuration
    settings["Camera.width"] = orbslam.IMG_SIZE[0]
    settings["Camera.height"] = orbslam.IMG_SIZE[1]
    settings["Camera.fps"] = float(kinect.FPS)
    settings["ORBextractor.nFeatures"] = orbslam.NUM_FEATURES

    # overwrite the kinect camera settings file with the new settings
    yaml.dump(settings, settings_file)

    # automatically select the camera image and info topic based on the configured MODE
    if orbslam.MODE == "rgb":
        orbslam.ROS_NODE = "Mono"
        kinect.IMAGE_TOPIC = "/rgb/image_raw"
        kinect.INFO_TOPIC = "/rgb/camera_info"
    elif orbslam.MODE == "rgbdl":
        orbslam.ROS_NODE = "Mono"
        kinect.IMAGE_TOPIC = "/rgb_to_depth/image_raw"
        kinect.INFO_TOPIC = "/rgb_to_depth/camera_info"
    elif orbslam.MODE == "rgbd":
        orbslam.ROS_NODE = "RGBD"
        kinect.IMAGE_TOPIC = "/rgb_to_depth/image_raw"
        kinect.INFO_TOPIC = "/rgb_to_depth/camera_info"

    # kill any pre-existing ROS or ORB SLAM related processes
    for process_name in ["roscore", "roslaunch", "rosrun", "azure_kinect_ros_driver", "Mono", "RGBD"]:
        os.system(f"killall {process_name}")
    os.system("wait")

    # print test header
    print()
    print(f"{orbslam.VERSION} INSTALLATION TEST")
    print('-' * 79)
    print('-' * 79)
    print('-' * 79)

    load_envbash(os.path.expanduser("~/catkin-ws/devel/setup.bash"), override=True)    # equivalent to "source ~/catkin-ws/devel/setup.bash"

    # launch the Kinect driver node
    exec_cmd(
	"roslaunch",
	"--wait", 
	"azure_kinect_ros_driver", 
	"driver.launch", 
	"color_enabled:=true", 
	f"depth_mode:={kinect.DEPTH_MODE}", 
	f"color_resolution:={kinect.COLOR_RESOLUTION}", 
	f"fps:={kinect.FPS}", 
	"&"
    )

    # launch the ros_imgresize node:
    # 1. the ros_imresize node will subscribe to the Kinect's camera image output topic -> kinect.IMAGE_TOPIC
    # 2. resize the image to orbslam.IMAGE_WIDTH and orbslam.IMAGE_HEIGHT
    # 3. publish the transformed image to topic -> kinect.IMAGE_TOPIC + "_crop"
    kinect.IMAGE_RESIZED_TOPIC = kinect.IMAGE_TOPIC + "_crop"
    exec_cmd(
	"roslaunch", 
	"ros_imresize", 
	"imresize.launch", 
	f"width:={orbslam.IMG_SIZE[0]}", 
	f"height:={orbslam.IMG_SIZE[1]}", 
	f"camera_topic:={kinect.IMAGE_TOPIC}", 
	f"camera_info:={kinect.INFO_TOPIC}", 
	"undistord:=false", 
	"&"
    )

    # prepare for takeoff
    os.system("sleep 8")
    os.environ["ROS_PACKAGE_PATH"] = "{}:{}/Examples/ROS".format(os.environ["ROS_PACKAGE_PATH"], orbslam.PATH)    # equivalent to "export ROS_PACKAGE_PATH=$ROS_PACKAGE_PATH:~/${ORB_SLAM_PATH}/Examples/ROS"
    os.chdir(f"{orbslam.PATH}/Examples/ROS/{orbslam.VERSION}")

    # start ORB SLAM
    if orbslam.VERSION == "ORB_SLAM2_CUDA":
        # if ORB SLAM2 CUDA, can only run Mono:
        exec_cmd(
            "roslaunch", 
            "./launch/ros_mono.launch", 
            "bUseViewer:=true", 
            f"camera_settings_path:={kinect.SETTINGS_FILE_PATH}", 
            f"/camera/image_raw:={kinect.IMAGE_RESIZED_TOPIC}"
        )
        
    else:
        # otherwise execute based on ROS_NODE
        os.system(f"chmod +x {orbslam.ROS_NODE}")

        if orbslam.ROS_NODE == "Mono":
            args = [
                f"/camera/image_raw:={kinect.IMAGE_RESIZED_TOPIC}",
            ]
        elif orbslam.ROS_NODE == "RGBD":
            args = [
                f"/camera/rgb/image_raw:={kinect.IMAGE_RESIZED_TOPIC}",
                f"/camera/depth_registered/image_raw:=/depth/image_raw",
            ]

        exec_cmd(
            "rosrun", 
            orbslam.VERSION, 
            orbslam.ROS_NODE, 
            orbslam.VOCAB_FILE_PATH,
            kinect.SETTINGS_FILE_PATH, 
            *args
        )


if __name__ == '__main__':
    yaml = YAML(typ="rt")
    yaml.version = (1, 1)
    yaml.explicit_start = True

    main()
