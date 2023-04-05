from rosbag import Bag
with Bag('bahen_fast_imu2_vins.bag', 'w') as Y:
    for topic, msg, t in Bag('bahen_fast_imu2.bag'):
        Y.write('/cam0/image_raw' if topic == '/tello/image_raw' else topic, msg, t)