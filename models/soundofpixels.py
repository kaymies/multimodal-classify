# -*- coding: utf-8 -*-
"""soundofpixels.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/16bXGKBjVGyFScwSKJ-vk1qP1tmVivd6i
"""

from google.colab import drive
drive.mount('/content/gdrive', force_remount=True)

# Commented out IPython magic to ensure Python compatibility.
!pip install torch>=1.2.0
!pip install torchaudio
# !pip install torchvision
# %matplotlib inline
# !pip install moviepy

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import Dataset
import torchaudio
import pandas as pd
import os
from google.colab import files
import pickle
import matplotlib.pyplot as plt
import math

device = torch.device("cuda" if torch.cuda.is_available() else "cpu") # see whether gpu can be used
print(device)

# load appropriate pickle file with spectrogram and labels
phys101_df = pd.read_pickle("/content/gdrive/MyDrive/phys101spec.pkl")

phys101_df_shuffled = phys101_df.sample(frac=1) # shuffle the data

# create dataset class
class SoundDataset(Dataset):
    def __init__(self, df):
        self.labels = np.asarray(df[[0, 1]]) # make labels (obj, mat)
        self.df = df
        self.specgrams = np.asarray(df['Sound']) # input


    def __getitem__(self, index):
        return F.pad(self.specgrams[index].log2(), (20,21,27,28)), self.labels[index, :]

    def __len__(self):
        return len(self.specgrams)

train_set = SoundDataset(phys101_df_shuffled[:533]) # ~80% of data for training
test_set = SoundDataset(phys101_df_shuffled[533:]) # ~20% of data for testing

print("Train set size: " + str(len(train_set)))
print("Test set size: " + str(len(test_set)))

train_loader = torch.utils.data.DataLoader(train_set, batch_size = 10, shuffle = True) # make data type for training data
test_loader = torch.utils.data.DataLoader(test_set, batch_size = 1, shuffle = True) # make data type for testing data

# these models are from https://github.com/IrisLi17/Sound_of_Pixels

def conv3x3(in_planes, out_planes, stride=1):
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)

class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out

class double_conv(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1):
        super(double_conv, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=kernel_size,
                      stride=stride, padding=padding),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=kernel_size,
                      stride=stride, padding=padding),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True))

    def forward(self, x):
        x = self.conv(x)
        return x


start_fm = 16

class UNet(nn.Module):
    def __init__(self):
        super(UNet, self).__init__()

        self.kchannels = 16
        self.double_conv1 = double_conv(1, start_fm, 3, 1, 1)
        self.maxpool1 = nn.MaxPool2d(kernel_size=2)
        # Convolution 2
        self.double_conv2 = double_conv(start_fm, start_fm * 2, 3, 1, 1)
        self.maxpool2 = nn.MaxPool2d(kernel_size=2)
        # Convolution 3
        self.double_conv3 = double_conv(start_fm * 2, start_fm * 4, 3, 1, 1)
        self.maxpool3 = nn.MaxPool2d(kernel_size=2)
        # Convolution 4
        self.double_conv4 = double_conv(start_fm * 4, start_fm * 8, 3, 1, 1)
        self.maxpool4 = nn.MaxPool2d(kernel_size=2)

        # Convolution 5
        self.double_conv5 = double_conv(start_fm * 8, start_fm * 16, 3, 1, 1)
        self.maxpool5 = nn.MaxPool2d(kernel_size=2)

        # Convolution 6
        self.double_conv6 = double_conv(start_fm * 16, start_fm * 32, 3, 1, 1)
        self.maxpool6 = nn.MaxPool2d(kernel_size=2)

        # Convolution 7
        self.double_conv7 = double_conv(start_fm * 32, start_fm * 64, 3, 1, 1)

        # Tranposed Convolution 6
        self.t_conv6 = nn.ConvTranspose2d(start_fm * 64, start_fm * 32, 2, 2)
        # Expanding Path Convolution 6
        self.ex_double_conv6 = double_conv(start_fm * 64, start_fm * 32, 3, 1, 1)

        # Transposed Convolution 5
        self.t_conv5 = nn.ConvTranspose2d(start_fm * 32, start_fm * 16, 2, 2)
        # Expanding Path Convolution 5
        self.ex_double_conv5 = double_conv(start_fm * 32, start_fm * 16, 3, 1, 1)

        # Transposed Convolution 4
        self.t_conv4 = nn.ConvTranspose2d(start_fm * 16, start_fm * 8, 2, 2)
        # Expanding Path Convolution 4
        self.ex_double_conv4 = double_conv(start_fm * 16, start_fm * 8, 3, 1, 1)

        # Transposed Convolution 3
        self.t_conv3 = nn.ConvTranspose2d(start_fm * 8, start_fm * 4, 2, 2)
        self.ex_double_conv3 = double_conv(start_fm * 8, start_fm * 4, 3, 1, 1)

        # Transposed Convolution 2
        self.t_conv2 = nn.ConvTranspose2d(start_fm * 4, start_fm * 2, 2, 2)
        self.ex_double_conv2 = double_conv(start_fm * 4, start_fm * 2, 3, 1, 1)

        # Transposed Convolution 1
        self.t_conv1 = nn.ConvTranspose2d(start_fm * 2, start_fm, 2, 2)
        self.ex_double_conv1 = double_conv(start_fm * 2, start_fm, 3, 1, 1)

        # One by One Conv
        self.one_by_one = nn.Conv2d(start_fm, self.kchannels, 1, 1, 0)
        # self.sum_of_one = nn.Conv2d(2, 1, 3, 1, 1)
        self.final_act = nn.Sigmoid()

        # self.finalconv = nn.Conv2d(1, self.kchannels, 3, 1, 1)

    def forward(self, inputs):
        # Contracting Path
        conv1 = self.double_conv1(inputs)
        maxpool1 = self.maxpool1(conv1)
        # print('mp1', maxpool1.size())

        conv2 = self.double_conv2(maxpool1)
        maxpool2 = self.maxpool2(conv2)
        # print(2, maxpool2)

        conv3 = self.double_conv3(maxpool2)
        maxpool3 = self.maxpool3(conv3)
        # print(3, maxpool3)

        conv4 = self.double_conv4(maxpool3)
        maxpool4 = self.maxpool4(conv4)

        conv5 = self.double_conv5(maxpool4)
        # print(5, conv5.size())
        maxpool5 = self.maxpool5(conv5)

        conv6 = self.double_conv6(maxpool5)
        maxpool6 = self.maxpool6(conv6)

        # Bottom
        conv7 = self.double_conv7(maxpool6)

        t_conv6 = self.t_conv6(conv7)
        cat6 = torch.cat([conv6, t_conv6], 1)
        ex_conv6 = self.ex_double_conv6(cat6)

        t_conv5 = self.t_conv5(ex_conv6)
        cat5 = torch.cat([conv5, t_conv5], 1)
        ex_conv5 = self.ex_double_conv5(cat5)

        # Expanding Path
        t_conv4 = self.t_conv4(ex_conv5)
        cat4 = torch.cat([conv4, t_conv4], 1)
        ex_conv4 = self.ex_double_conv4(cat4)
        

        t_conv3 = self.t_conv3(ex_conv4)
        cat3 = torch.cat([conv3, t_conv3], 1)
        ex_conv3 = self.ex_double_conv3(cat3)
        # print(5, ex_conv3)

        t_conv2 = self.t_conv2(ex_conv3)
        cat2 = torch.cat([conv2, t_conv2], 1)
        ex_conv2 = self.ex_double_conv2(cat2)
        # print(6, ex_conv2)

        t_conv1 = self.t_conv1(ex_conv2)
        cat1 = torch.cat([conv1, t_conv1], 1)
        ex_conv1 = self.ex_double_conv1(cat1)
        # print(7, ex_conv1)

        one_by_one = self.one_by_one(ex_conv1)
        # cat0 = torch.cat([one_by_one, inputs], 1)
        # one_by_one = self.sum_of_one(cat0)
        # print(1, one_by_one)

        act = self.final_act(one_by_one)
        # print(2, act)

        # k_channels = self.finalconv(one_by_one)
        # print(20, k_channels[:,0,:,:])
        # print(21, k_channels[:,1,:,:])
        # print(22, k_channels[:,2,:,:])

        return act


def UNet7():
    net = UNet()
    return net

# this is a wrapper model that we added to incorporate Sound of Pixels to classify
# object and material types by flattening the output of Sound of Pixels and passing it through
# a fully connected layer
class OurSound(nn.Module):
    def __init__(self, unet7):
        super(OurSound, self).__init__()
        self.unet7 = unet7
        # ([10, 16, 256, 1600])
        self.flatten = nn.Flatten()
        self.fc_obj = nn.Linear(16*256*1600, 12) # size is sofpixels_outchannel x signal_size, output is the number of classes
        self.fc_mat = nn.Linear(16*256*1600, 5)
    def forward(self, x):
        x = self.unet7(x) # output of SoundNet
        x = self.flatten(x) # flatten output of Sound of Pixels
        x_obj = self.fc_obj(x) # fully connected layer for object label
        x_mat = self.fc_mat(x) # fully connected layer for material label
        return F.log_softmax(x_obj, dim=1), F.log_softmax(x_mat, dim=1) # apply log_softmax to find most likely class (log_softmax works best with NLL Loss)

# define the training mode
# takes in the model that's used, the epoch number, and the optimizer 
def train(model, epoch, optimizer):
    model.train()
    loss_list = [] # initialize loss list so we can average loss for each epoch
    for batch_idx, (data, target) in enumerate(train_loader):
        data = torch.squeeze(data) # reformat the dimensions to match what the model expects
        data = torch.unsqueeze(data,1)
        optimizer.zero_grad()
        data = data.to(device)
        target = target.to(device).long() # pytorch wants target to be long() datatype
        output_obj, output_mat = model(data) # separate the output into material, object, scene
        loss_obj = F.nll_loss(output_obj, target[:,0]) # the loss functions expects a batchSizexn_class input
        loss_mat = F.nll_loss(output_mat, target[:,1])
        loss = loss_obj + loss_mat
        loss_list.append(loss)
        loss.backward() # back prop
        optimizer.step() # take a step with the chosen optimizer
        if batch_idx % log_interval == 0: #print training stats
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss))
    return sum(loss_list)/len(loss_list) # return average loss for this epoch for graphing purposes

# define test mode
# takes in model used, epoch number, and data
def test(model, epoch, test_loader):
    model.eval() # switch to test/evaluaion mode
    correct_obj = 0
    correct_mat = 0 # initialize correct classification count
    for data, target in test_loader:
        data = torch.unsqueeze(data,1) # reformat dimensions to the one that the model expects
        data = data.to(device)
        target = target.to(device).long() # pytorch wants target to be long() datatype
        output_obj, output_mat = model(data)
        pred_obj = torch.argmax(output_obj, dim=1)
        correct_obj += torch.sum(pred_obj == target[:,0])
        pred_mat = torch.argmax(output_mat, dim=1) # get the index of the max log-probability
        correct_mat += torch.sum(pred_mat == target[:,1]) # count as correct if the above index matches the target label
        print('\nTest set: Object Accuracy: {}/{} ({:.0f}%)\n Material Accuracy: {}/{} ({:.0f}%)'.format(
          correct_obj, len(test_loader.dataset),
          100. * correct_obj / len(test_loader.dataset),
          correct_mat, len(test_loader.dataset),
          100. * correct_mat / len(test_loader.dataset)))
    return correct_obj/len(test_loader.dataset), correct_mat/len(test_loader.dataset)

unet_model = UNet7()
oursound_model = OurSound(unet_model)
oursound_model.to(device)

# initializing the optimizer
optimizer = optim.Adam(oursound_model.parameters(), lr = 1)
# adaptive learning rate because we don't have pretrained weights for this model
scheduler = optim.lr_scheduler.StepLR(optimizer, step_size = 5, gamma = 0.6)

log_interval = 10 # printing the loss every log_interval steps
train_loss = [] # training loss for every epoch
accuracy = [] # test accuracy for every epoch
for epoch in range(100):
    train_loss.append(train(oursound_model, epoch, optimizer)) # train
    accuracy.append(test(oursound_model, epoch, test_loader)) # test
    scheduler.step()
torch.save(oursound_model.state_dict(), '/content/gdrive/My Drive/phys101_sop.pth')

# plot training loss
plt.plot(train_loss)
plt.xlabel('epoch')
plt.ylabel('training loss')

# plot validation accuracy
plt.plot(accuracy)
plt.xlabel('epoch')
plt.ylabel('validation accuracy')