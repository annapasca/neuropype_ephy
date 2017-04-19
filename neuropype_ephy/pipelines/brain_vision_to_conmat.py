# -*- coding: utf-8 -*-

import nipype.pipeline.engine as pe

from nipype.interfaces.utility import Function
from nipype.interfaces.utility import IdentityInterface


from neuropype_ephy.interfaces.mne.spectral import  SpectralConn,PlotSpectralConn

# from neuropype_ephy.spectral import  multiple_spectral_proc

from neuropype_ephy.nodes.import_data import ImportBrainVisionAscii

from neuropype_ephy.nodes.ts_tools import SplitWindows

from neuropype_ephy.import_txt import read_brainvision_vhdr

#from neuropype_ephy.spectral import split_win_ts

###TODO
#from neuropype_ephy.nodes.? import filter_adj_plot_mat

def create_pipeline_brain_vision_ascii_to_spectral_connectivity(main_path,pipeline_name="brain_vision_to_conmat", con_method = "coh", sample_size = 512, sep_label_name = "", sfreq = 512,filter_spectral = True, k_neigh = 3, n_windows = [], multi_con = False):
    
    """
    Description:
    
    Create pipeline from intraEEG times series in ascii format exported out of BrainVision, split txt and compute spectral connectivity.
    Possibly also filter out connections between "adjacent" contacts (on the same electrode)
    
    
    """
    pipeline = pe.Workflow(name=pipeline_name )
    pipeline.base_dir = main_path
    
    
    inputnode = pe.Node(interface = IdentityInterface(fields=['txt_file','freq_band']), name='inputnode')
    
    
    #### convert
    #split_ascii = pe.Node(interface = Function(input_names = ["sample_size","txt_file","sep_label_name"],output_names = ["splitted_ts_file","elec_names_file"],function = split_txt),name = 'split_ascii')
    
    split_ascii = pe.Node(interface = ImportBrainVisionAscii(),name = 'split_ascii')
    
    split_ascii.inputs.sample_size = sample_size
    split_ascii.inputs.sep_label_name = sep_label_name
    
    pipeline.connect(inputnode, 'txt_file',split_ascii,'txt_file')


    ts_pipe = create_pipeline_time_series_to_spectral_connectivity(main_path,sfreq, con_method = con_method, multi_con = multi_con, export_to_matlab = export_to_matlab, n_windows = n_windows)
    
     
     
    #pipeline.connect(inputnode, 'freq_band', ts_pipe, 'spectral.freq_band')
    pipeline.connect(inputnode, 'freq_band', ts_pipe, 'inputnode.freq_band')
    pipeline.connect(split_ascii, 'splitted_ts_file', ts_pipe, 'inputnode.ts_file')
    pipeline.connect(split_ascii, 'elec_names_file', ts_pipe, 'inputnode.labels_file')

     
    return pipeline
    
    
def create_pipeline_brain_vision_vhdr_to_spectral_connectivity(main_path,pipeline_name="brain_vision_to_conmat", con_method = "coh", sample_size = 512, sep_label_name = "", sfreq = 512,filter_spectral = True, k_neigh = 3, n_windows = [], multi_con = False):
    
    """
    Description:
    
    Create pipeline from intraEEG times series in ascii format exported out of BrainVision, split txt and compute spectral connectivity.
    Possibly also filter out connections between "adjacent" contacts (on the same electrode)
    
    
    """
    if multicon:
        pipeline_name = pipeline_name + "_multicon"
        
    pipeline = pe.Workflow(name=pipeline_name )
    pipeline.base_dir = main_path
    
    
    inputnode = pe.Node(interface = IdentityInterface(fields=['vhdr_file','freq_band']), name='inputnode')
    
    #### convert
    split_vhdr = pe.Node(interface = Function(input_names = ["vhdr_file","sample_size"],output_names = ["splitted_ts_file","channel_names"],function = read_brainvision_vhdr),name = 'split_vhdr')

    split_vhdr.inputs.sample_size = sample_size
    pipeline.connect(inputnode, 'vhdr_file',split_vhdr,'vhdr_file')

    ### pipeline ts_to_conmat
    ts_pipe = create_pipeline_time_series_to_spectral_connectivity(main_path,sfreq, con_method = con_method, multi_con = multi_con, export_to_matlab = export_to_matlab, n_windows = n_windows)
    
    pipeline.connect(split_vhdr,'splitted_ts_file',ts_pipe, 'inputnode.ts_file')
    pipeline.connect(split_vhdr,'channel_names',ts_pipe, 'inputnode.labels_file')
    pipeline.connect(inputnode, 'freq_band', ts_pipe, 'inputnode.freq_band')
     
    return pipeline
    