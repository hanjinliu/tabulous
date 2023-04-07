from __future__ import annotations

from enum import Enum
from scipy import stats


class Distributions(Enum):
    """Choices of distributions"""

    norm = "Normal"
    expon = "Exponential"
    uniform = "Uniform"
    gamma = "Gamma"
    beta = "Beta"
    chi2 = "χ^2"
    t = "T"
    f = "F"
    lognorm = "log-Normal"
    poisson = "Poisson"
    binom = "Binomial"
    boltzmann = "Boltzmann"

    def __str__(self) -> str:
        return self.value

    @property
    def dist(self) -> stats.rv_continuous | stats.rv_discrete:
        """Get the distribution"""
        return getattr(stats, self.name)

    @property
    def params(self) -> tuple[str, ...]:
        """Get the parameters"""
        return _PARAM_NAMES[self]

    @property
    def latex(self) -> str:
        """Get the LaTeX formula"""
        return _LATEX_FORMULAS[self]


_PARAM_NAMES = {
    Distributions.norm: ("loc", "scale"),
    Distributions.expon: ("loc", "scale"),
    Distributions.uniform: ("loc", "scale"),
    Distributions.gamma: ("a", "loc", "scale"),
    Distributions.beta: ("a", "b", "loc", "scale"),
    Distributions.chi2: ("df", "loc", "scale"),
    Distributions.t: ("df", "loc", "scale"),
    Distributions.f: ("dfn", "dfd", "loc", "scale"),
    Distributions.lognorm: ("s", "loc", "scale"),
    Distributions.poisson: ("mu",),
    Distributions.binom: ("n", "p"),
    Distributions.boltzmann: ("T", "loc", "scale"),
}

# fmt: off
_LATEX_FORMULAS = {
    Distributions.norm: r"$f(x) = \frac{1}{\sqrt{2\pi\sigma^2}}\exp\left(-\frac{(x-\mu)^2}{2\sigma^2}\right)$",  # noqa: E501
    Distributions.expon: r"$f(x) = \lambda e^{-\lambda x}$",  # noqa: E501
    Distributions.uniform: r"$f(x) = \frac{1}{b-a}$",  # noqa: E501
    Distributions.gamma: r"$f(x) = \frac{x^{k-1}e^{-x/\theta}}{\theta^k\Gamma(k)}$",  # noqa: E501
    Distributions.beta: r"$f(x) = \frac{x^{a-1}(1-x)^{b-1}}{B(a,b)}$",  # noqa: E501
    Distributions.chi2: r"$f(x) = \frac{1}{2^{\nu/2}\Gamma(\nu/2)}x^{\nu/2-1}e^{-x/2}$",  # noqa: E501
    Distributions.t: r"$f(x) = \frac{\Gamma((\nu+1)/2)}{\sqrt{\pi\nu}\Gamma(\nu/2)}\left(1+\frac{x^2}{\nu}\right)^{-(\nu+1)/2}$",  # noqa: E501
    Distributions.f: r"$f(x) = \frac{(\nu_1 x)^{\nu_1}\nu_2^{\nu_2}}{\nu_1 x+\nu_2}\frac{\Gamma(\nu_1+\nu_2)}{\Gamma(\nu_1)\Gamma(\nu_2)}\frac{1}{x}$",  # noqa: E501
    Distributions.lognorm: r"$f(x) = \frac{1}{x\sigma\sqrt{2\pi}}\exp\left(-\frac{(\ln x-\mu)^2}{2\sigma^2}\right)$",  # noqa: E501
    Distributions.poisson: r"$f(x) = \frac{\lambda^k e^{-\lambda}}{k!}$",  # noqa: E501
    Distributions.binom: r"$f(x) = \binom{n}{k}p^k(1-p)^{n-k}$",  # noqa: E501
    Distributions.boltzmann: r"$f(x) = \frac{1}{Z}\exp\left(-\frac{x-\mu}{\theta}\right)\left(\frac{x-\mu}{\theta}\right)^{k-1}$",  # noqa: E501
}
# fmt: on
