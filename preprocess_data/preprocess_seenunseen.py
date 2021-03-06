# -*- coding: utf-8 -*-
"""preprocess_seenunseen.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ZocoiaoWmyFiecodRq-2DUi1HdhVnnuo
"""

from google.colab import drive
drive.mount('/content/gdrive', force_remount=False)

# Commented out IPython magic to ensure Python compatibility.
!pip install torch>=1.2.0
!pip install torchaudio
# %matplotlib inline

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms, io
from torch.utils.data import Dataset
import torchaudio
import pandas as pd
import os
from google.colab import files
import pickle
import matplotlib.pyplot as plt
import math
from PIL import Image
from google.colab.patches import cv2_imshow

import sys
import argparse

import cv2
print(cv2.__version__)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu") # see whether gpu can be used
print(device)

#getting the frames of images
def extractImages(pathIn, pathOut): 
    vidcap = cv2.VideoCapture(pathIn)
    frames_skipped = 3 # our videos are 30 fps, so want to use 5 (6 fps) for the first 4 images
    success,image = vidcap.read()
    count = 0
    i = 0
    success = True
    while success and count < 4: # for the multiframe case we are extracting 4 images, otherwise we would extract only 1 image
      success,image = vidcap.read()
      if i > frames_skipped - 1:
        # print ('Read a new frame: ', success)
        if success:
          cv2.imwrite( pathOut + "/frame%d.jpg" % count, image)     # save frame as JPEG file
          count += 1
          i = 0
          continue
      i += 1
    return count

aud_list_seen = [] #initialize a list for waveforms to be added
frames_seendf = pd.DataFrame(columns = ['frame0', 'frame1', 'frame2', 'frame3']) #initialize a frames dataframe
# iterate through the folder structure to convert .mp4 files to .wav, then convert to waveform and also extract frames
for obj in range(12): 
    for mat in range(5): 
        for root, dirs, files in os.walk("/content/gdrive/My Drive/fall_seen/{}/{}/".format(obj,mat), topdown=False): # change directory as necessary
            for name in files: 
                full_file_name = os.path.join(root, name) # full name of the file including root
                if full_file_name.endswith("Camera_1.mp4"): # we only care about this file in each folder
                    clip = mp.VideoFileClip(r"{}".format(full_file_name))
                    clip.audio.write_audiofile(r"{}/Camera_1.wav".format(root)) # convert .mp4 to .wav
                    waveform, sample_rate = torchaudio.load("{}/Camera_1.wav".format(root)) # convert .wav to waveform
                    aud_list_seen.append(waveform[0])
                    count = extractImages(full_file_name, root)
                    frames = []
                    # get frames
                    for i in range(4): 
                      if i < count:
                        frames.append(os.path.join(root, "frame{}.jpg".format(i)))
                      else:
                        frames.append(np.nan)
                    # print(frames)
                    frame_series = pd.Series(frames, index = frames_seendf.columns)
                    frames_seendf = frames_seendf.append(frame_series, ignore_index=True)# add frames to initialized dataframe

# The below code is equivalent to the above example for seen data, but following the same procedure for unseen data, all comments apply as above for unseen data

aud_list_unseen = []
frames_unseendf = pd.DataFrame(columns = ['frame0', 'frame1', 'frame2', 'frame3'])
for obj in range(12):
    for mat in range(5):
        for root, dirs, files in os.walk("/content/gdrive/My Drive/fall_unseen/{}/{}/".format(obj,mat), topdown=False):
            for name in files:
                full_file_name = os.path.join(root, name)
                # print(full_file_name)
                if full_file_name.endswith("Camera_1.mp4"):
                    # clip = mp.VideoFileClip(r"{}".format(full_file_name))
                    # clip.audio.write_audiofile(r"{}/Camera_1.wav".format(root))
                    waveform, sample_rate = torchaudio.load("{}/Camera_1.wav".format(root))
                    aud_list_unseen.append(waveform[0])
                    count = extractImages(full_file_name, root)
                    frames = []
                    for i in range(4):
                      if i < count:
                        frames.append(os.path.join(root, "frame{}.jpg".format(i)))
                      else:
                        frames.append(np.nan)
                    print(frames)
                    frame_series = pd.Series(frames, index = frames_unseendf.columns)
                    frames_unseendf = frames_unseendf.append(frame_series, ignore_index=True)

# since the videos vary in length, we pad the waveforms to match the longest video
aud_list_seen_padded = [] # initialization for a padded list of the waveforms
for i in range(len(aud_list_seen)):
    diff = 311787 - len(aud_list_seen[i]) 
    print(aud_list_seen[i])
    pad = torch.nn.functional.pad(aud_list_seen[i], (math.floor(diff/2),math.ceil(diff/2)), mode='constant', value=0) #creates padding of the correct length
    aud_list_seen_padded.append(pad) # adds padding to aud_list_seen to create aud_list_seen_padded

# works analog to above but for unseen data
aud_list_unseen_padded = [] 
for i in range(len(aud_list_unseen)):
    diff = 311787 - len(aud_list_unseen[i]) # 311787 is the length of the longest file; compute the difference between current file and longest file
    print(aud_list_unseen[i])
    pad = torch.nn.functional.pad(aud_list_unseen[i], (math.floor(diff/2),math.ceil(diff/2)), mode='constant', value=0)# pad with appropriate number of zeros
    aud_list_unseen_padded.append(pad)

phys101_seendf = pd.read_csv('/content/gdrive/My Drive/Phys101_seen.csv', sep=',', header=None) # read off the labels from csv
phys101_seendf.fillna(0) # changes any NaN value to 0
phys101_seendf['Sound'] = aud_list_seen_padded # add a 'Sound' column with waveforms to dataframe
# phys101_seendf.to_pickle("/content/gdrive/My Drive/phys101_seen.pkl") # save to pickle for future use
phys101_seenmerged_df = pd.concat([phys101_seendf, frames_seendf], axis=1, sort=False) # concatenates the labels with the frames from the videos
phys101_seenmerged_df.to_pickle("/content/gdrive/My Drive/phys101_res_mf_seenmerged.pkl") # save to pickle for future use

# works analog to above but for the unseen data
phys101_unseendf = pd.read_csv('/content/gdrive/My Drive/Phys101_unseen.csv', sep=',', header=None)
phys101_unseendf.fillna(0)
phys101_unseendf['Sound'] = aud_list_unseen_padded # add a 'Sound' column with waveforms to dataframe
# phys101_unseendf.to_pickle("/content/gdrive/My Drive/phys101_unseen.pkl") # save to pickle for future use
phys101_unseenmerged_df = pd.concat([phys101_unseendf, frames_unseendf], axis=1, sort=False)
phys101_unseenmerged_df.to_pickle("/content/gdrive/My Drive/phys101_res_mf_unseenmerged.pkl") # save to pickle for future use

phys101_seendf_shuffled = phys101_seenmerged_df.sample(frac=1) # shuffle the data 
phys101_unseendf_shuffled = phys101_unseenmerged_df.sample(frac=1)
# print(type(phys101_merged_df[1][3]))

# visualize one image
imgseen = cv2.imread(np.asarray(phys101_seendf_shuffled['frame0'])[0])
cv2_imshow(imgseen)

imgunseen = cv2.imread(np.asarray(phys101_unseendf_shuffled['frame0'])[0])
cv2_imshow(imgunseen)