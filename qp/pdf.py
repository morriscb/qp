import numpy as np
import scipy.interpolate as spi
import matplotlib.pyplot as plt

import qp

class PDF(object):

    def __init__(self, truth=None, quantiles=None, histogram=None, samples=None,
                 vb=True):
        """
        An object representing a probability density function in
        various ways.
        Parameters
        ----------
        truth: scipy.stats.rv_continuous object or qp.composite object, optional
            Continuous, parametric form of the PDF
        quantiles: tuple of ndarrays, optional
            Pair of arrays of lengths (nquants, nquants) containing CDF values and quantiles
        histogram: tuple of ndarrays, optional
            Pair of arrays of lengths (nbins+1, nbins) containing endpoints of bins and values in bins
        samples: ndarray, optional
            Array of length nsamples containing sampled values
        vb: boolean
            report on progress to stdout?
        """
        self.truth = truth
        self.quantiles = quantiles
        self.histogram = histogram
        self.samples = samples
        self.initialized = None

        if self.truth is not None:
            self.initialized = 'truth'
        elif self.quantiles is not None:
            self.initialized = 'quantiles'
        elif self.histogram is not None:
            self.initialized = 'histogram'
        elif self.samples is not None:
            self.initialized = 'samples'
        self.last = self.initialized

        if vb and self.truth is None and self.quantiles is None and self.histogram is None and self.samples is None:
            print 'Warning: initializing a PDF object without inputs'

        self.interpolator = None
        return

    def evaluate(self, loc, vb=True):
        """
        Evaluates the PDF (either the true version, or the most recent
        approximation of it) at the given location(s).
        Parameters
        ----------
        loc: float or ndarray
            location(s) at which to evaluate the pdf
        vb: boolean
            report on progress to stdout?
        Returns
        -------
        val: float or ndarray
            the value of the PDF (ot its approximation) at the requested location(s)
        Notes
        -----
        This function evaluates the truth function if it is available and the interpolated quantile approximation otherwise.
        """
        if self.truth is not None:
            if vb: print('Evaluating the true distribution.')
            val = self.truth.pdf(loc)
        else:
            if vb: print('Evaluating an interpolation of the '+self.last+' parametrization.')
            val = self.approximate(loc, using=self.last)[1]

        return(val)

    def integrate(self, limits):
        """
        Computes the integral under the PDF between the given limits.
        Parameters
        ----------
        limits: float, tuple
            limits of integration
        Returns
        -------
        integral: float
            value of the integral
        Notes
        -----
        This method is not yet operational, and returns `None`.
        """
        return None

    def quantize(self, quants=None, percent=1., number=None, infty=100., vb=True):
        """
        Computes an array of evenly-spaced quantiles from the truth.
        Parameters
        ----------
        quants: ndarray, float, optional
            array of quantile locations as decimals
        percent: float, optional
            the separation of the requested quantiles, in percent
        number: int, optional
            the number of quantiles to compute.
        infty: float, optional
            approximate value at which CDF=1.
        vb: boolean
            report on progress to stdout?
        Returns
        -------
        self.quantiles: ndarray, float
            the quantile points.
        Notes
        -----
        Quantiles of a PDF could be a useful approximate way to store it. This method computes the quantiles from a truth distribution (other representations forthcoming)
        and stores them in the `self.quantiles` attribute.
        Uses the `.ppf` method of the `rvs_continuous` distribution
        object stored in `self.truth`. This calculates the inverse CDF.
        See `the Scipy docs <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.rv_continuous.ppf.html#scipy.stats.rv_continuous.ppf>`_ for details.
        """
        if quants is not None:
            quantpoints = quants
        else:
            if number is not None:
                # Compute the spacing of the quantiles:
                quantum = 1.0 / float(number+1)
            else:
                quantum = percent/100.0
                # Over-write the number of quantiles:
                number = np.ceil(100.0 / percent) - 1
                assert number > 0
            quantpoints = np.linspace(0.0+quantum, 1.0-quantum, number)

        if vb: print("Calculating "+str(len(quantpoints))+" quantiles: ", quantpoints)
        if self.truth is not None:
            quantiles = self.truth.ppf(quantpoints)
        else:
            print('New quantiles can only be computed from a truth distribution in this version.')
            return

        if vb: print("Resulting "+str(len(quantiles))+" quantiles: ", quantiles)
        self.quantiles = (quantpoints, quantiles)
        print(np.shape(quantpoints), np.shape(quantiles))
        self.last = 'quantiles'
        return self.quantiles

    def histogramize(self, binends=None, nbins=10, binrange=[0., 1.], vb=True):
        """
        Computes the histogram values from the truth.
        Parameters
        ----------
        binends: ndarray, float, optional
            Array of N+1 endpoints of N bins
        nbins: int, optional
            Number of bins if no binends provided
        range: tuple, float, optional
            Pair of values of endpoints of total bin range
        vb: boolean
            Report on progress to stdout?
        Returns
        -------
        self.histogram: tuple of ndarrays of floats
            Pair of arrays of lengths (nbins+1, nbins) containing endpoints of bins and values in bins
        Comments
        --------
        A histogram representation of a PDF is a popular approximate way to store it. This method computes some histogram bin heights from a truth distribution (other representations forthcoming)
        and stores them in the `self.histogram` attribute.
        Uses the `.cdf` method of the `rvs_continuous` distribution
        object stored in `self.truth`. This calculates the CDF.
        See `the Scipy docs <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.rv_continuous.cdf.html#scipy.stats.rv_continuous.cdf>`_ for details.
        """
        if binends is None:
            step = float(binrange[1]-binrange[0])/nbins
            binends = np.arange(binrange[0], binrange[1]+step, step)

        nbins = len(binends)-1
        histogram = np.zeros(nbins)
        if vb: print("Calculating histogram: ", binends)
        if self.truth is not None:
            cdf = self.truth.cdf(binends)
            for b in range(nbins):
                histogram[b] = (cdf[b+1]-cdf[b])/(binends[b+1]-binends[b])
        else:
            print('New histograms can only be computed from a truth distribution in this version.')
            return

        if vb: print("Result: ", histogram)
        self.histogram = (binends, histogram)
        self.last = 'histogram'
        return self.histogram

    def sample(self, N=100, infty=100., using=None, vb=True):
        """
        Samples the pdf in given representation
        Parameters
        ----------
        N: int, optional
            number of samples to produce
        infty: float, optional
            approximate value at which CDF=1.
        using: string
            Parametrization on which to interpolate
        vb: boolean
            report on progress to stdout?
        Returns
        -------
        samples: ndarray
            array of sampled values
        """
        if using is None:
            using = self.last

        if vb: print("Sampling from "+using+' parametrization.')

        if using == 'truth':
            samples = self.truth.rvs(size=N)

        else:
            if using == 'quantiles':
                # First find the quantiles if none exist:
                if self.quantiles is None:
                    self.quantiles = self.quantize()

                endpoints = np.append(np.array([-1.*infty]), self.quantiles[1])
                endpoints = np.append(endpoints,np.array([infty]))
                weights = qp.utils.evaluate_quantiles(self.quantiles, infty=infty)[1]# self.evaluate((endpoints[1:]+endpoints[:-1])/2.)

            if using == 'histogram':
                # First find the histogram if none exists:
                if self.histogram is None:
                    self.histogram = self.histogramize()

                endpoints = self.histogram[0]
                weights = self.histogram[1]

            ncats = len(weights)
            cats = range(ncats)
            sampbins = [0]*ncats
            for item in range(N):
                sampbins[qp.utils.choice(cats, weights)] += 1
            samples = []*N
            for c in cats:
                for n in range(sampbins[c]):
                    samples.append(np.random.uniform(low=endpoints[c], high=endpoints[c+1]))

        if vb: print("Sampled values: ", samples)
        self.sampvals = self.evaluate(samples)
        self.samples = samples
        self.last = 'samples'
        return self.samples

    def interpolate(self, using=None, vb=True):
        """
        Constructs an `interpolator` function based on the parametrization.
        Parameters
        ----------
        using: string
            Parametrization on which to interpolate, currently supports 'quantiles', 'histogram'
        vb: boolean
            report on progress to stdout?
        Returns
        -------
        None
        Notes
        -----
        The `self.interpolator` object is a function that is used by the `approximate` method.
        """
        if using is None:
            using = self.last

        if using == 'truth':
            print('The truth needs no interpolation.  Try converting to an approximate parametrization first.')
            return

        if using == 'quantiles':
            # First find the quantiles if none exist:
            if self.quantiles is None:
                self.quantiles = self.quantize()

            (x, y) = qp.utils.evaluate_quantiles(self.quantiles)

        if using == 'histogram':
            # First find the histogram if none exists:
            if self.histogram is None:
                self.histogram = self.histogramize()

            (x, y) = qp.utils.evaluate_histogram(self.histogram)

        if using == 'samples':
            # First sample if not already done:
            if self.samples is None:
                self.samples = self.sample()

            (x, y) = qp.evaluate_samples(self.samples)

        if vb: print("Creating interpolator for "+using+' parametrization.')
        self.interpolator = spi.interp1d(x, y, fill_value="extrapolate")

        return

    def approximate(self, points, using=None, vb=True):
        """
        Interpolates the parametrization to get an approximation to the density.
        Parameters
        ----------
        number: int
            the number of points over which to interpolate, bounded by the quantile value endpoints
        points: ndarray
            the value(s) at which to evaluate the interpolated function
        using: string, optional
            approximation parametrization, currently either 'quantiles'
            or 'histogram'
        vb: boolean
            report on progress to stdout?
        Returns
        -------
        points: ndarray, float
            the input grid upon which to interpolate
        interpolated: ndarray, float
            the interpolated points.
        Notes
        -----
        Extrapolation is linear while values are positive; otherwise, extrapolation returns 0.
        Example::
            x, y = p.approximate(np.linspace(-1., 1., 100))
        """

        if self.interpolator is None:
            self.interpolate(using=using)
        interpolated = self.interpolator(points)
        interpolated[interpolated<0.] = 0.

        return (points, interpolated)

    def plot(self):
        """
        Plots the PDF, in various ways.

        Notes
        -----
        What this method plots depends on what information about the PDF is stored in it: the more properties the PDF has, the more exciting the plot!
        """
        extrema = [0., 0.]

        if self.truth is not None:
            min_x = self.truth.ppf(0.001)
            max_x = self.truth.ppf(0.999)
            x = np.linspace(min_x, max_x, 100)
            plt.plot(x, self.truth.pdf(x), color='k', linestyle='-', lw=1.0, alpha=1.0, label='True PDF')
            extrema = [min(extrema[0], min_x), max(extrema[1], max_x)]

        if self.quantiles is not None:
            plt.vlines(self.quantiles[1], np.zeros(len(self.quantiles[1])), self.evaluate(self.quantiles[1]), color='b', linestyle=':', lw=1.0, alpha=1., label='Quantiles')
            (grid, qinterpolated) = self.approximate(x, using='quantiles')
            plt.plot(grid, qinterpolated, color='b', lw=2.0, alpha=1.0, linestyle='--', label='Quantile Interpolated PDF')
            extrema = [min(extrema[0], self.quantiles[1][0]), max(extrema[1], self.quantiles[1][-1])]

        if self.histogram is not None:
            plt.hlines(self.histogram[1], self.histogram[0][:-1], self.histogram[0][1:], color='r', linestyle=':', lw=1.0, alpha=1., label='Histogram')
            (grid, hinterpolated) = self.approximate(x, using='histogram')
            plt.plot(grid, hinterpolated, color='r', lw=2.0, alpha=1.0, linestyle='--', label='Histogram Interpolated PDF')
            extrema = [min(extrema[0], self.histogram[0][0]), max(extrema[1], self.histogram[0][-1])]

        if self.samples is not None:
            plt.plot(self.samples, np.zeros(np.shape(self.samples)), 'g+', ms=20, label='Samples')
            (grid, sinterpolated) = self.approximate(x, using='samples')
            plt.plot(grid, sinterpolated, color='g', lw=2.0, alpha=1.0, linestyle='--', label='Samples Interpolated PDF')
            extrema = [min(extrema[0], min(self.samples)), max(extrema[1], max(self.samples))]

        plt.xlim(extrema[0], extrema[-1])
        plt.legend(fontsize='small')
        plt.xlabel('x')
        plt.ylabel('Probability density')
        plt.savefig('plot.png')

        return

    def kld(self, limits=(0., 1.), dx=0.01):
        """
        Calculates Kullback-Leibler divergence of quantile approximation from truth.
        Parameters
        ----------
        limits: tuple of floats
            endpoints of integration interval in which to calculate KLD
        dx: float
            resolution of integration grid
        Returns
        -------
        KL: float
            value of Kullback-Leibler divergence from approximation to truth if truth is available; otherwise nothing.
        Notes
        -----
        Example::
            d = p.kld(limits=(-1., 1.), dx=1./100))
        """

        if self.truth is None:
            print('Truth not available for comparison.')
            return
        else:
            KL = qp.utils.calculate_kl_divergence(self, self, limits=limits, dx=dx)
            return(KL)

    def rms(self, limits=(0., 1.), dx=0.01):
        """
        Calculates root mean square difference between quantile approximation and truth.
        Parameters
        ----------
        limits: tuple of floats
            endpoints of integration interval in which to calculate KLD
        dx: float
            resolution of integration grid
        Returns
        -------
        RMS: float
            value of root mean square difference between approximation of truth if truth is available; otherwise nothing.
        Notes
        -----
        Example::
            d = p.rms(limits=(-1., 1.), dx=1./100))
        """

        if self.truth is None:
            print('Truth not available for comparison.')
            return
        else:
            RMS = qp.utils.calculate_rms(self, self, limits=limits, dx=dx)
            return(RMS)
