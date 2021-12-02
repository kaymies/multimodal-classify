# av-multimodal

Data
====
Please load the data from [google drive](https://drive.google.com/drive/folders/1ECMDyuiv3m-JgnZLP_tSUzFKUvP5dEk6?usp=sharing).
In the folder, you will find:
<ul>
<li>A folder "fall" containing videos from the [Physics 101 Dataset](http://phys101.csail.mit.edu).  The folder structure is as follows: object > surface material > trial. The key to what each value of the folder corresponds to is included in "key" above.</li>
<li>Folders "fall_seen" and "fall_unseen" contain training and testing sets respectively. This folder structure enables you to test the model on objects that the model has not yet seen during training.</li>
<li>In the "preprocess_data" folder, there is a "labels_csv" folder which contains the labels (object type and surface material type) to the "fall", "fall_seen", and "fall_unseen" datasets.</li>
<li>Similarly in the "preprocess_data" folder, there is a "pickle_files" folder that contains datasets that we have already created and are ready to be loaded and trained with.</li>
</ul>
Each model will require a different format of the dataset. For example, if you would like to run the SoundNet model, you should load the `phys101_waveform.pkl` or run the `preprocess_waveform.py` file to create the appropriate pickle file, as SoundNet expects waveforms.

Pretrained Model Parameters
===========================
You can also load some pretrained model parameters [here](https://drive.google.com/drive/folders/1ECMDyuiv3m-JgnZLP_tSUzFKUvP5dEk6?usp=sharing). The .pth files are contained in models > pth_files.

Code
====
All the code to preprocess the data (turn the videos into appropriate pickles) is contained in "preprocess_data" above. All the code to run SoundNet, ResNet-18, Sound of Pixels, and the multimodal models can be found in "models" above.