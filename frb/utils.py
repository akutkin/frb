# -*- coding: utf-8 -*-
import numpy as np
import os
import fnmatch
from sklearn.mixture import DPGMM, GMM
from sklearn.cluster import DBSCAN
from astropy.stats import mad_std, biweight_location
from scipy.stats import rayleigh
from scipy import signal

vround = np.vectorize(round)
vint = np.vectorize(int)


# TODO: Clipping out pixels with high `noise` flux can remove real FRB if it
# has high enough flux
def find_noisy(dsp, n_max_components, frac=1, alpha=0.1):
    """
    Attempt to characterize the noise of dynamical spectra. Fitting Dirichlet
    Process Gaussian Mixture Model to histogram of ``dsp`` values. If 2 (or
    more) components is chosen then we can find typical threshold for noise
    values.

    :param dsp:
        2D numpy.ndarray of dynamical spectra (n_nu, n_t).
    :param n_max_components:
        Maximum number of components to check.
    :param frac: (optional)
        Integer. Fraction ``1/frac`` will be used for ``sklearn.mixture.DPGMM``
        fitting. (default: ``1``)
    :param alpha: (optional)
        ``alpha`` parameter of DP. A higher alpha means more clusters, as the
        expected number of clusters is ``alpha*log(N)``. (default: ``0.1``)

    :return:
        Tuple. First element is dictionary with keys - number of component,
        values - lists of component mean, sigma, number of points & weight.
        Second element is 2D numpy.ndarray with shape as original ``dsp`` shape
        where each pixel has value equal to component it belongs to.
    """
    data = dsp.copy()
    data = data.ravel()[::frac]
    data = data.reshape((data.size, 1))
    clf = DPGMM(n_components=n_max_components, alpha=alpha)
    clf.fit(data)
    y = clf.predict(data)
    components = sorted(list(set(y)))
    components_dict = {i: [clf.means_[i][0], clf.weights_[i],
                           1./np.sqrt(clf.precs_[i][0]), list(y).count(i)] for
                       i in components}

    # Append weight
    for k, a in components_dict.items():
        components_dict[k].append(a[1] * a[3])
        components_dict[k].remove(a[1])
    sum_nw = sum(a[-1] for a in components_dict.values())
    for k, a in components_dict.items():
        components_dict[k][-1] /= sum_nw

    dsp_classified = y.reshape(dsp.shape)

    return components_dict, dsp_classified


# FIXME: When # amplitudes is small enough, ``eps`` becomes too large...
def find_clusters_ell_amplitudes(amplitudes, min_samples=10, leaf_size=5,
                                 eps=None):
    """

    :param amplitudes:
    :param eps:
        `eps` parameter of `DBSCAN`.
    :param min_samples:
        `min_samples` parameter of `DBSCAN`.
    :param leaf_size:
        `leaf_size` parameter of `DBSCAN`.
    :return:
        Threshold for amplitude. Chosen in a way that fitted elliptical
        gaussians with amplitude higher then the threshold should be outliers
        (ie. represent signals).
    """

    data = np.asarray(amplitudes).copy()
    ldata = np.log(data)
    data_ = data.reshape((data.size, 1))
    ldata_ = ldata.reshape((ldata.size, 1))

    data_range = np.max(data) - np.min(data)
    if eps is None:
        eps = data_range / np.sqrt(len(amplitudes))
        print "eps {}".format(eps)
    db = DBSCAN(eps=eps, min_samples=min_samples,
                leaf_size=leaf_size).fit(data_)
    core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels = db.labels_
    # Number of clusters in labels, ignoring noise if present.
    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    unique, unique_counts = np.unique(labels, return_counts=True)
    largest_cluster_data = data[labels == unique[np.argmax(unique_counts)]]
    outliers = data[labels == -1]
    params = rayleigh.fit(largest_cluster_data)
    distr = rayleigh(loc=params[0], scale=params[1])
    threshold = distr.ppf(0.999)

    # Need data > threshold to ensure that low power outliers haven't been
    # included
    indx = np.logical_and(labels == -1, data > threshold)
    # return threshold
    return min(data[indx]) - eps


def moving_average(data, window_size):
    """
    See scipy.sinal window functions also.
    :param data:
    :param window_size:
    :return:
    """
    window = np.ones(int(window_size))/float(window_size)
    return np.convolve(data, window, 'same')


def gauss_kern(size, sizey=None):
    """ Returns a normalized 2D gauss kernel array for convolutions """
    size = int(size)
    if not sizey:
        sizey = size
    else:
        sizey = int(sizey)
    x, y = np.mgrid[-size:size+1, -sizey:sizey+1]
    g = np.exp(-(x**2/float(size)+y**2/float(sizey)))
    return g / g.sum()


def blur_image(im, n, ny=None) :
    """ blurs the image by convolving with a gaussian kernel of typical
        size n. The optional keyword argument ny allows for a different
        size in the y direction.
    """
    g = gauss_kern(n, sizey=ny)
    improc = signal.convolve(im,g, mode='valid')
    return improc


def smooth(x,window_len=11,window='hanning'):
    """smooth the data using a window with requested size.

    This method is based on the convolution of a scaled window with the signal.
    The signal is prepared by introducing reflected copies of the signal
    (with the window size) in both ends so that transient parts are minimized
    in the begining and end part of the output signal.

    input:
        x: the input signal
        window_len: the dimension of the smoothing window; should be an odd integer
        window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
            flat window will produce a moving average smoothing.

    output:
        the smoothed signal

    example:

    t=linspace(-2,2,0.1)
    x=sin(t)+randn(len(t))*0.1
    y=smooth(x)

    see also:
    numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
    scipy.signal.lfilter

    TODO: the window parameter could be the window itself if an array instead of a string
    NOTE: length(output) != length(input), to correct this: return y[(window_len/2-1):-(window_len/2)] instead of just y.
    """

    if x.ndim != 1:
        raise ValueError, "smooth only accepts 1 dimension arrays."

    if x.size < window_len:
        raise ValueError, "Input vector needs to be bigger than window size."


    if window_len<3:
        return x


    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"


    s=np.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
    #print(len(s))
    if window == 'flat': #moving average
        w=np.ones(window_len,'d')
    else:
        w=eval('numpy.'+window+'(window_len)')

    y=np.convolve(w/w.sum(),s,mode='valid')
    return y


def find_robust_gaussian_params(data):
    """
    Calculate first two moments of gaussian in presence of outliers.
    :param data:
        Iterable of data points.
    :return:
        Mean & std of gaussian distribution.
    """
    mean = biweight_location(data)
    std = mad_std(data)
    return mean, std


def read_hdf5(fname, name):
    """
    Read data from HDF5 format.

    :param fname:
        File to read data.
    :param name:
        Name of dataset to use.

    :return:
        Numpy array with data & dictionary with metadata.

    :note:
        HDF5 hasn't time formats. Use ``unicode(datetime)`` to create strings
        with microseconds.
    """
    import h5py
    f = h5py.File(fname, "r")
    dset = f[name]
    meta_data = dict()
    for key, value in dset.attrs.items():
        meta_data.update({str(key): value})
    data = dset.value
    f.close()
    return data, meta_data


def find_file(fname, path='/'):
    """
    Find a file ``fname`` in ``path``. Wildcards are supported
    (ak)
    """
    matches = []
    for root, dirnames, filenames in os.walk(path):
        for filename in fnmatch.filter(filenames, fname):
            matches.append(os.path.join(root, filename))
    if not matches:
        return None
    return matches
