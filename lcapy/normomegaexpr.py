"""This module provides the NormAngularFourierDomainExpression class
to represent Omega-domain (normalised angular Fourier domain)
expressions.

Copyright 2021 Michael Hayes, UCECE

"""

from __future__ import division
from .domains import NormAngularFourierDomain
from .inverse_fourier import inverse_fourier_transform
from .inverse_dtft import IDTFT
from .expr import Expr, expr, expr_make
from .fexpr import f
from .sym import ssym, tsym, fsym, pi
from .dsym import Omegasym, nsym, dt
from .units import u as uu
from .utils import factor_const, remove_images
from sympy import Integral, Expr as symExpr

class NormAngularFourierDomainExpression(NormAngularFourierDomain, Expr):

    """Normalised angular Fourier domain expression or symbol."""

    var = Omegasym

    def __init__(self, val, **assumptions):

        check = assumptions.pop('check', True)        
        assumptions['real'] = True
        super(NormAngularFourierDomainExpression, self).__init__(val, **assumptions)

        expr = self.expr        
        if check and expr.find(ssym) != set() and not expr.has(Integral):

            raise ValueError(
                'Omega-domain expression %s cannot depend on s' % expr)
        if check and expr.find(tsym) != set() and not expr.has(Integral):
            raise ValueError(
                'Omega-domain expression %s cannot depend on t' % expr)

    def as_expr(self):
        return NormAngularFourierDomainExpression(self)

    def inverse_fourier(self, evaluate=True, **assumptions):
        """Attempt inverse Fourier transform."""

        expr = self.subs(2 * pi * fsym * dt)        
        result = inverse_fourier_transform(expr, fsym, tsym, evaluate=evaluate)

        return self.change(result, 'time', units_scale=uu.Hz, **assumptions)

    def IFT(self, evaluate=True, **assumptions):
        """Convert to time domain.  This is an alias for inverse_fourier."""

        return self.inverse_fourier(evaluate=evaluate, **assumptions)

    def IDTFT(self, var=None, evaluate=True, **assumptions):
        """Convert to discrete-time domain using inverse discrete-time
        Fourier transform."""

        foo = self.subs(2 * pi * f * dt)
        result = IDTFT(foo.expr, self.var, nsym, evaluate=evaluate)

        return self.change(result, 'discrete time', units_scale=uu.Hz,
                           **assumptions)

    def time(self, **assumptions):
        return self.inverse_fourier(**assumptions)

    def angular_fourier(self, **assumptions):
        """Convert to angular Fourier domain."""
        from .symbols import omega
        
        result = self.subs(omega / dt)
        return result
    
    def norm_fourier(self, **assumptions):
        """Convert to normalised Fourier domain."""
        from .symbols import F
        from .dsym import dt
        
        result = self.subs(2 * pi * F / dt)
        return result

    def norm_angular_fourier(self, **assumptions):
        """Convert to normalised angular Fourier domain."""

        return self

    def laplace(self, **assumptions):
        """Determine one-side Laplace transform with 0- as the lower limit."""

        result = self.time(**assumptions).laplace()
        return result
    
    def phasor(self, **assumptions):
        """Convert to phasor domain."""

        return self.time(**assumptions).phasor(**assumptions)        

    def plot(self, Wvector=None, plot_type=None, **kwargs):
        """Plot frequency response at values specified by `Wvector`.

        If `Wvector` is a tuple, this sets the frequency limits.

        `plot_type` - 'dB-phase', 'dB-phase-degrees', 'mag-phase',
        'mag-phase-degrees', 'real-imag', 'mag', 'phase',
        'phase-degrees', 'real', or 'imag'.

        The default `plot_type` for complex data is `dB-phase`.

        `kwargs` include:
        `axes` - the plot axes to use otherwise a new figure is created
        `xlabel` - the x-axis label
        `ylabel` - the y-axis label
        `ylabel2` - the second y-axis label if needed, say for mag and phase
        `xscale` - the x-axis scaling, say for plotting as ms
        `yscale` - the y-axis scaling, say for plotting mV
        `norm` - use normalised frequency
        in addition to those supported by the matplotlib plot command.
        
        The plot axes are returned.  This is a tuple for magnitude/phase or
        real/imaginary plots.

        There are many plotting options, see lcapy.plot and
        matplotlib.pyplot.plot.

        For example:
            V.plot(Wvector, log_frequency=True)
            V.real.plot(Wvector, color='black')
            V.phase.plot(Wvector, color='black', linestyle='--')

        By default complex data is plotted as separate plots of
        magnitude (dB) and phase.

        """

        from .plot import plot_angular_frequency
        return plot_angular_frequency(self, Wvector, plot_type=plot_type,
                                      norm=True, **kwargs)

    def remove_images(self):
        """Remove all the spectral images resulting from a DTFT.
        
        For example,

        >>> x = Sum(DiracDelta(Omega - m * 2 * pi), (m, -oo, oo))
        >>> x.remove_images()
        DiracDelta(Omega)
        """

        result = remove_images(self.expr, self.var, dt)
        return self.__class__(result, **self.assumptions)

    
def Omegaexpr(arg, **assumptions):
    """Create NormAngularFourierDomainExpression object. 
    If `arg` is Omegasym return Omega"""

    if arg is Omegasym:
        return Omega
    return expr_make('fourier', arg, **assumptions)

from .expressionclasses import expressionclasses

classes = expressionclasses.register('norm angular fourier',
                                     NormAngularFourierDomainExpression)

Omega = NormAngularFourierDomainExpression('Omega')
Omega.units = uu.rad