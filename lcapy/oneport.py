"""
This module supports simple linear one-port networks based on the
following ideal components:

V independent voltage source
I independent current source
R resistor
C capacitor
L inductor

These components are converted to s-domain models and so capacitor and
inductor components can be specified with initial voltage and
currents, respectively, to model transient responses.

One-ports can either be connected in series (+) or parallel (|) to
create a new one-port.

Copyright 2014--2019 Michael Hayes, UCECE
"""

# TODO.   Rethink best way to handle impedances.   These can either be
# s-domain or omega domain (or DC as a special case where omega = 0).
# Perhaps alays use Current and Voltage and have these classes
# handle multiplication/division with admittances/impedances?



from __future__ import division
from .functions import Heaviside, cos, exp
from .symbols import j, t, s
from .network import Network
from .immitance import ImmitanceMixin
from .impedance import Impedance
from .admittance import Admittance


__all__ = ('V', 'I', 'v', 'i', 'R', 'L', 'C', 'G', 'Y', 'Z',
           'Vdc', 'Vstep', 'Idc', 'Istep', 'Vac', 'sV', 'sI',
           'Iac', 'Vnoise', 'Inoise', 
           'Par', 'Ser', 'Xtal', 'FerriteBead', 'CPE')

def _check_oneport_args(args):

    for arg1 in args:
        if not isinstance(arg1, OnePort):
            raise ValueError('%s not a OnePort' % arg1)


class OnePort(Network, ImmitanceMixin):
    """One-port network

    There are four major types of OnePort:
       VoltageSource
       CurrentSource
       Impedance
       Admittance
       ParSer for combinations of OnePort

    Attributes: Y, Z, Voc, Isc, y, z, voc, isc
      Y = Y(s)  admittance
      Z = Z(s)  impedance
      Voc       open-circuit voltage in appropriate transform domain
      Isc       short-circuit current in appropriate transform domain
      y = y(t)  impulse response of admittance
      z = z(t)  impulse response of impedance
      voc = voc(t) open-circuit voltage time response
      isc = isc(t) short-circuit current time response
    """

    # Dimensions and separations of component with horizontal orientation.
    height = 0.3
    hsep = 0.5
    width = 1
    wsep = 0.5

    _Z = None
    _Y = None
    _Voc = None
    _Isc = None

    @property
    def impedance(self):
        if self._Z is not None:
            return self._Z
        if self._Y is not None:
            return Impedance(1 / self._Y)
        if self._Voc is not None:        
            return Impedance(0)
        if self._Isc is not None:        
            return Impedance(1 / Admittance(0))
        raise ValueError('_Isc, _Voc, _Y, or _Z undefined for %s' % self)

    @property
    def admittance(self):
        if self._Y is not None:
            return self._Y
        return Admittance(1 / self.impedance)

    @property
    def Voc(self):
        """Open-circuit voltage."""        
        if self._Voc is not None:
            return self._Voc
        if self._Isc is not None:
            return self._Isc * self.impedance
        if self._Z is not None:        
            return Voltage(0)
        if self._Y is not None:        
            return Current(0)
        raise ValueError('_Isc, _Voc, _Y, or _Z undefined for %s' % self)
    
    @property
    def Isc(self):
        """Short-circuit current."""        
        if self._Isc is not None:
            return self._Isc
        return self.Voc / self.impedance

    @property
    def V(self):
        """Open-circuit voltage."""
        return self.Voc

    @property
    def I(self):
        """Open-circuit current.  Except for a current source this is zero."""
        return Current(0)

    @property
    def i(self):
        """Open-circuit time-domain current.  Except for a current source this
        is zero."""
        return self.I.time()

    def __add__(self, OP):
        """Series combination"""

        return Ser(self, OP)

    def __or__(self, OP):
        """Parallel combination"""

        return Par(self, OP)

    def series(self, OP):
        """Series combination"""

        return Ser(self, OP)

    def parallel(self, OP):
        """Parallel combination"""

        return Par(self, OP)

    def ladder(self, *args):
        """Create (unbalanced) ladder network"""

        return Ladder(self, *args)

    def lsection(self, OP2):
        """Create L section (voltage divider)"""

        if not issubclass(OP2.__class__, OnePort):
            raise TypeError('Argument not ', OnePort)

        return LSection(self, OP2)

    def tsection(self, OP2, OP3):
        """Create T section"""

        if not issubclass(OP2.__class__, OnePort):
            raise TypeError('Argument not ', OnePort)

        if not issubclass(OP3.__class__, OnePort):
            raise TypeError('Argument not ', OnePort)

        return TSection(self, OP2, OP3)

    def expand(self):

        return self

    def load(self, OP2):

        if not issubclass(OP2.__class__, OnePort):
            raise TypeError('Load argument not ', OnePort)

        return LoadCircuit(self, OP2)
    
    @property
    def voc(self):
        """Open-circuit time-domain voltage."""
        return self.Voc.time()

    @property
    def isc(self):
        """Short-circuit time-domain current."""        
        return self.Isc.time()

    @property
    def v(self):
        """Open-circuit time-domain voltage."""
        return self.voc

    @property
    def z(self):
        """Impedance impulse-response."""
        return self.impedance.time()

    @property
    def y(self):
        """Admittance impulse-response."""        
        return self.admittance.time()

    def thevenin(self):
        """Simplify to a Thevenin network"""

        new = self.simplify()
        Voc = new.Voc
        Z = new.impedance

        if Voc.is_superposition and not Z.is_real:
            print('Warning, detected superposition with reactive impedance,'
                  ' using s-domain.')
            Z1 = Z
            V1 = Voc.laplace()
        elif Voc.is_ac:
            Z1 = Z.subs(j * Voc.ac_keys()[0])
            V1 = Voc.select(Voc.ac_keys()[0])
        elif Voc.is_dc:
            Z1 = Z.subs(0)
            V1 = Voc(0)
        else:
            V1 = Voc
            Z1 = Z

        V1 = V1.cpt()
        Z1 = Z1.cpt()        

        if Voc == 0:
            return Z1
        if Z == 0:
            return V1

        return Ser(Z1, V1)

    def norton(self):
        """Simplify to a Norton network"""

        new = self.simplify()
        Isc = new.Isc
        Y = new.admittance
        
        if Isc.is_superposition and not Y.is_real:
            print('Warning, detected superposition with reactive impedance,'
                  ' using s-domain.')
            Y1 = Y
            I1 = Isc.laplace()
        elif Isc.is_ac:
            Y1 = Y.subs(j * Isc.ac_keys()[0])
            I1 = Isc.select(Isc.ac_keys()[0])
        elif Isc.is_dc:
            Y1 = Y.subs(0)
            I1 = Isc(0)
        else:
            I1 = Isc
            Y1 = Y

        I1 = I1.cpt()
        Y1 = Y1.cpt()        
            
        if Isc == 0:
            return Y1
        if Y == 0:
            return I1

        return Par(Y1, I1)

    def s_model(self):
        """Convert to s-domain."""

        if self._Voc is not None:
            if self._Voc == 0:
                return Z(self.impedance)
            Voc = self._Voc.laplace()
            if self.Z == 0:
                return V(Voc)
            return Ser(V(Voc), Z(self.impedance))
        elif self._Isc is not None:
            if self._Isc == 0:
                return Y(self.admittance)
            Isc = self._Isc.laplace()
            if self.admittance == 0:
                return I(Isc)
            return Par(I(Isc), Y(self.admittance))
        elif self._Z is not None:
            return Z(self._Z)
        elif self._Y is not None:
            return Y(self._Y)        
        raise ValueError('Internal error')

    def noise_model(self):
        """Convert to noise model."""

        from .symbols import omega

        if not isinstance(self, (R, G, Y, Z)):
            return self
        
        R1 = self.R
        if R1 != 0:
            Vn = Vnoise('sqrt(4 * k * T * %s)' % R1(j * omega))
            return self + Vn
        return self

    
class ParSer(OnePort):
    """Parallel/serial class"""

    def __str__(self):

        str = ''

        for m, arg in enumerate(self.args):
            argstr = arg.__str__()

            if isinstance(arg, ParSer) and arg.__class__ != self.__class__:
                argstr = '(' + argstr + ')'

            str += argstr

            if m != len(self.args) - 1:
                str += ' %s ' % self._operator

        return str

    def _repr_pretty_(self, p, cycle):

        p.text(self.pretty())

    def _repr_latex_(self):

        return '$%s$' % self.latex()

    def pretty(self):

        str = ''

        for m, arg in enumerate(self.args):
            argstr = arg.pretty()

            if isinstance(arg, ParSer) and arg.__class__ != self.__class__:
                argstr = '(' + argstr + ')'

            str += argstr

            if m != len(self.args) - 1:
                str += ' %s ' % self._operator

        return str

    def pprint(self):

        print(self.pretty())

    def latex(self):

        str = ''

        for m, arg in enumerate(self.args):
            argstr = arg.latex()

            if isinstance(arg, ParSer) and arg.__class__ != self.__class__:
                argstr = '(' + argstr + ')'

            str += argstr

            if m != len(self.args) - 1:
                str += ' %s ' % self._operator

        return str

    def _combine(self, arg1, arg2):

        if arg1.__class__ != arg2.__class__:
            if self.__class__ == Ser:
                if isinstance(arg1, V) and arg1.Voc == 0:
                    return arg2
                if isinstance(arg2, V) and arg2.Voc == 0:
                    return arg1
                if isinstance(arg1, (R, Z)) and arg1.impedance == 0:
                    return arg2
                if isinstance(arg2, (R, Z)) and arg2.impedance == 0:
                    return arg1
            if self.__class__ == Par:
                if isinstance(arg1, I) and arg1.Isc == 0:
                    return arg2
                if isinstance(arg2, I) and arg2.Isc == 0:
                    return arg1
                if isinstance(arg1, (Y, G)) and arg1.admittance == 0:
                    return arg2
                if isinstance(arg2, (Y, G)) and arg2.admittance == 0:
                    return arg1

            return None

        if self.__class__ == Ser:
            if isinstance(arg1, I):
                return None
            if isinstance(arg1, Vdc):
                return Vdc(arg1.v0 + arg2.v0)
            # Could simplify Vac here if same frequency
            if isinstance(arg1, V):
                return V(arg1 + arg2)
            if isinstance(arg1, R):
                return R(arg1._R + arg2._R)
            if isinstance(arg1, L):
                # The currents should be the same!
                if arg1.i0 != arg2.i0 or arg1.hasic != arg2.hasic:
                    raise ValueError('Series inductors with different'
                          ' initial currents!')
                i0 = arg1.i0 if arg1.hasic else None
                return L(arg1.L + arg2.L, i0)
            if isinstance(arg1, G):
                return G(arg1._G * arg2._G / (arg1._G + arg2._G))
            if isinstance(arg1, C):
                v0 = arg1.v0 + arg2.v0 if arg1.hasic or arg2.hasic else None
                return C(arg1.C * arg2.C / (arg1.C + arg2.C), v0)
            return None

        elif self.__class__ == Par:
            if isinstance(arg1, V):
                return None
            if isinstance(arg1, Idc):
                return Idc(arg1.i0 + arg2.i0)
            # Could simplify Iac here if same frequency
            if isinstance(arg1, I):
                return I(arg1 + arg2)
            if isinstance(arg1, G):
                return G(arg1._G + arg2._G)
            if isinstance(arg1, C):
                # The voltages should be the same!
                if arg1.v0 != arg2.v0 or arg1.hasic != arg2.hasic:
                    raise ValueError('Parallel capacitors with different'
                          ' initial voltages!')
                v0 = arg1.v0 if arg1.hasic else None
                return C(arg1.C + arg2.C, v0)
            if isinstance(arg1, R):
                return R(arg1._R * arg2._R / (arg1._R + arg2._R))
            if isinstance(arg1, L):
                i0 = arg1.i0 + arg2.i0 if arg1.hasic or arg2.hasic else None
                return L(arg1.L * arg2.L / (arg1.L + arg2.L), i0)
            return None

        else:
            raise TypeError('Undefined class')

    def simplify(self, deep=True):
        """Perform simple simplifications, such as parallel resistors,
        series inductors, etc., rather than collapsing to a Thevenin
        or Norton network.

        This does not expand compound components such as crystal
        or ferrite bead models.  Use expand() first.
        """

        # Simplify args (recursively) and combine operators if have
        # Par(Par(A, B), C) etc.
        new = False
        newargs = []
        for m, arg in enumerate(self.args):
            if isinstance(arg, ParSer):
                arg = arg.simplify(deep)
                new = True
                if arg.__class__ == self.__class__:
                    newargs.extend(arg.args)
                else:
                    newargs.append(arg)
            else:
                newargs.append(arg)

        if new:
            self = self.__class__(*newargs)

        # Scan arg list looking for compatible combinations.
        # Could special case the common case of two args.
        new = False
        args = list(self.args)
        for n in range(len(args)):

            arg1 = args[n]
            if arg1 is None:
                continue
            if isinstance(arg1, ParSer):
                continue

            for m in range(n + 1, len(args)):

                arg2 = args[m]
                if arg2 is None:
                    continue
                if isinstance(arg2, ParSer):
                    continue

                # TODO, think how to simplify things such as
                # Par(Ser(V1, R1), Ser(R2, V2)).
                # Could do Thevenin/Norton transformations.

                newarg = self._combine(arg1, arg2)
                if newarg is not None:
                    # print('Combining', arg1, arg2, 'to', newarg)
                    args[m] = None
                    arg1 = newarg
                    new = True

            args[n] = arg1

        if new:
            args = [arg for arg in args if arg is not None]
            if len(args) == 1:
                return args[0]
            self = self.__class__(*args)

        return self

    def expand(self):
        """Expand compound components such as crystals or ferrite bead
        models into R, L, G, C, V, I"""

        newargs = []
        for m, arg in enumerate(self.args):
            newarg = arg.expand()
            newargs.append(newarg)

        return self.__class__(*newargs)

    def s_model(self):
        """Convert to s-domain."""
        args = [arg.s_model() for arg in self.args]
        return (self.__class__(*args))

    def noise_model(self):
        """Convert to noise model."""
        args = [arg.noise_model() for arg in self.args]
        return (self.__class__(*args))

    @property
    def Isc(self):
        return self.cct.Isc(1, 0)

    @property
    def Voc(self):
        return self.cct.Voc(1, 0)


class Par(ParSer):
    """Parallel class"""

    _operator = '|'

    def __init__(self, *args):

        _check_oneport_args(args)
        super(Par, self).__init__()
        self.args = args

        for n, arg1 in enumerate(self.args):
            for arg2 in self.args[n + 1:]:
                if isinstance(arg1, V) and isinstance(arg2, V):
                    raise ValueError('Voltage sources connected in parallel'
                                     ' %s and %s' % (arg1, arg2))
                elif isinstance(arg1, V):
                    print('Warn: redundant component %s in parallel with voltage source %s' % (arg2, arg1))

                elif isinstance(arg2, V):
                    print('Warn: redundant component %s in parallel with voltage source %s' % (arg1, arg2))


    @property
    def width(self):

        total = 0
        for arg in self.args:
            val = arg.width
            if val > total:
                total = val
        return total + 2 * self.wsep

    @property
    def height(self):

        total = 0
        for arg in self.args:
            total += arg.height
        return total + (len(self.args) - 1) * self.hsep

    def net_make(self, net, n1=None, n2=None):

        s = []
        if n1 is None:
            n1 = net.node
        n3, n4 =  net.node, net.node

        H = [(arg.height + self.hsep) * 0.5 for arg in self.args]
        
        N = len(H)
        num_branches = N // 2

        # Draw component in centre if have odd number in parallel.
        if (N & 1):
            s.append(self.args[N // 2].net_make(net, n3, n4))

        na, nb = n3, n4

        s.append('W %s %s; right=%s' % (n1, n3, self.wsep))

        # Draw components above centre
        for n in range(num_branches):

            if not (N & 1) and n == 0:
                sep = H[N // 2 - 1]
            else:
                sep = H[N // 2 - n] + H[N // 2 - 1 - n]

            nc, nd =  net.node, net.node
            s.append('W %s %s; up=%s' % (na, nc, sep))
            s.append('W %s %s; up=%s' % (nb, nd, sep))
            s.append(self.args[N // 2 - 1 - n].net_make(net, nc, nd))
            na, nb = nc, nd

        na, nb = n3, n4

        # Draw components below centre
        for n in range(num_branches):

            if not (N & 1) and n == 0:
                sep = H[(N + 1) // 2]
            else:
                sep = H[(N + 1) // 2 + n] + H[(N + 1) // 2 - 1 + n]

            nc, nd =  net.node, net.node
            s.append('W %s %s; down=%s' % (na, nc, sep))
            s.append('W %s %s; down=%s' % (nb, nd, sep))
            s.append(self.args[(N + 1) // 2 + n].net_make(net, nc, nd))
            na, nb = nc, nd

        if n2 is None:
            n2 = net.node

        s.append('W %s %s; right=%s' % (n4, n2, self.wsep))
        return '\n'.join(s)

    @property
    def admittance(self):
        Y = 0
        for arg in self.args:
            Y += arg.admittance
        return Admittance(Y)

    @property
    def impedance(self):
        return Impedance(1 / self.admittance)

class Ser(ParSer):
    """Series class"""

    _operator = '+'

    def __init__(self, *args):

        _check_oneport_args(args)
        super(Ser, self).__init__()
        self.args = args

        for n, arg1 in enumerate(self.args):
            for arg2 in self.args[n + 1:]:
                if isinstance(arg1, I) and isinstance(arg2, I):
                    raise ValueError('Current sources connected in series'
                                     ' %s and %s' % (arg1, arg2))
                elif isinstance(arg1, I):
                    print('Warn: redundant component %s in series with current source %s' % (arg2, arg1))

                elif isinstance(arg2, I):
                    print('Warn: redundant component %s in series with current source %s' % (arg1, arg2))                    

    @property
    def height(self):

        total = 0
        for arg in self.args:
            val = arg.height
            if val > total:
                total = val
        return total

    @property
    def width(self):

        total = 0
        for arg in self.args:
            total += arg.width
        return total + (len(self.args) - 1) * self.wsep

    def net_make(self, net, n1=None, n2=None):

        s = []
        if n1 is None:
            n1 = net.node
        for arg in self.args[:-1]:
            n3 = net.node
            s.append(arg.net_make(net, n1, n3))
            n1 = net.node
            s.append('W %s %s; right=%s' % (n3, n1, self.wsep))

        if n2 is None:
            n2 = net.node
        s.append(self.args[-1].net_make(net, n1, n2))
        return '\n'.join(s)

    @property
    def Admittance(self):
        return Admittance(1 / self.impedance)
    
    @property
    def impedance(self):
        Z = 0
        for arg in self.args:
            Z += arg.impedance
        return Impedance(Z)

    
class R(OnePort):
    """Resistor"""

    def __init__(self, Rval):

        self.args = (Rval, )
        self._R = cExpr(Rval)
        self._Z = Impedance(self._R)


class G(OnePort):
    """Conductance"""

    def __init__(self, Gval):

        self.args = (Gval, )
        self._G = cExpr(Gval)
        self._Z = 1 / Admittance(self._G)

    def net_make(self, net, n1=None, n2=None):

        if n1 == None:
            n1 = net.node
        if n2 == None:
            n2 = net.node
        return 'R %s %s {%s}; right' % (n1, n2, 1 / self._G)


class L(OnePort):
    """Inductor

    Inductance Lval, initial current i0"""

    def __init__(self, Lval, i0=None):

        self.hasic = i0 is not None
        if i0 is None:
            i0 = 0

        if self.hasic:
            self.args = (Lval, i0)
        else:
            self.args = (Lval, )

        Lval = cExpr(Lval)
        i0 = cExpr(i0)
        self.L = Lval
        self.i0 = i0
        self._Z = Impedance(s * Lval)
        self._Voc = Voltage(-Vs(i0 * Lval))
        self.zeroic = self.i0 == 0 


class C(OnePort):
    """Capacitor

    Capacitance Cval, initial voltage v0"""

    def __init__(self, Cval, v0=None):

        self.hasic = v0 is not None
        if v0 is None:
            v0 = 0

        if self.hasic:
            self.args = (Cval, v0)
        else:
            self.args = (Cval, )

        Cval = cExpr(Cval)
        v0 = cExpr(v0)
        self.C = Cval
        self.v0 = v0
        self._Z = Impedance(1 / (s * Cval))
        self._Voc = Voltage(Vs(v0) / s)
        self.zeroic = self.v0 == 0


class CPE(OnePort):
    """Constant phase element

    This has an impedance 1 / (s**alpha * K).  When alpha == 0, the CPE is
    equivalent to a resistor of resistance 1 / K.  When alpha == 1, the CPE is
    equivalent to a capacitor of capacitance K.

    When alpha == 0.5 (default), the CPE is a Warburg element.

    The phase of the impedance is -pi * alpha / 2.

    Note, when alpha is non-integral, the impedance cannot be represented
    as a rational function and so there are no poles or zeros.  So
    don't be suprised if Lcapy throws an occasional wobbly."""

    def __init__(self, K, alpha=0.5):

        self.args = (K, alpha)

        K = cExpr(K)
        alpha = cExpr(alpha)
        self.K = K
        self.alpha = alpha
        self._Z = Impedance(1 / (s ** alpha * K))


class Y(OnePort):
    """General admittance."""

    def __init__(self, Yval):

        self.args = (Yval, )
        Yval = Admittance(Yval)
        self._Z = 1 / Yval


class Z(OnePort):
    """General impedance."""

    def __init__(self, Zval):

        self.args = (Zval, )
        Zval = Impedance(Zval)
        self._Z = Zval


class VoltageSource(OnePort):

    voltage_source = True
    netname = 'V'
    is_noisy = False


class sV(VoltageSource):
    """Arbitrary s-domain voltage source"""

    netkeyword = 's'

    def __init__(self, Vval):

        self.args = (Vval, )
        Vval = sExpr(Vval)
        self._Voc = Voltage(Vs(Vval))


class V(VoltageSource):
    """Arbitrary voltage source"""

    def __init__(self, Vval):

        self.args = (Vval, )
        self._Voc = Voltage(Vval)

        
class Vstep(VoltageSource):
    """Step voltage source (s domain voltage of v / s)."""

    netkeyword = 'step'

    def __init__(self, v):

        self.args = (v, )
        v = cExpr(v)
        self._Voc = Voltage(tExpr(v) * Heaviside(t))
        self.v0 = v


class Vdc(VoltageSource):
    """DC voltage source (note a DC voltage source of voltage V has
    an s domain voltage of V / s)."""

    netkeyword = 'dc'
    
    def __init__(self, v):

        self.args = (v, )
        v = cExpr(v)
        self._Voc = Voltage(Vconst(v, dc=True))
        self.v0 = v

    @property
    def voc(self):
        return self.v0


class Vac(VoltageSource):
    """AC voltage source."""

    netkeyword = 'ac'

    def __init__(self, V, phi=None, omega=None):

        if phi is None and omega is None:
            self.args = (V, )
        elif phi is not None and omega is None:
            self.args = (V, phi)
        elif phi is None and omega is not None:
            self.args = (V, 0, omega)            
        else:
            self.args = (V, phi, omega)            

        if phi is None:
            phi = 0
            
        if omega is None:
            from .symbols import omega
        else:
            omega = Expr(omega)

        V = Expr(V)
        phi = Expr(phi)

        # Note, cos(-pi / 2) is not quite zero.

        self.omega = omega
        self.v0 = V
        self.phi = phi
        self._Voc = Voltage(Vphasor(self.v0 * exp(j * self.phi),
                                   ac=True, omega=self.omega))

    @property
    def voc(self):
        return self.v0 * cos(self.omega * t + self.phi)


class Vnoise(VoltageSource):
    """Noise voltage source."""

    netkeyword = 'noise'
    is_noisy = True

    def __init__(self, V, nid=None):

        V1 = Vn(V, nid=nid)
        self.args = (V, V1.nid)
        self._Voc = Voltage(V1)

        
class v(VoltageSource):
    """Arbitrary t-domain voltage source"""

    def __init__(self, vval):

        self.args = (vval, )
        Vval = tExpr(vval)
        self._Voc = Voltage(Vval)


class CurrentSource(OnePort):

    current_source = True
    netname = 'I'
    is_noisy = False    

    @property
    def I(self):
        """Open-circuit current of a current source.  To achieve this the
        open-circuit voltage needs to be infinite."""
        return self.Isc
    
    
class sI(CurrentSource):
    """Arbitrary s-domain current source"""

    netkeyword = 's'

    def __init__(self, Ival):

        self.args = (Ival, )
        Ival = sExpr(Ival)
        self._Isc = Current(Is(Ival))


class I(CurrentSource):
    """Arbitrary current source"""

    def __init__(self, Ival):

        self.args = (Ival, )
        self._Isc = Current(Ival)

            
class Istep(CurrentSource):
    """Step current source (s domain current of i / s)."""

    netkeyword = 'step'

    def __init__(self, i):

        self.args = (i, )
        i = cExpr(i)
        self._Isc = Current(tExpr(i) * Heaviside(t))
        self.i0 = i


class Idc(CurrentSource):
    """DC current source (note a DC current source of current i has
    an s domain current of i / s)."""

    netkeyword = 'dc'
    
    def __init__(self, i):

        self.args = (i, )
        i = cExpr(i)
        self._Isc = Current(Iconst(i, dc=True))
        self.i0 = i

    @property
    def isc(self):
        return self.i0


class Iac(CurrentSource):
    """AC current source."""

    netkeyword = 'ac'

    def __init__(self, I, phi=0, omega=None):

        if phi is None and omega is None:
            self.args = (I, )
        elif phi is not None and omega is None:
            self.args = (I, phi)
        elif phi is None and omega is not None:
            self.args = (I, 0, omega)            
        else:
            self.args = (I, phi, omega)            

        if phi is None:
            phi = 0
            
        if omega is None:
            from .symbols import omega            
        else:
            omega = Expr(omega)

        I = Expr(I)
        phi = Expr(phi)

        self.omega = omega
        self.i0 = I
        self.phi = phi
        self._Isc = Current(Iphasor(self.i0 * exp(j * self.phi),
                                   ac=True, omega=self.omega))

    @property
    def isc(self):
        return self.i0 * cos(self.omega * t + self.phi)


class Inoise(CurrentSource):
    """Noise current source."""

    netkeyword = 'noise'
    is_noisy = True

    def __init__(self, I, nid=None):

        I1 = In(I, nid=nid)
        self._Isc = Current(I1)
        self.args = (I, I1.nid)

        
class i(CurrentSource):
    """Arbitrary t-domain current source"""

    def __init__(self, ival):

        self.args = (ival, )
        Ival = tExpr(ival)
        self._Isc = Current(Ival)


class Xtal(OnePort):
    """Crystal

    This is modelled as a series R, L, C circuit in parallel
    with C0 (a Butterworth van Dyke model).  Note,
    harmonic resonances are not modelled.
    """

    def __init__(self, C0, R1, L1, C1):

        self.C0 = cExpr(C0)
        self.R1 = cExpr(R1)
        self.L1 = cExpr(L1)
        self.C1 = cExpr(C1)

        self._Z = self.expand().impedance
        self.args = (C0, R1, L1, C1)

    def expand(self):

        return (R(self.R1) + L(self.L1) + C(self.C1)) | C(self.C0)

    def net_make(self, net, n1=None, n2=None):

        # TODO: draw this with a symbol
        net = self.expand()
        return net.net_make(net, n1, n2)    


class FerriteBead(OnePort):
    """Ferrite bead (lossy inductor)

    This is modelled as a series resistor (Rs) connected
    to a parallel R, L, C network (Rp, Lp, Cp).
    """

    def __init__(self, Rs, Rp, Cp, Lp):

        self.Rs = cExpr(Rs)
        self.Rp = cExpr(Rp)
        self.Cp = cExpr(Cp)
        self.Lp = cExpr(Lp)

        self._Z = self.expand().impedance
        self.args = (Rs, Rp, Cp, Lp)

    def expand(self):

        return R(self.Rs) + (R(self.Rp) + L(self.Lp) + C(self.Cp))

    def net_make(self, net, n1=None, n2=None):

        # TODO: draw this with a symbol
        net = self.expand()
        return net.net_make(net, n1, n2)            
    
class LoadCircuit(Network):
    """Circuit comprised of a load oneport connected in parallel with a
    source oneport."""

    def __init__(self, source_OP, load_OP):

        self.source_OP = source_OP
        self.load_OP = load_OP

        self.vnet = source_OP | load_OP
        self.inet = source_OP + load_OP
        self.args = (source_OP, load_OP)

    @property
    def V(self):
        """Voltage across load."""
        return self.vnet.Voc

    @property
    def v(self):
        """Time-domain voltage across load."""
        return self.vnet.voc

    @property
    def I(self):
        """Current into load."""
        return self.inet.Isc

    @property
    def i(self):
        """Time-domain current into load."""
        return self.inet.isc

    def net_make(self, net, n1=None, n2=None):

        # TODO: draw this better rather than as a oneport.
        return self.vnet.net_make(self.vnet, n1, n2)


class ControlledSource(OnePort):
    """These components are controlled one-ports."""
    pass


class CCVS(ControlledSource):

    def __init__(self, control, value):

        self.args = (control, value)        
        self._Voc = Voltage(0)
        self._Z = Impedance(0)

        
class CCCS(ControlledSource):

    def __init__(self, control, value):

        self.args = (control, value)        
        self._Isc = Current(0)
        self._Y = Admittance(0)     

        
class VCVS(ControlledSource):

    def __init__(self, value):

        self.args = (value, )        
        self._Voc = Voltage(0)
        self._Z = Impedance(0)

        
class VCCS(ControlledSource):

    def __init__(self, value):

        self.args = (value, )
        self._Isc = Current(0)
        self._Y = Admittance(0)     
        

class Dummy(OnePort):
    pass


class W(Dummy):
    """Wire (short)"""

    def __init__(self):

        self.args = ()
        self._Z = Impedance(0)

        
class O(Dummy):
    """Open circuit"""

    def __init__(self):

        self.args = ()
        self._Y = Admittance(0)

        
class P(O):
    """Port (open circuit)"""
    pass



        
    
# Imports at end to circumvent circular dependencies
from .expr import Expr
from .cexpr import cExpr, Iconst, Vconst
from .sexpr import sExpr, Is, Vs, Ys, Zs
from .texpr import tExpr
from .noiseexpr import In, Vn
from .voltage import Voltage
from .current import Current
from .phasor import Iphasor, Vphasor
from .twoport import Ladder, LSection, TSection

