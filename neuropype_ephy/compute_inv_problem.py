# Created on Thu Oct  8 17:53:07 2015
# @author: pasca


def compute_noise_cov(cov_fname, raw):
    """
    Compute noise covariance data from a continuous segment of raw data.
    Employ empty room data (collected without the subject) to calculate
    the full noise covariance matrix.
    This is recommended for analyzing ongoing spontaneous activity.

    Inputs
        cov_fname : str
            noise covariance file name
        raw : Raw
            the raw data

    Output
        cov_fname : str
            noise covariance file name in which is saved the noise covariance
            matrix
    """

    import os.path as op

    from mne import compute_raw_covariance, pick_types, write_cov
    from nipype.utils.filemanip import split_filename as split_f
    from neuropype_ephy.preproc import create_reject_dict

    print '***** COMPUTE RAW COV *****' + cov_fname

    if not op.isfile(cov_fname):

        data_path, basename, ext = split_f(raw.info['filename'])
        fname = op.join(data_path, '%s-cov.fif' % basename)

        reject = create_reject_dict(raw.info)

        picks = pick_types(raw.info, meg=True, ref_meg=False, exclude='bads')

        noise_cov = compute_raw_covariance(raw, picks=picks, reject=reject)

        write_cov(fname, noise_cov)

    else:
        print '*** NOISE cov file %s exists!!!' % cov_fname

    return cov_fname


def read_noise_cov(cov_fname, raw_info):
    """
    Read a noise covariance matrix from cov_fname

    Inputs
        cov_fname : str
            noise covariance file name
        raw_info : dict
            dictionary containing the information about the raw data

    Outputs
        noise_cov : Covariance
            the noise covariance matrix
    """
    import os.path as op
    import numpy as np
    import mne

    print '***** READ RAW COV *****' + cov_fname

    if not op.isfile(cov_fname):
        # create an Identity matrix
        picks = mne.pick_types(raw_info, meg=True, ref_meg=False,
                               exclude='bads')
        ch_names = [raw_info['ch_names'][i] for i in picks]

        C = mne.Covariance(data=np.identity(len(picks)), names=ch_names,
                           bads=[], projs=[], nfree=0)
        mne.write_cov(cov_fname, C)
    else:
        print '*** noise covariance file %s exists!!!' % cov_fname
        noise_cov = mne.read_cov(cov_fname)

    return noise_cov


def compute_ts_inv_sol(raw, fwd_filename, cov_fname, snr, inv_method, aseg):
    import os.path as op
    import numpy as np
    import mne
    from mne.minimum_norm import make_inverse_operator, apply_inverse_raw
    from nipype.utils.filemanip import split_filename as split_f

    print '***** READ FWD SOL %s *****' % fwd_filename
    forward = mne.read_forward_solution(fwd_filename)

    # Convert to surface orientation for cortically constrained
    # inverse modeling
    if not aseg:
        forward = mne.convert_forward_solution(forward, surf_ori=True)

    lambda2 = 1.0 / snr ** 2

    # compute inverse operator
    print '***** COMPUTE INV OP *****'
    inverse_operator = make_inverse_operator(raw.info, forward, cov_fname,
                                             loose=0.2, depth=0.8)

    # apply inverse operator to the time windows [t_start, t_stop]s
    # TEST
    t_start = 0  # sec
    t_stop = 3  # sec
    start, stop = raw.time_as_index([t_start, t_stop])
    print '***** APPLY INV OP ***** [%d %d]sec' % (t_start, t_stop)
    stc = apply_inverse_raw(raw, inverse_operator, lambda2, inv_method,
                            label=None,
                            start=start, stop=stop, pick_ori=None)

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

'''
+---------------------+-----------+-----------+-----------+-----------------+--------------+
| Inverse desired                             | Forward parameters allowed                 |
+=====================+===========+===========+===========+=================+==============+
|                     | **loose** | **depth** | **fixed** | **force_fixed** | **surf_ori** |
+---------------------+-----------+-----------+-----------+-----------------+--------------+
| | Loose constraint, | 0.2       | 0.8       | False     | False           | True         |
| | Depth weighted    |           |           |           |                 |              |
+---------------------+-----------+-----------+-----------+-----------------+--------------+
| | Loose constraint  | 0.2       | None      | False     | False           | True         |
+---------------------+-----------+-----------+-----------+-----------------+--------------+
| | Free orientation, | None      | 0.8       | False     | False           | True         |
| | Depth weighted    |           |           |           |                 |              |
+---------------------+-----------+-----------+-----------+-----------------+--------------+
| | Free orientation  | None      | None      | False     | False           | True | False |
+---------------------+-----------+-----------+-----------+-----------------+--------------+
| | Fixed constraint, | None      | 0.8       | True      | False           | True         |
| | Depth weighted    |           |           |           |                 |              |
+---------------------+-----------+-----------+-----------+-----------------+--------------+
| | Fixed constraint  | None      | None      | True      | True            | True         |
+---------------------+-----------+-----------+-----------+-----------------+--------------+       
'''


def compute_ROIs_inv_sol(raw_filename, sbj_id, sbj_dir, fwd_filename,
                         cov_fname, is_epoched=False, events_id=[],
                         t_min=None, t_max=None, is_evoked=False,
                         snr=1.0, inv_method='MNE',
                         parc='aparc', aseg=False, aseg_labels=[],
                         save_stc=False):
    """
    Compute the inverse solution on raw/epoched data and return the average
    time series computed in the N_r regions of the source space defined by
    the specified cortical parcellation

    Inputs
        raw_filename : str
            filename of the raw/epoched data
        sbj_id : str
            subject name
        sbj_dir : str
            Freesurfer directory
        fwd_filename : str
            filename of the forward operator
        cov_filename : str
            filename of the noise covariance matrix
        is_epoched : bool
            if True and events_id = None the input data are epoch data
            in the format -epo.fif
            if True and events_id is not None, the raw data are epoched
            according to events_id and t_min and t_max values
        events_id: dict
            the dict of events
        t_min, t_max: int
            define the time interval in which to epoch the raw data
        is_evoked: bool
            if True the raw data will be averaged according to the events
            contained in the dict events_id
        inv_method : str
            the inverse method to use; possible choices: MNE, dSPM, sLORETA
        snr : float
            the SNR value used to define the regularization parameter
        parc: str
            the parcellation defining the ROIs atlas in the source space
        aseg: bool
            if True a mixed source space will be created and the sub cortical
            regions defined in aseg_labels will be added to the source space
        aseg_labels: list
            list of substructures we want to include in the mixed source space
        save_stc: bool
            if True the stc will be saved

    Outputs
        ts_file : str
            filename of the file where are saved the ROIs time series
        labels_file : str
            filename of the file where are saved the ROIs of the parcellation
        label_names_file : str
            filename of the file where are saved the name of the ROIs of the
            parcellation
        label_coords_file : str
            filename of the file where are saved the coordinates of the
            centroid of the ROIs of the parcellation

    """
    import os
    import os.path as op
    import numpy as np
    import mne
    import pickle

    from mne.io import read_raw_fif
    from mne import read_epochs
    from mne.minimum_norm import make_inverse_operator, apply_inverse_raw
    from mne.minimum_norm import apply_inverse_epochs, apply_inverse
    from mne import get_volume_labels_from_src

    from nipype.utils.filemanip import split_filename as split_f

    from neuropype_ephy.preproc import create_reject_dict

    try:
        traits.undefined(events_id)
    except NameError:
        events_id = None

    print '\n*** READ raw filename %s ***\n' % raw_filename
    if is_epoched and events_id is None:
        epochs = read_epochs(raw_filename)
        info = epochs.info
    else:
        raw = read_raw_fif(raw_filename, add_eeg_ref=False)
        raw.set_eeg_reference()
        info = raw.info

    subj_path, basename, ext = split_f(raw_filename)

    print '\n*** READ noise covariance %s ***\n' % cov_fname
    noise_cov = mne.read_cov(cov_fname)

    print '\n*** READ FWD SOL %s ***\n' % fwd_filename
    forward = mne.read_forward_solution(fwd_filename)

    if not aseg:
        forward = mne.convert_forward_solution(forward, surf_ori=True,
                                               force_fixed=False)

    lambda2 = 1.0 / snr ** 2

    # compute inverse operator
    print '\n*** COMPUTE INV OP ***\n'
    if not aseg:
        loose = 0.2
        depth = 0.8
    else:
        loose = None
        depth = None

    inverse_operator = make_inverse_operator(info, forward, noise_cov,
                                             loose=loose, depth=depth,
                                             fixed=False)

    # apply inverse operator to the time windows [t_start, t_stop]s
    print '\n*** APPLY INV OP ***\n'
    if is_epoched and events_id is not None:
        events = mne.find_events(raw)
        picks = mne.pick_types(info, meg=True, eog=True, exclude='bads')
        reject = create_reject_dict(info)

        if is_evoked:
            epochs = mne.Epochs(raw, events, events_id, t_min, t_max,
                                picks=picks, baseline=(None, 0), reject=reject)
            evoked = [epochs[k].average() for k in events_id]
            snr = 3.0
            lambda2 = 1.0 / snr ** 2

            ev_list = events_id.items()
            for k in range(len(events_id)):
                stc = apply_inverse(evoked[k], inverse_operator, lambda2,
                                    inv_method, pick_ori=None)

                print '\n*** STC for event %s ***\n' % ev_list[k][0]
                stc_file = op.abspath(basename + '_' + ev_list[k][0])

                print '***'
                print 'stc dim ' + str(stc.shape)
                print '***'

                if not aseg:
                    stc.save(stc_file)

        else:
            epochs = mne.Epochs(raw, events, events_id, t_min, t_max,
                                picks=picks, baseline=(None, 0), reject=reject)
            stc = apply_inverse_epochs(epochs, inverse_operator, lambda2,
                                       inv_method, pick_ori=None)

            print '***'
            print 'len stc %d' % len(stc)
            print '***'

    elif is_epoched and events_id is None:
        stc = apply_inverse_epochs(epochs, inverse_operator, lambda2,
                                   inv_method, pick_ori=None)

        print '***'
        print 'len stc %d' % len(stc)
        print '***'
    else:
        stc = apply_inverse_raw(raw, inverse_operator, lambda2, inv_method,
                                label=None,
                                start=None, stop=None,
                                buffer_size=1000,
                                pick_ori=None)  # None 'normal'

        print '***'
        print 'stc dim ' + str(stc.shape)
        print '***'

    if save_stc:
        if aseg:
            for i in range(len(stc)):
                try:
                    os.mkdir(op.join(subj_path, 'TS'))
                except OSError:
                    pass
                stc_file = op.join(subj_path, 'TS', basename + '_' +
                                   inv_method + '_stc_' + str(i) + '.npy')

                if not op.isfile(stc_file):
                    np.save(stc_file, stc[i].data)

    labels_cortex = mne.read_labels_from_annot(sbj_id, parc=parc,
                                               subjects_dir=sbj_dir)

    print '\n*** %d ***\n' % len(labels_cortex)

    src = inverse_operator['src']

    # allow_empty : bool -> Instead of emitting an error, return all-zero time
    # courses for labels that do not have any vertices in the source estimate
    label_ts = mne.extract_label_time_course(stc, labels_cortex, src,
                                             mode='mean',
                                             allow_empty=True,
                                             return_generator=False)

    # save results in .npy file that will be the input for spectral node
    print '\n*** SAVE ROI TS ***\n'
    print len(label_ts)

    ts_file = op.abspath(basename + '_ROI_ts.npy')
    np.save(ts_file, label_ts)

    if aseg:
        print sbj_id
        labels_aseg = get_volume_labels_from_src(src, sbj_id, sbj_dir)
        labels = labels_cortex + labels_aseg
    else:
        labels = labels_cortex

    print labels[0].pos
    print len(labels)

    labels_file = op.abspath('labels.dat')
    with open(labels_file, "wb") as f:
        pickle.dump(len(labels), f)
        for value in labels:
            pickle.dump(value, f)

    label_names_file = op.abspath('label_names.txt')
    label_coords_file = op.abspath('label_coords.txt')

    label_names = []
    label_coords = []

    for value in labels:
        label_names.append(value.name)
#        label_coords.append(value.pos[0])
        label_coords.append(np.mean(value.pos, axis=0))

    np.savetxt(label_names_file, np.array(label_names, dtype=str),
               fmt="%s")
    np.savetxt(label_coords_file, np.array(label_coords, dtype=float),
               fmt="%f %f %f")

    return ts_file, labels_file, label_names_file, label_coords_file
