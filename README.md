# Search Fast Radio Bursts in Radioastron-project archive data

## Installing

```
$ git clone https://github.com/akutkin/frb.git
```
- Create & activate virtual environment for installing dependencies
```
$ cd frb
$ wget https://github.com/pypa/virtualenv/archive/master.zip
$ unzip master.zip
$ python2 virtualenv-master/virtualenv.py ./venv
$ source venv/bin/activate
```
- Install dependencies inside virtual environment
```
$ pip2 install scipy astropy scikit-learn scikit-image matplotlib h5py sqlalchemy
```

## Finding injected pulses in one file

- Download sample data
```
$ cd examples
$ wget https://www.dropbox.com/s/ag7rz88kjnblqzv/data.tgz
$ tar -xvzf data.tgz
```
- Run  script
```
$ python2 caching.py
```

- Deactivate virtual environment
```
$ deactivate
```
This script will inject pulses in raw data and search for them using three algorithms. Each one begins with non-coherent de-dispersion. First one shear ``t-DM`` plane on universal value and average frequencies to find peaks in time and then DM. Last two use pre-processing the resulting ``t-DM`` plane to reduce the noise and exclude some extended regions of atypicaly high amplitude. Blobs of high intensity are found. Next, 2D elliptical gaussians are fitted to regions of individuals blobs in original``t-DM`` plane. Second algorithm chooses candidates with auto-selected threshold gaussian amplitudes and some other parameters of gaussians that are specific to narrow dispersed pulses. Third algorithm uses artificially injected pulses to train ``Gradient Boosting Classifier``[Currently didn't used]. It uses features of fitted gaussians as well as numerous blob properties to build desicion surface in features space.


Searching pulses using fitted elliptical gaussians in ``t-DM`` place is much faster then using ``Gradient Boosting Classifier``. It is because later needs training sample to be constructed & analyzed. Also it finds best parameters of
classifier using grid of their values. All these steps (training of classifier) must be done only once for small portion of data. 


Currently, amplitudes of injected pulses in training phase are set by hand. It will be fixed soon by analyzing amplitudes of `noise` pulses in apriori pulse-free small chunk of data.

Script will create ``png`` plots of found candidates in original dynamical spectra & ``t-DM`` plane in ``frb/examples`` directory and dump data on found candidates and data searched in ``frb/frb/frb.db`` ``SQLite`` database.  It can be easily viewed/queried in ``Firefox`` with ``SQLite Manager`` addon.

## Process experiment
- Login to ``frb`` computer with your credientials
- Clone ``frb`` repository, install virtual environment, activate it & install dependencies inside virtual environment (see Installing)
- Download experiment CFX-file
```
$ cd frb/frb
$ wget https://www.dropbox.com/s/8pcmgmed36fo8uy/RADIOASTRON_RAKS12EC_C_20151030T210000_ASC_V1.cfx
```
- Compile ``my5spec`` program for converting raw ``Mk5`` data to txt-format
```
$ cd ../my5spec; /usr/bin/make
```
- Run example
```
$ cd ../frb
$ python2 pipeline.py
```
Script processes experiment (``raks12ec``, C-band, Noto & Yebes radiotelescopes). Results on data searched & pulse candidates are dumped to ``frb/frb/frb.db`` ``SQLite`` database. Finally, script check DB to find close (in time & DM) pulse candidates among searched antennas.

## Using ``docker``

There's no need to install any packages except ``docker`` itself

- Install ``docker`` package on your machine
- Run container with image and mount it to some directory ``host_dir`` on your host machine. It will take some time to download image with preinstalled OS & software.
```
$ docker run -it -v host_dir:/home/frb-dev/data ipashchenko/frb /bin/bash
```
- Inside container load data and start script
```
# cd frb-dev/examples
# wget https://www.dropbox.com/s/ag7rz88kjnblqzv/data.tgz
# tar -xvzf data.tgz
# python2 caching.py
```
- After it's execution copy results (images & DB file) to mounted dirrectory
```
# cp *.png ../data/.
# cp ../frb/frb.db ../data/.
```
- Results can be viewed in directory ``host_dir`` on your host machine.

## TODOs

- Currently, ``my5spec`` fails to read raw data with some format (see issue [#7](https://github.com/akutkin/frb/issues/7)) and fails to read ends of files (see issue [#13](https://github.com/akutkin/frb/issues/13)).
