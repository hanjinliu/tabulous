from functools import partial
from typing import Union
from typing_extensions import Annotated, Literal
from sklearn import cluster, svm, linear_model, decomposition
from sklearn.mixture import GaussianMixture


class ModelRegistry(dict):
    def register(self, name: str):
        def _wrapper(cls):
            self[name] = cls
            return cls

        return _wrapper


MODELS = ModelRegistry()


def _normalize_random_state(state) -> Union[int, None]:
    if state:
        return int(state)
    else:
        return None


# Model factories
_AffinityType = Literal["euclidean", "l1", "l2", "manhattan", "cosine", "precomputed"]
_BoolOrAuto = Literal["auto", "true", "false"]


@MODELS.register("k-means")
def kmeans(
    n_clusters: int = 8,
    init: Literal["k-means++", "random"] = "k-means++",
    n_init: Annotated[int, {"min": 1, "max": 100}] = 10,
    max_iter: Annotated[int, {"min": 1, "max": 10000}] = 300,
    tol: str = "1e-4",
    random_state: str = "",
):
    random_state = _normalize_random_state(random_state)
    tol = float(tol)
    return cluster.KMeans(
        n_clusters=n_clusters,
        init=init,
        n_init=n_init,
        max_iter=max_iter,
        tol=tol,
        random_state=random_state,
    )


@MODELS.register("DBSCAN")
def dbscan(
    eps: Annotated[float, {"min": 0.0, "max": 1000.0}] = 0.5,
    min_samples: Annotated[int, {"min": 1, "max": 100}] = 5,
    metric: str = "euclidean",
    algorithm: Literal["auto", "ball_tree", "kd_tree", "brute"] = "auto",
    leaf_size: Annotated[int, {"min": 1, "max": 100}] = 30,
    p: Annotated[int, {"min": 1, "max": 100}] = 2,
    n_jobs: Annotated[int, {"min": 1, "max": 100}] = None,
):
    return cluster.DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric=metric,
        algorithm=algorithm,
        leaf_size=leaf_size,
        p=p,
        n_jobs=n_jobs,
    )


@MODELS.register("Agglomerative")
def agglomerative(
    n_clusters: Annotated[int, {"min": 1, "max": 100}] = 2,
    affinity: _AffinityType = "euclidean",
    compute_full_tree: _BoolOrAuto = "auto",
    linkage: Literal["ward", "complete", "average", "single"] = "ward",
):
    return cluster.AgglomerativeClustering(
        n_clusters=n_clusters,
        affinity=affinity,
        compute_full_tree=compute_full_tree,
        linkage=linkage,
    )


@MODELS.register("OPTICS")
def optics(
    min_samples: Annotated[int, {"min": 1, "max": 100}] = 5,
    max_eps: str = "inf",
    metric: str = "minkowski",
    algorithm: Literal["auto", "ball_tree", "kd_tree", "brute"] = "auto",
    leaf_size: Annotated[int, {"min": 1, "max": 100}] = 30,
    p: Annotated[int, {"min": 1, "max": 100}] = 2,
    n_jobs: Annotated[int, {"min": 1, "max": 100}] = None,
):
    max_eps = float(max_eps)
    return cluster.OPTICS(
        min_samples=min_samples,
        max_eps=max_eps,
        metric=metric,
        algorithm=algorithm,
        leaf_size=leaf_size,
        p=p,
        n_jobs=n_jobs,
    )


@MODELS.register("Spectral")
def spectral(
    n_clusters: Annotated[int, {"min": 1, "max": 100}] = 8,
    eigen_solver: Literal["arpack", "lobpcg", "amg"] = "arpack",
    random_state: str = "",
    n_init: Annotated[int, {"min": 1, "max": 100}] = 10,
    gamma: Annotated[float, {"min": 0.0, "max": 100.0}] = 1.0,
    affinity: Literal["nearest_neighbors", "rbf"] = "rbf",
    n_neighbors: Annotated[int, {"min": 1, "max": 100}] = 10,
    eigen_tol: Annotated[float, {"min": 0.0, "max": 100.0}] = 0.0,
    assign_labels: Literal["kmeans", "discretize"] = "kmeans",
    degree: float = 3,
    coef0: float = 1,
):
    random_state = _normalize_random_state(random_state)
    return cluster.SpectralClustering(
        n_clusters=n_clusters,
        eigen_solver=eigen_solver,
        random_state=random_state,
        n_init=n_init,
        gamma=gamma,
        affinity=affinity,
        n_neighbors=n_neighbors,
        eigen_tol=eigen_tol,
        assign_labels=assign_labels,
        degree=degree,
        coef0=coef0,
    )


@MODELS.register("Affinity propagation")
def affinity_propagation(
    damping: Annotated[float, {"min": 0.5, "max": 1.0, "step": 0.01}] = 0.5,
    max_iter: Annotated[int, {"min": 1, "max": 10000}] = 200,
    convergence_iter: Annotated[int, {"min": 1, "max": 10000}] = 15,
    affinity: _AffinityType = "euclidean",
):
    return cluster.AffinityPropagation(
        damping=damping,
        max_iter=max_iter,
        convergence_iter=convergence_iter,
        affinity=affinity,
    )


@MODELS.register("Birch")
def birch(
    n_clusters: Annotated[int, {"min": 1, "max": 100}] = 3,
    threshold: Annotated[float, {"min": 0.0, "max": 100.0}] = 0.5,
    branching_factor: Annotated[int, {"min": 1, "max": 100}] = 50,
    compute_labels: _BoolOrAuto = "auto",
):
    return cluster.Birch(
        n_clusters=n_clusters,
        threshold=threshold,
        branching_factor=branching_factor,
        compute_labels=compute_labels,
    )


@MODELS.register("Mean shift")
def mean_shift(
    bandwidth: Annotated[float, {"min": 0.0, "max": 100.0}] = None,
    bin_seeding: bool = False,
    min_bin_freq: Annotated[int, {"min": 1, "max": 100}] = 1,
    cluster_all: bool = True,
):
    return cluster.MeanShift(
        bandwidth=bandwidth,
        bin_seeding=bin_seeding,
        min_bin_freq=min_bin_freq,
        cluster_all=cluster_all,
    )


@MODELS.register("Gaussian mixture")
def gaussian_mixture(
    n_components: Annotated[int, {"min": 1, "max": 100}] = 1,
    covariance_type: Literal["full", "tied", "diag", "spherical"] = "full",
    tol: str = "1e-3",
    reg_covar: Annotated[float, {"min": 0.0, "max": 100.0}] = 1e-6,
    max_iter: Annotated[int, {"min": 1, "max": 1000}] = 100,
    n_init: Annotated[int, {"min": 1, "max": 100}] = 1,
    init_params: Literal["kmeans", "random"] = "kmeans",
    random_state: str = "",
):
    random_state = _normalize_random_state(random_state)
    tol = float(tol)
    return GaussianMixture(
        n_components=n_components,
        covariance_type=covariance_type,
        tol=tol,
        reg_covar=reg_covar,
        max_iter=max_iter,
        n_init=n_init,
        init_params=init_params,
        random_state=random_state,
    )


_SvmKernels = Literal["linear", "poly", "rbf", "sigmoid", "precomputed"]


@MODELS.register("SVC")
def svc(
    C: Annotated[float, {"min": 0.0, "max": 100.0}] = 1.0,
    kernel: _SvmKernels = "rbf",
    degree: Annotated[int, {"min": 1, "max": 100}] = 3,
    # gamma: _GammaType = "scale",
    coef0: Annotated[float, {"min": 0.0, "max": 100.0}] = 0.0,
    shrinking: bool = True,
    probability: bool = False,
    tol: str = "1e-3",
    cache_size: Annotated[int, {"min": 1, "max": 1000}] = 200,
    random_state: str = "",
    regression: bool = False,
):
    random_state = _normalize_random_state(random_state)
    if regression:
        svm_cls = svm.SVR
    else:
        svm_cls = svm.SVC
    return svm_cls(
        C=C,
        kernel=kernel,
        degree=degree,
        # gamma=gamma,
        coef0=coef0,
        shrinking=shrinking,
        probability=probability,
        tol=float(tol),
        cache_size=cache_size,
        random_state=random_state,
    )


@MODELS.register("Nu-SVC")
def nusvc(
    nu: Annotated[float, {"min": 0.0, "max": 1.0}] = 0.5,
    kernel: _SvmKernels = "rbf",
    degree: Annotated[int, {"min": 1, "max": 100}] = 3,
    # gamma: _GammaType = "scale",
    coef0: Annotated[float, {"min": 0.0, "max": 100.0}] = 0.0,
    shrinking: bool = True,
    tol: str = "1e-3",
    cache_size: Annotated[int, {"min": 1, "max": 100}] = 200,
    random_state: str = "",
    regression: bool = False,
):
    random_state = _normalize_random_state(random_state)
    if regression:
        svm_cls = svm.NuSVR
    else:
        svm_cls = svm.NuSVC
    return svm_cls(
        nu=nu,
        kernel=kernel,
        degree=degree,
        # gamma=gamma,
        coef0=coef0,
        shrinking=shrinking,
        tol=float(tol),
        cache_size=cache_size,
        random_state=random_state,
    )


@MODELS.register("Linear-SVC")
def linear_svc(
    penalty: Literal["l1", "l2"] = "l2",
    dual: bool = True,
    tol: str = "1e-4",
    C: Annotated[float, {"min": 0.0, "max": 100.0}] = 1.0,
    multi_class: Literal["ovr", "crammer_singer"] = "ovr",
    fit_intercept: bool = True,
    intercept_scaling: Annotated[float, {"min": 0.0, "max": 100.0}] = 1,
    random_state: str = "",
    max_iter: Annotated[int, {"min": 1, "max": 10000}] = 1000,
    regression: bool = False,
):
    random_state = _normalize_random_state(random_state)
    if regression:
        if penalty == "l1":
            loss = "epsilon_insensitive"
        else:
            loss = "squared_epsilon_insensitive"
        svm_cls = partial(svm.LinearSVR, loss=loss)
    else:
        svm_cls = partial(svm.LinearSVC, penalty=penalty)
    return svm_cls(
        penalty=penalty,
        dual=dual,
        tol=float(tol),
        C=C,
        multi_class=multi_class,
        fit_intercept=fit_intercept,
        intercept_scaling=intercept_scaling,
        random_state=random_state,
        max_iter=max_iter,
    )


@MODELS.register("Ridge")
def ridge(
    alpha: Annotated[float, {"min": 0.0, "max": 100.0}] = 1.0,
    fit_intercept: bool = True,
    normalize: bool = False,
    max_iter: Annotated[int, {"min": 0, "max": 10000}] = 0,
    tol: str = "1e-3",
    solver: Literal[
        "auto", "svd", "cholesky", "lsqr", "sparse_cg", "sag", "saga"
    ] = "auto",
    random_state: str = "",
):
    random_state = _normalize_random_state(random_state)
    if max_iter == 0:
        max_iter = None
    return linear_model.Ridge(
        alpha=alpha,
        fit_intercept=fit_intercept,
        normalize=normalize,
        max_iter=max_iter,
        tol=float(tol),
        solver=solver,
        random_state=random_state,
    )


@MODELS.register("Lasso")
def lasso(
    alpha: Annotated[float, {"min": 0.0, "max": 100.0}] = 1.0,
    fit_intercept: bool = True,
    normalize: bool = False,
    max_iter: Annotated[int, {"min": 0, "max": 10000}] = 1000,
    tol: str = "1e-4",
    warm_start: bool = False,
    positive: bool = False,
    random_state: str = "",
    selection: Literal["cyclic", "random"] = "cyclic",
):
    random_state = _normalize_random_state(random_state)
    return linear_model.Lasso(
        alpha=alpha,
        fit_intercept=fit_intercept,
        normalize=normalize,
        max_iter=max_iter,
        tol=float(tol),
        warm_start=warm_start,
        positive=positive,
        random_state=random_state,
        selection=selection,
    )


@MODELS.register("ElasticNet")
def elastic_net(
    alpha: Annotated[float, {"min": 0.0, "max": 100.0}] = 1.0,
    l1_ratio: Annotated[float, {"min": 0.0, "max": 1.0}] = 0.5,
    fit_intercept: bool = True,
    normalize: bool = False,
    max_iter: Annotated[int, {"min": 0, "max": 10000}] = 1000,
    tol: str = "1e-4",
    warm_start: bool = False,
    positive: bool = False,
    random_state: str = "",
    selection: Literal["cyclic", "random"] = "cyclic",
):
    random_state = _normalize_random_state(random_state)
    return linear_model.ElasticNet(
        alpha=alpha,
        l1_ratio=l1_ratio,
        fit_intercept=fit_intercept,
        normalize=normalize,
        max_iter=max_iter,
        tol=float(tol),
        warm_start=warm_start,
        positive=positive,
        random_state=random_state,
        selection=selection,
    )


@MODELS.register("Multi-task Lasso")
def multi_task_lasso(
    alpha: Annotated[float, {"min": 0.0, "max": 100.0}] = 1.0,
    fit_intercept: bool = True,
    normalize: bool = False,
    max_iter: Annotated[int, {"min": 0, "max": 10000}] = 1000,
    tol: str = "1e-4",
    warm_start: bool = False,
    random_state: str = "",
    selection: Literal["cyclic", "random"] = "cyclic",
):
    random_state = _normalize_random_state(random_state)
    return linear_model.MultiTaskLasso(
        alpha=alpha,
        fit_intercept=fit_intercept,
        normalize=normalize,
        max_iter=max_iter,
        tol=float(tol),
        warm_start=warm_start,
        random_state=random_state,
        selection=selection,
    )


@MODELS.register("PCA")
def pca(
    n_components: Annotated[int, {"min": 1, "max": 1000}] = 2,
    whiten: bool = False,
    svd_solver: Literal["auto", "full", "arpack", "randomized"] = "auto",
    tol: str = "0.0",
    iterated_power: Annotated[int, {"min": 1, "max": 1000}] = 5,
    random_state: str = "",
):
    random_state = _normalize_random_state(random_state)
    return decomposition.PCA(
        n_components=n_components,
        whiten=whiten,
        svd_solver=svd_solver,
        tol=float(tol),
        iterated_power=iterated_power,
        random_state=random_state,
    )
