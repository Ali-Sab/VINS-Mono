from rosbag import Bag
with Bag('bahen_legal_new.bag', 'w') as Y:
    for topic, msg, t in Bag('bahen_legal.bag'):
        Y.write('/cam0/image_raw' if topic == '/tello/image_raw' else topic, msg, t)