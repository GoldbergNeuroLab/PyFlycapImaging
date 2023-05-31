from tkinter import *
from tkinter.ttk import *
from get_dir import select_dir
import glob
import os
import PyCapture2
import csv
import time
from pprint import pprint
import time
import subprocess
#buttons
def set_origin():
    #origin askdirectory
    global dir1, filelist

    dir1 = select_dir()
    orig_lbl.configure(text=dir1)
    filelist = glob.glob(dir1 + "/*.abf")
    os.chdir(dir1)
    print("Current working directory --",os.getcwd())


def gen_name():
    global new_file_name
    new_file_name = "KG"+experiment.get()+"_m"+mouse.get()+"_FOV"+fieldn.get()
    final_lbl.configure(text=new_file_name)
    print("Saving data as" + new_file_name)


def append_lab_entry():
    global lab_entry_file
    f=open(lab_entry_file, "a")
    f.write("\n"+current_file +"was saved as" + new_file_name)
    f.close()

def create_lab_entry():
    global dir1
    global lab_entry_file
    if experiment.get() == "KGXXX":
        print('name experiment first')
    else:
        lab_entry_file = dir1+"/"+experiment.get()+"_lab_entry.txt"
        f=open(lab_entry_file, "w+")
        f.close()
        os.startfile(dir1+"/"+experiment.get()+"_lab_entry.txt")

def print_build_info():
    lib_ver = PyCapture2.getLibraryVersion()
    print('PyCapture2 library version: %d %d %d %d' % (lib_ver[0], lib_ver[1], lib_ver[2], lib_ver[3]))
    print()

def print_camera_info(cam):
    cam_info = cam.getCameraInfo()
    print('\n*** CAMERA INFORMATION ***\n')
    print('Serial number - %d', cam_info.serialNumber)
    print('Camera model - %s', cam_info.modelName)
    print('Camera vendor - %s', cam_info.vendorName)
    print('Sensor - %s', cam_info.sensorInfo)
    print('Resolution - %s', cam_info.sensorResolution)
    print('Firmware version - %s', cam_info.firmwareVersion)
    print('Firmware build time - %s', cam_info.firmwareBuildTime)
    print()

def print_format7_capabilities(fmt7_info):
    print('Max image pixels: ({}, {})'.format(fmt7_info.maxWidth, fmt7_info.maxHeight))
    print('Image unit size: ({}, {})'.format(fmt7_info.imageHStepSize, fmt7_info.imageVStepSize))
    print('Offset unit size: ({}, {})'.format(fmt7_info.offsetHStepSize, fmt7_info.offsetVStepSize))
    print('Pixel format bitfield: 0x{}'.format(fmt7_info.pixelFormatBitField))
    print()

def enable_embedded_timestamp(cam, enable_timestamp):
    embedded_info = cam.getEmbeddedImageInfo()
    if embedded_info.available.timestamp:
        cam.setEmbeddedImageInfo(timestamp = enable_timestamp)
        if enable_timestamp:
            print('\nTimeStamp is enabled.\n')
        else:
            print('\nTimeStamp is disabled.\n')

def enable_embedded_GPIO(cam, enable_GPIOPinState):
    embedded_info = cam.getEmbeddedImageInfo()
    if embedded_info.available.GPIOPinState:
        cam.setEmbeddedImageInfo(GPIOPinState = enable_GPIOPinState)
        if enable_GPIOPinState:
            print('\nGPIO recording is enabled.\n')
        else:
            print('\nTimeStamp is disabled.\n')

def save_video_helper(cam, file_format, filename, framerate):

    num_images = int(num_frames.get())
    t=time.strftime("%m%d%Y_%H%M%S")

    vid_filename = "{}_{}.avi".format(filename,t)
    video = PyCapture2.FlyCapture2Video()
    prev_ts = None


    with open("{}_{}.csv".format(filename,t),"w") as csvfile:
        filewriter = csv.writer(csvfile, delimiter = ',', lineterminator='\n', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        filewriter.writerow(['Frame','Cycle Second','Cycle Count','Frame length(cycles)'])
        for i in range(num_images):

            log_every_n = 1000
            if (i == 0):
                if file_format == 'AVI':
                    video.AVIOpen(vid_filename.encode('utf-8'), framerate)
                elif file_format == 'MJPG':
                    video.MJPGOpen(vid_filename.encode('utf-8'), framerate, 75)
                #elif file_format == 'H264':
                    #video.H264Open(filename, framerate, image.getCols(), image.getRows(), 1000000)
                else:
                    print('Specified format is not available.')
                    return
                print('Starting capture...waiting for trigger')

            try:
                image = cam.retrieveBuffer()


            except PyCapture2.Fc2error as fc2Err:
                print('Error retrieving buffer : %s' % fc2Err)
                continue

        #print('Grabbed image {}'.format(i))

            ts = image.getTimeStamp()

            if i == 0:
                t0=time.perf_counter()
                print('Triggered!')
                adj_set()
                t1=time.perf_counter()
                total=(t1-t0)
                timestamp_prev=round(total*1000,2)
                filewriter.writerow([i+1, ts.cycleSeconds, ts.cycleCount, timestamp_prev])
            else:
                timestamp_ms = ((ts.cycleSeconds - prev_ts.cycleSeconds) * 8000 + (ts.cycleCount - prev_ts.cycleCount))/8
                if timestamp_ms<0:
                    timestamp_ms = ((ts.cycleSeconds - prev_ts.cycleSeconds+128) * 8000 + (ts.cycleCount - prev_ts.cycleCount))/8

                timestamp_prev += timestamp_ms
                filewriter.writerow([i+1, ts.cycleSeconds, ts.cycleCount, timestamp_prev])

            prev_ts = ts

            video.append(image)
            if (i % log_every_n) == 0:
                print('Acquired {} frames'.format(i))

        print('Appended {} images to {} file: {}...'.format(num_images, file_format, filename))
        video.close()
    csvfile.close()

def initialize_camera():
    global cam
    global offy
    global offx
     # Print PyCapture2 Library Information
    print_build_info()

    # Ensure sufficient cameras are found
    bus = PyCapture2.BusManager()
    num_cams = bus.getNumOfCameras()
    print('Number of cameras detected: %d' % num_cams)
    if not num_cams:
        print('Insufficient number of cameras. Exiting...')
        exit()

    # Select camera on 0th index
    cam = PyCapture2.Camera()
    cam.connect(bus.getCameraFromIndex(0))

    # Print camera details
    print_camera_info(cam)
    fmt7_info, supported = cam.getFormat7Info(0)
    print_format7_capabilities(fmt7_info)

    # Check whether pixel format mono8 is supported
    if PyCapture2.PIXEL_FORMAT.MONO8 & fmt7_info.pixelFormatBitField == 0:
        print('Pixel format is not supported\n')
        exit()

    # Configure camera format7 settings
    f7mode=0
    offx = 768
    offy = 768
    sizex = 512
    sizey = 440
    fmt7_img_set = PyCapture2.Format7ImageSettings(f7mode, offx, offy, sizex, sizey, PyCapture2.PIXEL_FORMAT.MONO8)
    fmt7_pkt_inf, isValid = cam.validateFormat7Settings(fmt7_img_set)
    if not isValid:
        print('Format7 settings are not valid!')
        exit()
    cam.setFormat7ConfigurationPacket(fmt7_pkt_inf.recommendedBytesPerPacket, fmt7_img_set)
    print("Format7 settings:mode{}, offset {} {}, Size {} {}".format(f7mode,offx,offy,sizex,sizey))

    # Enable camera embedded timestamp
    enable_embedded_timestamp(cam, True)
    enable_embedded_GPIO(cam, True)
    adj_set()
    print_settings()

def estimate_framerate():
    global cam
    global new_file_name
    global framerate
    cam.setProperty(type = PyCapture2.PROPERTY_TYPE.SHUTTER, absValue = float(shutter_val.get()), autoManualMode = False)
    #cam.setTriggerMode(onOff = False)
    cam.setTriggerMode(onOff = False)
    time.sleep(1)
    cam.setTriggerMode(onOff = True, mode = 15, parameter = 0, polarity = 1)
    time.sleep(1)
    cam.startCapture()
    print('Starting Framerate estimate')

    time.sleep(1)

    cam.fireSoftwareTrigger()

    t0=time.perf_counter()
    num_images = 500

    prev_ts = None
    timestamp_prev = float(0)
    with open("estimate_FR.csv","w") as csvfile:
        filewriter = csv.writer(csvfile, delimiter = ',', lineterminator='\n', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        filewriter.writerow(['Frame','Cycle Second','Cycle Count','Frame length(cycles)'])

        for i in range(num_images):
            try:
                image = cam.retrieveBuffer()
            except PyCapture2.Fc2error as fc2Err:
                print('Error retrieving buffer : %s' % fc2Err)
                continue

        #print('Grabbed image {}'.format(i))

            ts = image.getTimeStamp()

            if i == 0:

                adj_set()
                t1=time.perf_counter()
                total=(t1-t0)
                timestamp_prev=round(total*1000,2)
                filewriter.writerow([i+1, ts.cycleSeconds, ts.cycleCount, timestamp_prev])

            else:
                timestamp_ms = ((ts.cycleSeconds - prev_ts.cycleSeconds) * 8000 + (ts.cycleCount - prev_ts.cycleCount))/8
                if timestamp_ms<0:
                    timestamp_ms = ((ts.cycleSeconds - prev_ts.cycleSeconds+128) * 8000 + (ts.cycleCount - prev_ts.cycleCount))/8

                timestamp_prev += timestamp_ms
                filewriter.writerow([i+1, ts.cycleSeconds, ts.cycleCount, timestamp_prev])

            prev_ts = ts

    FR_estimate=float(num_images)/(timestamp_prev/1000)
    print(FR_estimate)
    framerate=FR_estimate
    fr_lbl.configure(text=str(int(FR_estimate)))
    cam.stopCapture()
    cam.disconnect()
    initialize_camera()


def start_recording():
    global cam
    global new_file_name
    subprocess.call([r'C:\Users\User\Desktop\Pycap_imaging\kill_flycap2_window.bat'])
    framerate=float(FR_val.get())
    file_format = 'MJPG'
    filename = '{}_{}'.format(new_file_name,file_format)
    print(framerate)
    print(filename)
    #cam.setProperty(type = PyCapture2.PROPERTY_TYPE.SHUTTER, absValue = float(shutter_val.get()))
    #cam.setTriggerMode(onOff = False)
    cam.setTriggerMode(onOff = False)
    time.sleep(2)
    cam.setTriggerMode(onOff = True, mode = 15, parameter = 0)
    time.sleep(2)

    print('Using frame rate of {} Hz'.format(framerate))
    cam.startCapture()


    time.sleep(2)

    #cam.fireSoftwareTrigger()


    save_video_helper(cam, file_format, filename, framerate)

    print('Stopping capture...')
    cam.stopCapture()
    cam.disconnect()

    print('Done! Re-initialize camera to record another file...\n')

def trigger_button():
    global cam
    cam.fireSoftwareTrigger()

def cam_up():
    global offy
    offy-=10
    move_camera()
def cam_down():
    global offy
    offy+=10
    move_camera()
def cam_left():
    global offx
    offx-=10
    move_camera()

def cam_right():
    global offx
    offx+=10
    move_camera()

def move_camera():
    global offx
    global offy
    f7mode=0
    sizex = 512
    sizey = 440

    fmt7_img_set = PyCapture2.Format7ImageSettings(f7mode, offx, offy, sizex, sizey, PyCapture2.PIXEL_FORMAT.MONO8)
    fmt7_pkt_inf, isValid = cam.validateFormat7Settings(fmt7_img_set)
    if not isValid:
        print('Format7 settings are not valid!')
        exit()
    cam.setFormat7ConfigurationPacket(fmt7_pkt_inf.recommendedBytesPerPacket, fmt7_img_set)
    print("Format7 settings:mode{}, offset {} {}, Size {} {}".format(f7mode,offx,offy,sizex,sizey))


def adj_set():
    global cam
    cam.setTriggerMode(onOff = False)
    cam.setProperty(type = PyCapture2.PROPERTY_TYPE.SHUTTER, absValue = float(shutter_val.get()), autoManualMode = False)
    #print("Shutter value")
    #pprint(vars(cam.getProperty(PyCapture2.PROPERTY_TYPE.SHUTTER)))
    cam.setProperty(type = PyCapture2.PROPERTY_TYPE.FRAME_RATE, absControl = True, absValue = float(FR_val.get()), autoManualMode = False, onOff = True)
    cam.setProperty(type = PyCapture2.PROPERTY_TYPE.GAIN, absControl = True, absValue = float(gain_val.get()), autoManualMode = False)
    cam.setProperty(type = PyCapture2.PROPERTY_TYPE.GAMMA, absControl = True, absValue = float(gamma_val.get()), onOff = True)
    cam.setProperty(type = PyCapture2.PROPERTY_TYPE.SHARPNESS, absControl = False, valueA = float(sharp_val.get()))
    cam.setProperty(type = PyCapture2.PROPERTY_TYPE.AUTO_EXPOSURE, autoManualMode = False, onOff = False)
    cam.setProperty(type = PyCapture2.PROPERTY_TYPE.BRIGHTNESS, absValue = float(brightness_val.get()))

def print_settings():
    global cam
    print("SHUTTER")
    pprint(vars(cam.getProperty(PyCapture2.PROPERTY_TYPE.SHUTTER)))
    print("FRAMERATE")
    pprint(vars(cam.getProperty(PyCapture2.PROPERTY_TYPE.FRAME_RATE)))
    print("GAIN")
    pprint(vars(cam.getProperty(PyCapture2.PROPERTY_TYPE.GAIN)))
    print("GAMMA")
    pprint(vars(cam.getProperty(PyCapture2.PROPERTY_TYPE.GAMMA)))
    print("SHARPNESS")
    pprint(vars(cam.getProperty(PyCapture2.PROPERTY_TYPE.SHARPNESS)))
    print("EXPOSURE")
    pprint(vars(cam.getProperty(PyCapture2.PROPERTY_TYPE.AUTO_EXPOSURE)))
    print("BRIGHTNESS")
    pprint(vars(cam.getProperty(PyCapture2.PROPERTY_TYPE.BRIGHTNESS)))
def restart_camera_stream():
    os.startfile(r'C:\Program Files\Point Grey Research\FlyCapture2\bin64\FlyCapture2SimpleGUI_MFC.exe')
#build gui

window = Tk()

window.title("Record Avi files with Pyflycap2")
window.geometry('700x300')

orig_lbl = Label(window, text="Directory")
orig_lbl.grid(column=1, row=0)
orig_btn = Button(window, text="Set Directory",command=set_origin)
orig_btn.grid(column=0, row=0)

experiment = Entry(window,width=15, text = "XXX")
experiment.grid(column=1, row=3)
mouse = Entry(window,width=15, text = "XXXX")
mouse.grid(column=1, row=4)

fieldn = Combobox(window,width=15)
fieldn.grid(column=1, row=5)
fieldn['values']= (1, 2, 3, 4, 5, 6, 7, 8, 9)
fieldn.current(0)

lbl1 = Label(window, text="experiment number")
lbl1.grid(column=0, row=3)
lbl2 = Label(window, text="mouse number")
lbl2.grid(column=0, row=4)
lbl3 = Label(window, text="Field of view")
lbl3.grid(column=0, row=5)

name_file = Button(window, text="Generate name",command=gen_name)
name_file.grid(column=0, row=6)
restart_camera = Button(window, text="Restart Camera Stream", command=restart_camera_stream)
restart_camera.grid(column=0,row=7)
#find_btn =Button(window, text='Autofind',command=find_cell_number)
#find_btn.grid(column=3, row=5)
#outofind function not working


final_lbl = Label(window, text="KGXXXcellmXXXXFOVX")
final_lbl.grid(column=1, row=6)


#lab_entry_btn =Button(window, text='Create Lab entry',command=create_lab_entry)
#lab_entry_btn.grid(column=0, row=8)

init_btn =Button(window, text='Re-Initialize Camera',command=initialize_camera)
init_btn.grid(column=5, row=0)

rec_btn =Button(window, text='Start Recording',command=start_recording)
rec_btn.grid(column=5, row=1)
num_frames = Entry(window,width=15)
num_frames.grid(column=5, row=3)
num_frames.insert(0,10000)
lbl4 = Label(window, text="Number of Images")
lbl4.grid(column=5, row=2)

shutter_val= Entry(window,width=15)
shutter_val.grid(column=6, row=1)
shutter_val.insert(0,1.5)
lbl4 = Label(window, text="SHUTTER (ms)")
lbl4.grid(column=6, row=0)
FR_val= Entry(window,width=15)
FR_val.grid(column=6, row=3)
FR_val.insert(0,100)
lbl5 = Label(window, text="FRAMERATE (Hz)")
lbl5.grid(column=6, row=2)

gain_val=Entry(window,width=15)
gain_val.grid(column=6, row=5)
gain_val.insert(0,1)
lblgain_val = Label(window, text="GAIN")
lblgain_val.grid(column=6, row=4)

gamma_val=Entry(window,width=15)
gamma_val.grid(column=7, row=1)
gamma_val.insert(0,1)
lblgamma_val = Label(window, text="GAMMA")
lblgamma_val.grid(column=7, row=0)

sharp_val=Entry(window,width=15)
sharp_val.grid(column=7, row=3)
sharp_val.insert(0,4095)
lblsharp_val = Label(window, text="SHARPNESS")
lblsharp_val.grid(column=7, row=2)

brightness_val=Entry(window,width=15)
brightness_val.grid(column=7, row=5)
brightness_val.insert(0,1)
lblbrightness_val = Label(window, text="BRIGHTNESS")
lblbrightness_val.grid(column=7, row=4)

cup_btn =Button(window, text='Camera Up',command=cam_up)
cup_btn.grid(column=8, row=0)
cdn_btn =Button(window, text='Camera Down',command=cam_down)
cdn_btn.grid(column=8, row=1)
clf_btn =Button(window, text='Camera Left',command=cam_left)
clf_btn.grid(column=8, row=2)
crt_btn =Button(window, text='Camera Right',command=cam_right)
crt_btn.grid(column=8, row=3)

#FR_btn =Button(window, text='Estimate Framerate',command=estimate_framerate)
#FR_btn.grid(column=5, row=6)
#fr_lbl = Label(window, text="100")
#fr_lbl.grid(column=5, row=7)
#firetrigger = Button(window, text='Fire internal trigger',command=trigger_button)
#firetrigger.grid(column=5, row=8)

settings_adjust = Button(window, text='Set/Get settings',command=lambda:[adj_set(), print_settings()])
settings_adjust.grid(column=5, row=4)
window.mainloop()

#destination askdirectory
#dir2 = select_dir()
