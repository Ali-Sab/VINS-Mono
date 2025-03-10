import rospy

from std_msgs.msg import Empty, UInt8, Bool
from std_msgs.msg import UInt8MultiArray
from std_msgs.msg import String
from sensor_msgs.msg import Image, _Imu
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from dynamic_reconfigure.server import Server
#from h264_image_transport.msg import H264Packet

from cv_bridge import CvBridge, CvBridgeError

#import av
import math
import numpy as np
import time

from djitellopy import Tello
from threading import Thread, Event
import time, cv2
import signal
import logging
import readchar

#tello = Tello()
#Step 1 connect to Tello
#tello.connect()

#Step 2 publish images to node /camera/image_raw
#To do 

tello = Tello(skipAddressCheck=True)
tello.LOGGER.setLevel(logging.INFO)
tello.connect()
keepRecording = Event()
keepRecording.set()
keepAlive = Event()
keepAlive.set()

tello.streamon()
frame_read = tello.get_frame_read()
bridge = CvBridge()

print("Tello Battery Level = {}%".format(tello.get_battery()))

#Step 3 subscribe to commands published by mono_sub.cc
#code borrowed from : https://www.geeksforgeeks.org/ros-subscribers-using-python/ 

class command_subscriber:
  
    def __init__(self):
        # initialize the subscriber node
        # here we deal with messages of type String which are commands coming from subscriber.
        self.image_sub = rospy.Subscriber("tello/command", 
                                          String, self.process_command)
        print("Initializing the command subscriber!")
  
    def process_command(self, String):
        
        # now print what mono sub has sent.
        #rospy.get_caller_id must return command_subscriber....
        #http://wiki.ros.org/rospy_tutorials/Tutorials/WritingPublisherSubscriber
        rospy.loginfo(rospy.get_caller_id() + "The commands in coming are %s",
                      String)
        
        # To handle commands
        # check if tello is busy (as a backup, in case for some reason ros_mono_sub/pub doesn't realize it is busy)
        # Use switch case to determine which command it is
        # Call the revelant DJITelloPy API function to have the command work
        # Set flag to indicate tello is busy
        # 
  
  
def main():
    # create a  command subscriber instance
    sub = command_subscriber()
      
    print('Currently in the main function...')
    # pub = rospy.Publisher("test/raw", String, queue_size=10)
    pub_img = rospy.Publisher("/tello/image_raw", Image, queue_size=10)
    pub_imu = rospy.Publisher("/imu0", _Imu.Imu, queue_size=10)
      
    # initializing the subscriber node
    rospy.init_node('command_subscriber', anonymous=True)

    def videoRecorder():
        # create a VideoWrite object, recoring to ./video.avi
        height, width, _ = frame_read.frame.shape
        fps = 1.0/30
        seq = 1

        print("Start recording")
        # video = cv2.VideoWriter('video.avi', cv2.VideoWriter_fourcc(*'MJPG'), 30, (width, height))

        while keepRecording.is_set():
            img_msg = bridge.cv2_to_imgmsg(frame_read.frame, encoding='bgr8')
            img_msg.header.seq = seq
            img_msg.header.stamp.set(math.floor(time.time()), time.time_ns() % 1000000000)
            # 1000000000 is to only the decimals for nano seconds
            img_msg.header.frame_id = "cam0"
            pub_img.publish(img_msg)
            seq += 1
            # video.write(frame_read.frame)
            time.sleep(fps)

        print("Stop recording")

        # video.release()

    def imuReceiver():
        seq = 10001
        fps = 1.0/180
        lastYaw = 0
        lastPitch = 0
        lastRoll = 0
        Rx = 0
        Ry = 0
        Rz = 0
        lastVX = 0
        lastVY = 0
        lastVZ = 0
        Ax = 0
        Ay = 0
        Az = 0
        
        wait = 0

        while keepRecording.is_set():
            imu_msg = _Imu.Imu()

            if wait > 20 or tello.get_roll() != lastRoll or tello.get_pitch() != lastPitch or tello.get_yaw() != lastYaw or tello.get_speed_x() != lastVX or tello.get_speed_y() != lastVY or tello.get_speed_z() != lastVZ:
                Rx = (tello.get_roll() - lastRoll)*math.pi/18 # rad = degree*pi/180 (18 because 10hz values)
                Ry = (tello.get_pitch() - lastPitch)*math.
                pi/18
                Rz = (tello.get_yaw() - lastYaw)*math.pi/18
                lastRoll = tello.get_roll()
                lastYaw = tello.get_yaw()
                lastPitch = tello.get_pitch()

                # Ax = (tello.get_speed_x() - lastVX)/10
                # Ay = (tello.get_speed_y() - lastVY)/10
                # Az = (tello.get_speed_z() - lastVZ)/10
                # lastVX = tello.get_speed_x()
                # lastVY = tello.get_speed_y()
                # lastVZ = tello.get_speed_z()
                print("Ax: {}, Ay: {}, Az: {}, Vx: {}, Vy: {}, Vz: {}, Rx: {}, Ry: {}, Rz: {}".format(Ax, Ay, Az, tello.get_speed_x(), tello.get_speed_y(), tello.get_speed_z(), Rx, Ry, Rz))
                wait = 0

            wait += 1

            imu_msg.header.seq = seq
            imu_msg.header.stamp.set(math.floor(time.time()), time.time_ns() % 1000000000)
            imu_msg.header.frame_id = "imu4"
            imu_msg.orientation.z = 1
            imu_msg.orientation_covariance[0] = 99999.9
            imu_msg.orientation_covariance[4] = 99999.9
            imu_msg.orientation_covariance[8] = 99999.9

            imu_msg.linear_acceleration.x = tello.get_acceleration_x()/100
            imu_msg.linear_acceleration.y = tello.get_acceleration_y()/100
            imu_msg.linear_acceleration.z = tello.get_acceleration_z()/100
            # imu_msg.linear_acceleration.x = Ax
            # imu_msg.linear_acceleration.y = Ay
            # imu_msg.linear_acceleration.z = Az
            imu_msg.angular_velocity.x = Rx
            imu_msg.angular_velocity.y = Ry
            imu_msg.angular_velocity.z = Rz

            pub_imu.publish(imu_msg)
            seq += 1
            time.sleep(fps)


    time.sleep(2)

    imgRecorder = Thread(target=videoRecorder)
    imuRecorder = Thread(target=imuReceiver)

    imgRecorder.start()
    imuRecorder.start()

    def exitCatcher():
        while keepAlive.is_set():
            try:
                tello.send_keepalive()
            except Exception:
                print("Keeping alive")
            time.sleep(10)


    def exit_handler(signum, frame):
        msg = "Stopping drone. Drone will now hover.\n W = forward\nS = backwards\nA = left\nD = right\nQ = turn left\nE = turn right\nZ = ascend\nX = descend\nENTER = land\nSPACEBAR = hover\nPlease shutdown manually by pressing the button on the drone or press ENTER to land the drone."
        print(msg, flush=True)
        keepingAlive = Thread(target=exitCatcher)
        keepingAlive.start()

        try:
            speed = 50
            while True:
                inputChar = readchar.readchar()
                updownV = 0
                leftRightV = 0
                forwardBackwardV = 0
                yawV = 0
                if inputChar == 'w':
                    forwardBackwardV = speed
                elif inputChar == 's':
                    forwardBackwardV = -speed
                elif inputChar == 'a':
                    leftRightV = -speed
                elif inputChar == 'd':
                    leftRightV = speed
                elif inputChar == 'z':
                    updownV = 70
                elif inputChar == 'x':
                    updownV = -70
                elif inputChar == 'q':
                    yawV = -30
                elif inputChar == 'e':
                    yawV = 30
                elif inputChar == 'o':
                    speed += 10
                elif inputChar == 'p':
                    speed -= 10
                elif inputChar == readchar.key.ENTER:
                    tello.land()
                    keepAlive.clear()
                    keepRecording.clear()
                    imgRecorder.join()
                    imuRecorder.join()
                    exit(1)
                    rospy.spin()
                elif inputChar == readchar.key.ESC:          # THIS IS A DANGEROUS COMMAND. ONLY USE WHEN DRONE HAS LANDED ALREADY FOR WHATEVER REASON (auto landing, crash landing, flew down too much, etc.) TO EXIT THE PROGRAM.
                    keepAlive.clear()
                    keepRecording.clear()
                    imgRecorder.join()
                    imuRecorder.join()
                    exit(1)
                    rospy.spin()
                else:
                    print("Tello Battery Level = {}%".format(tello.get_battery()))
                # PRESS SPACEBAR TO HOVER
                tello.send_rc_control(leftRightV, forwardBackwardV, updownV, yawV)
        except KeyboardInterrupt:
            print("Exiting keepAlive")
            keepAlive.clear()
            keepRecording.clear()
            imgRecorder.join()
            imuRecorder.join()
            print("Killing program")
            exit(1)
            rospy.spin()

    signal.signal(signal.SIGINT, exit_handler)



    tello.takeoff()

    time.sleep(3)

    # You can add forced commands here if you want it to run by script (though it may fail in bad lighting or other issues)
    # Most reliable way to control drone is with `send_rc` commands rather then `move` commands

    # cv2.imwrite("picture2.png", frame_read.frame)

    # tello.move("up", 80)
    # cv2.imwrite("picture3.png", frame_read.frame)

    # tello.move("forward", 40)
    # cv2.imwrite("picture4.png", frame_read.frame)

    # tello.move("left", 20)
    # cv2.imwrite("picture5.png", frame_read.frame)

    # tello.move("right", 40)
    # cv2.imwrite("picture6.png", frame_read.frame)

    # tello.move("left", 20)
    # cv2.imwrite("picture7.png", frame_read.frame)

    # tello.move("up", 20)
    # cv2.imwrite("picture8.png", frame_read.frame)

    # tello.move("back", 30)
    # cv2.imwrite("picture9.png", frame_read.frame)

    # print("Landing drone!")
    # tello.land()


    while imgRecorder.is_alive():
        time.sleep(0.2)

        
    if (keepRecording.is_set() == True):
        keepRecording.clear()

    imgRecorder.join()
    imuRecorder.join()


    rospy.spin()
  
if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
