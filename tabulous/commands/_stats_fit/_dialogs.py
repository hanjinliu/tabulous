from enum import Enum
from scipy import stats
from magicgui import magic_factory
from tabulous.widgets import TableBase, Table
from tabulous._selection_op import SelectionOperator


class Distributions(Enum):
    norm = "norm"
    expon = "expon"
    gamma = "gamma"
    beta = "beta"
    chi2 = "chi2"
    t = "t"
    f = "f"
    lognorm = "lognorm"
    poisson = "poisson"
    binom = "binom"
    boltzmann = "boltzmann"

    @property
    def dist(self) -> "stats.rv_continuous | stats.rv_discrete":
        """Get the distribution"""
        return getattr(stats, self.name)

    @property
    def params(self) -> tuple[str, ...]:
        """Get the parameters"""
        return _PARAM_NAMES[self]


_PARAM_NAMES = {
    Distributions.norm: ("loc", "scale"),
    Distributions.expon: ("loc", "scale"),
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


@magic_factory
def fit(
    table: TableBase,
    sel: SelectionOperator,
    distribution: Distributions = Distributions.norm,
    floc: str = "",
    fscale: str = "",
):
    import pandas as pd

    df = sel.operate(table.data)
    out: dict[str, tuple] = {}
    dist = distribution.dist

    kwargs = {}
    if floc:
        kwargs["floc"] = float(floc)
    if fscale:
        kwargs["fscale"] = float(fscale)

    for col in df.columns:
        d = dist.fit(df[col].values, **kwargs)
        out[col] = d

    df = pd.DataFrame(out, index=distribution.params)
    table.add_side_widget(
        Table(df, editable=False), name="Distribution Fitting Results"
    )
