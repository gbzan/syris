"""Cameras used by experiments."""
import numpy as np


def is_fps_feasible(fps, exp_time):
    """Determine whether frame rate given by *fps* can be accomplished with
    the exposure time *exp_time*. It is only possible to set frame rates
    for which :math:`exposure\ time <= 1 / fps`.
    """
    return exp_time <= 1.0 / fps


class FPSError(ValueError):

    """Exception raised when exposure time exceeds :math:`1/FPS`."""

    def __init__(self, fps, exp_time):
        super(FPSError, self).__init__(
            "FPS {0} not feasible for exposure time {1}.".
            format(fps, exp_time))


def _fps_check_raise(fps, exp_time):
    """Check FPS and exposure time feasibility and raise exception if not
    compatible.
    """
    if not is_fps_feasible(fps, exp_time):
        raise FPSError(fps, exp_time)


class Camera(object):

    """Base class representing a camera."""

    def __init__(self, pixel_size, gain, dark_current, amplifier_sigma,
                 bits_per_pixel, quantum_efficiencies, shape=None,
                 exp_time=None, fps=None):
        """Create a camera with *pixel_size*, *gain*
        specifying :math:`\frac{counts}{e^-}`, *dark_current* as mean number
        of electrons present without incident light, *amplifier_sigma* is the
        sigma of the normal distributed noise given by camera electronics,
        *bit_per_pixel* is the number of bits holding the pixel grey value,
        *quantum_efficiencies* are specified as {energy: fraction}, *exp_time*
        is the exposure time and *fps* are Frames Per Second which are
        generated by the camera (exposure time is independent from fps, i.e.
        e.g. fps can be set to 1000 and exposure time to 1 \mu s, but
        it cannot exceed :math:`1/fps` s).
        """
        self.pixel_size = pixel_size
        self.gain = gain
        self.dark_current = dark_current
        self.amplifier_sigma = amplifier_sigma
        self.bpp = bits_per_pixel
        self.quantum_effs = quantum_efficiencies
        self._dtype = np.ushort
        self.shape = shape
        
        if fps is None and exp_time is None:
            self._fps = None
            self._exp_time = None
        else:
            if fps is not None:
                if exp_time is None:
                    exp_time = 1.0 / fps
            else:
                fps = 1.0 / exp_time
        
        if fps is not None:
            _fps_check_raise(fps, exp_time)
        self._exp_time = exp_time
        self._fps = fps
            
    @property
    def shape(self):
        return self._shape
    
    @shape.setter
    def shape(self, shape):
        self._shape = shape
        if self._shape is not None:
            self._dark_image = np.ones(self.shape, self._dtype) * \
                                self.dark_current
        else:
            self.dark_image = None

    @property
    def exp_time(self):
        return self._exp_time

    @exp_time.setter
    def exp_time(self, exp_time):
        _fps_check_raise(self.fps, exp_time)
        self._exp_time = exp_time.simplified

    @property
    def fps(self):
        return self._fps

    @fps.setter
    def fps(self, fps):
        _fps_check_raise(fps, self.exp_time)
        self._fps = fps.simplified

    @property
    def max_grey_value(self):
        return 2 ** self.bpp - 1

    def get_image(self, photons):
        """Get digital counts image from incoming *photons*. The resulting
        image is based on the incoming photons and dark current. We apply
        noise based on EMVA 1288 standard according to which the variance
        :math:`\sigma_y^2 = K^2 ( \sigma_e^2 + \sigma_d^2 ) + \sigma_q^2`,
        where :math:`K` is the system gain, :math:`\sigma_e^2` is the poisson-
        distributed shot noise variance, :math:`\sigma_d^2` is the normal
        distributed electronics noise variance and :math:`\sigma_q^2`
        is the quantization noise variance.
        """
        # Apply shot and electronics noise.
        res = self.gain * np.random.normal(np.random.poisson(
                                           photons + self._dark_image),
                                           self.amplifier_sigma)

        # Cut the values beyond the maximum represented grey value given by
        # bytes per pixel.
        res[np.where(res > self.max_grey_value)] = self.max_grey_value

        # Apply quantization noise
        return res.astype(self._dtype)
