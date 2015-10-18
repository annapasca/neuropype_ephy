# 2015.10.09 12:02:45 EDT
# Embedded file name: /home/karim/Documents/pasca/packages/neuropype_ephy/neuropype_ephy/compute_inv_problem.py
"""
Created on Thu Oct  8 17:53:07 2015

@author: pasca
"""
# compute inverse solution on raw data
def compute_inv_sol(raw, fwd_filename, snr, method):
    import os.path as op
    import numpy as np
    import mne
    from mne.minimum_norm import make_inverse_operator, apply_inverse_raw
    from nipype.utils.filemanip import split_filename as split_f
    
    print '***** READ FWD SOL %s *****' %fwd_filename
    forward = mne.read_forward_solution(fwd_filename)
    forward = mne.convert_forward_solution(forward, surf_ori=True)

    lambda2 = 1.0 / snr ** 2
    reject = dict(mag=4e-12, grad=4000e-13, eog=250e-6)

    picks = mne.pick_types(raw.info, meg=True, ref_meg=False, exclude='bads')

    # compute noise covariance data
    print '***** COMPUTE RAW COV *****'
    noise_cov = mne.compute_raw_covariance(raw, picks=picks, reject=reject)
    
    # compute inverse operator    
    print '***** COMPUTE INV OP *****'
    inverse_operator = make_inverse_operator(raw.info, forward, noise_cov, loose=0.2, depth=0.8)
    
    # apply inverse operator to the time windows [t_start, t_stop]s
    t_start = 0 # sec
    t_stop  = 3 # sec
    start, stop = raw.time_as_index([t_start, t_stop])
    print '***** APPLY INV OP ***** [%d %d]sec' %(t_start, t_stop)
    stc = apply_inverse_raw(raw, inverse_operator, lambda2, method, label=None, start=start, stop=stop, pick_ori=None)
    
    print '***'
    print 'stc dim ' + str(stc.shape)
    print '***'
    
    subj_path, basename, ext = split_f(raw.info['filename'])
    data = stc.data
    
    print 'data dim ' + str(data.shape)

    # save results in .npy file that will be the input for spectral node
    print '***** SAVE SOL *****'
    ts_file = op.abspath(basename + '.npy')
    np.save(ts_file, data)

    return ts_file