from munch import Munch


orbslam = Munch(
    # ["ORB_SLAM2", "ORB_SLAM2_CUDA", "ORB_SLAM3_BETA"]
    PATH = "~/ORB_SLAM2",
    # ["rgb", "rgbd", "rgbdl"]
    MODE = "rgb",
    IMG_SIZE = (768, 432), 
    #IMG_SIZE = (640, 576),
    NUM_FEATURES = 2000,
)

kinect = Munch(
    # ["NFOV_UNBINNED", "NFOV_2X2BINNED", "WFOV_UNBINNED", "WFOV_2X2BINNED"]
    DEPTH_MODE = "NFOV_UNBINNED",
    # ["720P", "1080P", "1440P", "1536P", "2160P", "3072P"]
    COLOR_RESOLUTION = "2160P",
    # [5, 15, 30]
    FPS = 30,
)
