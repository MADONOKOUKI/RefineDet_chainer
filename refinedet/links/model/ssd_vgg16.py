from __future__ import division

import numpy as np
import warnings

import chainer
import chainer.functions as F
from chainer import initializers
import chainer.links as L

from chainercv.links.model.ssd import ResidualMultibox
from chainercv.links.model.ssd import DeconvolutionalResidualMultibox
from chainercv.links.model.ssd import Normalize
from chainercv.links.model.ssd import SSD
from chainercv.links.model.ssd import VGG16Extractor300
from chainercv.utils import download_model

from refinedet.links.model.multibox import ExtendedMultibox
from refinedet.links.model.multibox import ExtendedResidualMultibox
from refinedet.links.model.multibox import MultiboxWithTCB
from refinedet.links.model.ssd import RefineDetSSD

try:
    import cv2  # NOQA
    _available = True
except ImportError:
    _available = False


# RGB, (C, 1, 1) format
_imagenet_mean = np.array((123, 117, 104)).reshape((-1, 1, 1))


# to skip unsaved parameters, use strict option.
def _load_npz(filename, obj):
    with np.load(filename) as f:
        d = chainer.serializers.NpzDeserializer(f, strict=False)
        d.load(obj)


def _check_pretrained_model(n_fg_class, pretrained_model, models):
    if pretrained_model in models:
        model = models[pretrained_model]
        if n_fg_class:
            if model['n_fg_class'] and not n_fg_class == model['n_fg_class']:
                raise ValueError(
                    'n_fg_class should be {:d}'.format(model['n_fg_class']))
        else:
            if not model['n_fg_class']:
                raise ValueError('n_fg_class must be specified')
            n_fg_class = model['n_fg_class']

        path = download_model(model['url'])

        if not _available:
            warnings.warn(
                'cv2 is not installed on your environment. '
                'Pretrained models are trained with cv2. '
                'The performace may change with Pillow backend.',
                RuntimeWarning)
    elif pretrained_model:
        path = pretrained_model
    else:
        path = None

    return n_fg_class, path


class SSD300Plus(SSD):
    """Single Shot Multibox Detector with 300x300 inputs with residual
    prediction module [#].

    .. [#] Wei Liu, Dragomir Anguelov, Dumitru Erhan, Christian Szegedy,
       Scott Reed, Cheng-Yang Fu, Alexander C. Berg.
       SSD: Single Shot MultiBox Detector. ECCV 2016.

    """

    _models = {
        'voc0712': {
            'n_fg_class': 20,
            'url': 'https://github.com/yuyu2172/share-weights/releases/'
            'download/0.0.3/ssd300_voc0712_2017_06_06.npz'
        },
        'imagenet': {
            'n_fg_class': None,
            'url': 'https://github.com/yuyu2172/share-weights/releases/'
            'download/0.0.3/ssd_vgg16_imagenet_2017_06_09.npz'
        },
    }

    def __init__(self, n_fg_class=None, pretrained_model=None):
        n_fg_class, path = _check_pretrained_model(
            n_fg_class, pretrained_model, self._models)

        super(SSD300Plus, self).__init__(
            extractor=VGG16Extractor300(),
            multibox=ResidualMultibox(
                n_class=n_fg_class + 1,
                aspect_ratios=((2,), (2, 3), (2, 3), (2, 3), (2,), (2,))),
            steps=(8, 16, 32, 64, 100, 300),
            sizes=(30, 60, 111, 162, 213, 264, 315),
            mean=_imagenet_mean)

        if path:
            _load_npz(path, self)


class DSSD300(SSD):
    """Deconvolutional Single Shot Multibox Detector with 300x300 inputs.

    This is a model of Single Shot Multibox Detector [#]_.
    This model uses :class:`~chainercv.links.model.ssd.VGG16Extractor300` as
    its feature extractor.

    .. [#] Wei Liu, Dragomir Anguelov, Dumitru Erhan, Christian Szegedy,
       Scott Reed, Cheng-Yang Fu, Alexander C. Berg.
       SSD: Single Shot MultiBox Detector. ECCV 2016.

    Args:
       n_fg_class (int): The number of classes excluding the background.
       pretrained_model (str): The weight file to be loaded.
           This can take :obj:`'voc0712'`, `filepath` or :obj:`None`.
           The default value is :obj:`None`.

            * :obj:`'voc0712'`: Load weights trained on trainval split of \
                PASCAL VOC 2007 and 2012. \
                The weight file is downloaded and cached automatically. \
                :obj:`n_fg_class` must be :obj:`20` or :obj:`None`. \
                These weights were converted from the Caffe model provided by \
                `the original implementation \
                <https://github.com/weiliu89/caffe/tree/ssd>`_. \
                The conversion code is `chainercv/examples/ssd/caffe2npz.py`.
            * :obj:`'imagenet'`: Load weights of VGG-16 trained on ImageNet. \
                The weight file is downloaded and cached automatically. \
                This option initializes weights partially and the rests are \
                initialized randomly. In this case, :obj:`n_fg_class` \
                can be set to any number.
            * `filepath`: A path of npz file. In this case, :obj:`n_fg_class` \
                must be specified properly.
            * :obj:`None`: Do not load weights.

    """

    _models = {
        'voc0712': {
            'n_fg_class': 20,
            'url': 'https://github.com/yuyu2172/share-weights/releases/'
            'download/0.0.3/ssd300_voc0712_2017_06_06.npz'
        },
        'imagenet': {
            'n_fg_class': None,
            'url': 'https://github.com/yuyu2172/share-weights/releases/'
            'download/0.0.3/ssd_vgg16_imagenet_2017_06_09.npz'
        },
    }

    def __init__(self, n_fg_class=None, pretrained_model=None):
        n_fg_class, path = _check_pretrained_model(
            n_fg_class, pretrained_model, self._models)

        super(DSSD300, self).__init__(
            extractor=VGG16Extractor300(),
            multibox=DeconvolutionalResidualMultibox(
                n_class=n_fg_class + 1,
                aspect_ratios=((2,), (2, 3), (2, 3), (2, 3), (2,), (2,))),
            steps=(8, 16, 32, 64, 100, 300),
            sizes=(30, 60, 111, 162, 213, 264, 315),
            mean=_imagenet_mean)

        if path:
            _load_npz(path, self)


class ESSD300Plus(SSD):
    """Deconvolutional Single Shot Multibox Detector with 300x300 inputs.

    This is a model of Single Shot Multibox Detector [#]_.
    This model uses :class:`~chainercv.links.model.ssd.VGG16Extractor300` as
    its feature extractor.

    .. [#] Wei Liu, Dragomir Anguelov, Dumitru Erhan, Christian Szegedy,
       Scott Reed, Cheng-Yang Fu, Alexander C. Berg.
       SSD: Single Shot MultiBox Detector. ECCV 2016.

    Args:
       n_fg_class (int): The number of classes excluding the background.
       pretrained_model (str): The weight file to be loaded.
           This can take :obj:`'voc0712'`, `filepath` or :obj:`None`.
           The default value is :obj:`None`.

            * :obj:`'voc0712'`: Load weights trained on trainval split of \
                PASCAL VOC 2007 and 2012. \
                The weight file is downloaded and cached automatically. \
                :obj:`n_fg_class` must be :obj:`20` or :obj:`None`. \
                These weights were converted from the Caffe model provided by \
                `the original implementation \
                <https://github.com/weiliu89/caffe/tree/ssd>`_. \
                The conversion code is `chainercv/examples/ssd/caffe2npz.py`.
            * :obj:`'imagenet'`: Load weights of VGG-16 trained on ImageNet. \
                The weight file is downloaded and cached automatically. \
                This option initializes weights partially and the rests are \
                initialized randomly. In this case, :obj:`n_fg_class` \
                can be set to any number.
            * `filepath`: A path of npz file. In this case, :obj:`n_fg_class` \
                must be specified properly.
            * :obj:`None`: Do not load weights.

    """

    _models = {
        # 'voc0712': {
        #     'n_fg_class': 20,
        #     'url': 'https://github.com/yuyu2172/share-weights/releases/'
        #     'download/0.0.3/ssd300_voc0712_2017_06_06.npz'
        # },
        'imagenet': {
            'n_fg_class': None,
            'url': 'https://github.com/yuyu2172/share-weights/releases/'
            'download/0.0.3/ssd_vgg16_imagenet_2017_06_09.npz'
        },
    }

    def __init__(self, n_fg_class=None, pretrained_model=None):
        n_fg_class, path = _check_pretrained_model(
            n_fg_class, pretrained_model, self._models)

        super(ESSD300Plus, self).__init__(
            extractor=VGG16Extractor300(),
            multibox=ExtendedResidualMultibox(
                n_class=n_fg_class + 1,
                aspect_ratios=((2,), (2, 3), (2, 3), (2, 3), (2,), (2,))),
            steps=(8, 16, 32, 64, 100, 300),
            sizes=(30, 60, 111, 162, 213, 264, 315),
            mean=_imagenet_mean)

        if path:
            _load_npz(path, self)


class ESSD300(SSD):
    """Extended Single Shot Multibox Detector with 300x300 inputs.

    This is a model of Extended Single Shot Multibox Detector [#]_.
    This model uses :class:`~chainercv.links.model.ssd.VGG16Extractor300` as
    its feature extractor.

    .. [#] Liwen Zheng, Canmiao Fu, Yong Zhao.
       Extend the shallow part of Single Shot MultiBox Detector via
       Convolutional Neural Network.

    Args:
       n_fg_class (int): The number of classes excluding the background.
       pretrained_model (str): The weight file to be loaded.
           This can take :obj:`'voc0712'`, `filepath` or :obj:`None`.
           The default value is :obj:`None`.

            * :obj:`'voc0712'`: Load weights trained on trainval split of \
                PASCAL VOC 2007 and 2012. \
                The weight file is downloaded and cached automatically. \
                :obj:`n_fg_class` must be :obj:`20` or :obj:`None`. \
                These weights were converted from the Caffe model provided by \
                `the original implementation \
                <https://github.com/weiliu89/caffe/tree/ssd>`_. \
                The conversion code is `chainercv/examples/ssd/caffe2npz.py`.
            * :obj:`'imagenet'`: Load weights of VGG-16 trained on ImageNet. \
                The weight file is downloaded and cached automatically. \
                This option initializes weights partially and the rests are \
                initialized randomly. In this case, :obj:`n_fg_class` \
                can be set to any number.
            * `filepath`: A path of npz file. In this case, :obj:`n_fg_class` \
                must be specified properly.
            * :obj:`None`: Do not load weights.

    """

    _models = {
        # 'voc0712': {
        #     'n_fg_class': 20,
        #     'url': 'https://github.com/yuyu2172/share-weights/releases/'
        #     'download/0.0.3/ssd300_voc0712_2017_06_06.npz'
        # },
        'imagenet': {
            'n_fg_class': None,
            'url': 'https://github.com/yuyu2172/share-weights/releases/'
            'download/0.0.3/ssd_vgg16_imagenet_2017_06_09.npz'
        },
    }

    def __init__(self, n_fg_class=None, pretrained_model=None):
        n_fg_class, path = _check_pretrained_model(
            n_fg_class, pretrained_model, self._models)

        super(ESSD300, self).__init__(
            extractor=VGG16Extractor300(),
            multibox=ExtendedMultibox(
                n_class=n_fg_class + 1,
                aspect_ratios=((2,), (2, 3), (2, 3), (2, 3), (2,), (2,))),
            steps=(8, 16, 32, 64, 100, 300),
            sizes=(30, 60, 111, 162, 213, 264, 315),
            mean=_imagenet_mean)

        if path:
            _load_npz(path, self)


class VGG16RefineDet(chainer.Chain):
    """An extended VGG-16 model for SSD320.

    This is an extended VGG-16 model proposed in [#]_.
    The differences from original VGG-16 [#]_ are shown below.

    * :obj:`conv5_1`, :obj:`conv5_2` and :obj:`conv5_3` are changed from \
    :class:`~chainer.links.Convolution2d` to \
    :class:`~chainer.links.DilatedConvolution2d`.
    * :class:`~chainercv.links.model.ssd.Normalize` is \
    inserted after :obj:`conv4_3`.
    * The parameters of max pooling after :obj:`conv5_3` are changed.
    * :obj:`fc6` and :obj:`fc7` are converted to :obj:`conv6` and :obj:`conv7`.

    .. [#] Wei Liu, Dragomir Anguelov, Dumitru Erhan,
       Christian Szegedy, Scott Reed, Cheng-Yang Fu, Alexander C. Berg.
       SSD: Single Shot MultiBox Detector. ECCV 2016.
    .. [#] Karen Simonyan, Andrew Zisserman.
       Very Deep Convolutional Networks for Large-Scale Image Recognition.
       ICLR 2015.
    """

    def __init__(self):
        super(VGG16RefineDet, self).__init__()
        with self.init_scope():
            self.conv1_1 = L.Convolution2D(64, 3, pad=1)
            self.conv1_2 = L.Convolution2D(64, 3, pad=1)

            self.conv2_1 = L.Convolution2D(128, 3, pad=1)
            self.conv2_2 = L.Convolution2D(128, 3, pad=1)

            self.conv3_1 = L.Convolution2D(256, 3, pad=1)
            self.conv3_2 = L.Convolution2D(256, 3, pad=1)
            self.conv3_3 = L.Convolution2D(256, 3, pad=1)

            self.conv4_1 = L.Convolution2D(512, 3, pad=1)
            self.conv4_2 = L.Convolution2D(512, 3, pad=1)
            self.conv4_3 = L.Convolution2D(512, 3, pad=1)
            self.norm4 = Normalize(512, initial=initializers.Constant(20))

            self.conv5_1 = L.DilatedConvolution2D(512, 3, pad=1)
            self.conv5_2 = L.DilatedConvolution2D(512, 3, pad=1)
            self.conv5_3 = L.DilatedConvolution2D(512, 3, pad=1)

            self.conv6 = L.DilatedConvolution2D(1024, 3, pad=3, dilate=3)
            self.conv7 = L.Convolution2D(1024, 1)

    def __call__(self, x):
        ys = list()

        h = F.relu(self.conv1_1(x))
        h = F.relu(self.conv1_2(h))
        h = F.max_pooling_2d(h, 2)

        h = F.relu(self.conv2_1(h))
        h = F.relu(self.conv2_2(h))
        h = F.max_pooling_2d(h, 2)

        h = F.relu(self.conv3_1(h))
        h = F.relu(self.conv3_2(h))
        h = F.relu(self.conv3_3(h))
        h = F.max_pooling_2d(h, 2)

        h = F.relu(self.conv4_1(h))
        h = F.relu(self.conv4_2(h))
        h = F.relu(self.conv4_3(h))
        ys.append(self.norm4(h))
        h = F.max_pooling_2d(h, 2)

        h = F.relu(self.conv5_1(h))
        h = F.relu(self.conv5_2(h))
        h = F.relu(self.conv5_3(h))
        ys.append(self.norm4(h))
        h = F.max_pooling_2d(h, 2, stride=2, pad=0)

        h = F.relu(self.conv6(h))
        h = F.relu(self.conv7(h))
        ys.append(h)

        return ys


class VGG16Extractor320(VGG16RefineDet):
    """A VGG-16 based feature extractor for RefineDet320.

    """

    insize = 320
    grids = (40, 20, 10, 5)

    def __init__(self):
        init = {
            'initialW': initializers.LeCunUniform(),
            'initial_bias': initializers.Zero(),
        }
        super(VGG16Extractor320, self).__init__()
        with self.init_scope():
            self.conv6_1 = L.Convolution2D(256, 1, **init)
            self.conv6_2 = L.Convolution2D(512, 3, stride=2, pad=1, **init)

    def __call__(self, x):
        """Compute feature maps from a batch of images.

        This method extracts feature maps from
        :obj:`conv4_3`, :obj:`conv7`, :obj:`conv8_2`,
        :obj:`conv9_2`, :obj:`conv10_2`, :obj:`conv11_2`, and :obj:`conv12_2`.

        Args:
            x (ndarray): An array holding a batch of images.
                The images should be resized to :math:`512\\times 512`.

        Returns:
            list of Variable:
            Each variable contains a feature map.
        """

        ys = super(VGG16Extractor320, self).__call__(x)
        h = ys[-1]
        h = F.relu(self.conv6_1(h))
        h = F.relu(self.conv6_2(h))
        ys.append(h)
        return ys


class RefineDet320(RefineDetSSD):
    """RefineDet with 320x320 inputs.

    This is a model of RefineDet [#]_.
    This model uses :class:`~chainercv.links.model.ssd.VGG16Extractor320` as
    its feature extractor.

    .. [#] Shifeng Zhang, Longyin Wen, Xiao Bian, Zhen Lei, Stan Z. Li.
       Single-Shot Refinement Neural Network for Object Detection.

    Args:
       n_fg_class (int): The number of classes excluding the background.
       pretrained_model (str): The weight file to be loaded.
           This can take :obj:`'voc0712'`, `filepath` or :obj:`None`.
           The default value is :obj:`None`.

            * :obj:`'voc0712'`: Load weights trained on trainval split of \
                PASCAL VOC 2007 and 2012. \
                The weight file is downloaded and cached automatically. \
                :obj:`n_fg_class` must be :obj:`20` or :obj:`None`. \
                These weights were converted from the Caffe model provided by \
                `the original implementation \
                <https://github.com/weiliu89/caffe/tree/ssd>`_. \
                The conversion code is `chainercv/examples/ssd/caffe2npz.py`.
            * :obj:`'imagenet'`: Load weights of VGG-16 trained on ImageNet. \
                The weight file is downloaded and cached automatically. \
                This option initializes weights partially and the rests are \
                initialized randomly. In this case, :obj:`n_fg_class` \
                can be set to any number.
            * `filepath`: A path of npz file. In this case, :obj:`n_fg_class` \
                must be specified properly.
            * :obj:`None`: Do not load weights.

    """

    _models = {
        # 'voc0712': {
        #     'n_fg_class': 20,
        #     'url': 'https://github.com/yuyu2172/share-weights/releases/'
        #     'download/0.0.3/ssd300_voc0712_2017_06_06.npz'
        # },
        'imagenet': {
            'n_fg_class': None,
            'url': 'https://github.com/fukatani/RefineDet_chainer/releases/'
                   'download/0.0.0/VGG_ILSVRC_16_layers_fc_reduced.npz'
        },
    }

    def __init__(self, n_fg_class=None, pretrained_model=None):
        n_fg_class, path = _check_pretrained_model(
            n_fg_class, pretrained_model, self._models)

        super(RefineDet320, self).__init__(
            extractor=VGG16Extractor320(),
            multibox=MultiboxWithTCB(
                n_class=n_fg_class + 1,
                aspect_ratios=((2,), (2,), (2,), (2,))),
            steps=(8, 16, 32, 64),
            sizes=(32, 64, 128, 256),
            mean=_imagenet_mean)

        if path:
            _load_npz(path, self)
