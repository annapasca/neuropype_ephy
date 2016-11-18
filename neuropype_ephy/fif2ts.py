""" fif convertors """

from neuropype_ephy.aux_tools import nostdout

def ep2ts(fif_file):
    """Read fif file with raw data or epochs and save
    timeseries to .npy
    """
    from mne import read_epochs
    from numpy import save
    import os.path as op

    with nostdout():
        epochs = read_epochs(fif_file)

    data = epochs.get_data()
    save_path = op.abspath('ts_epochs.npy')
    save(save_path, data)
    return save_path

