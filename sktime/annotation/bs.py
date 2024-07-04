"""Binary Segmentation."""

import numpy as np
import pandas as pd

from sktime.annotation.base._base import BaseSeriesAnnotator


class BinarySegmentation(BaseSeriesAnnotator):
    """Binary segmentation change point detector.

    This method finds change points by fitting piecewise constant functions to a
    timeseries. Change points are selected according to the CUMSUM statistic.

    Parameters
    ----------
    threshold : float
        Threshold for the CUMSUM statistic. Change points that do not increase the
        CUMSUM statistic above this threshold are ignored.

    Notes
    -----
    This is base on the implementation of binary segmentation described in [1]_.

    References
    ----------
    .. [1] Fryzlewicz, Piotr. "WILD BINARY SEGMENTATION FOR MULTIPLE CHANGE-POINT
           DETECTION." The Annals of Statistics, vol. 42, no. 6, 2014, pp. 2243–81.
           JSTOR, http://www.jstor.org/stable/43556493. Accessed 4 July 2024.

    Examples
    --------
    >>> import pandas as pd
    >>> from sktime.annotation.bs import BinarySegmentation
    >>> model = BinarySegmentation(threshold=1)
    >>> X = pd.Series([1, 1, 1, 1, 5, 5, 5, 5])
    >>> model.fit_predict(X)
    0    3
    dtype: int64
    >>> X = pd.Series([1.1, 1.3, -1.4, -1.4, 5.5, 5.6])
    >>> model.fit_predict(X)
    0    1
    1    3
    dtype: int64
    """

    _tags = {
        "fit_is_empty": True,
        "task": "change_point_detection",
        "learning_type": "unsupervised",
    }

    def __init__(self, threshold):
        self.threshold = threshold
        super().__init__()

    def _cumsum_statistic(self, X, start, end, change_point):
        """Calculate CUMSUM statistic to evaluate a change point.

        The CUMSUM statistic measures the quality of the fit on 'X' of a piecewise
        constant function that starts at 'start', ends at 'end', and has one change
        point at 'change_point'. This is taken from [1]_.

        Parameters
        ----------
        X : pd.Series
            Timeseries on which the cumsum statistic is calculated.
        start : int
            Index (in terms of 'iloc') of the start of the left segment.
        end : int
            Index (in terms of 'iloc') of the end of the right segment.
        change_point : int
            Index (in terms of 'iloc') of the change point in the piecewise constant
            function.

        Returns
        -------
        float
            The CUMSUM statistic which is a positive float. A larger value indicates a
            bigger difference between the left and right segments.
        """
        if change_point < start or change_point >= end:
            raise RuntimeError("The change point must be within 'start' and 'end'.")

        n = end - start + 1
        w_left = np.sqrt((end - change_point) / (n * (change_point - start + 1)))
        w_right = np.sqrt((change_point - start + 1) / (n * (end - change_point)))

        left = X.iloc[start : change_point + 1].to_numpy()
        right = X.iloc[change_point + 1 : end + 1].to_numpy()
        cumsum_statistic = w_left * np.sum(left) - w_right * np.sum(right)

        return np.abs(cumsum_statistic)

    def _find_change_points(self, X, start, end, threshold, change_points):
        """Find change points in 'X' between the 'start' and 'end' index.

        All change points are appended to 'change_points'.

        Parameters
        ----------
        X : pd.Series
            Timeseries data on which the change points will be found.
        start : int
            Starting index of the window in which the change points will be found.
        end : int
            Final index of the window in which the change points will be found. The
            value at this index will be included in the window (inclusive).
        threshold : float
            Threshold for a change point to be kept.
        change_points : list[int]
            Indexes of change points. Newly detected change points are appended to this
            list.
        """
        if end - start < 1:
            return

        costs = []
        for change_point in range(start, end):
            costs.append(self._cumsum_statistic(X, start, end, change_point))

        if np.max(costs) > threshold:
            new_change_point = start + np.argmax(costs)
            change_points.append(new_change_point)
            self._find_change_points(
                X, start, new_change_point, threshold, change_points
            )
            self._find_change_points(
                X, new_change_point + 1, end, threshold, change_points
            )
        else:
            return

    def _fit(self, X, Y=None):
        return self

    def _predict(self, X, Y=None):
        """Find the change points on 'X'.

        Parameters
        ----------
        X : pd.Series
            Timeseries on which the change points will be detected.
        Y : any
            Unused argument. Included for compatability with sklearn.

        Returns
        -------
        pd.Series
            Series whose values are the indexes of the change points.
        """
        change_points = []
        self._find_change_points(X, 0, len(X) - 1, self.threshold, change_points)
        change_points.sort()
        return pd.Series(X.index[change_points])

    @classmethod
    def get_test_params(cls, parameter_set="default"):
        """Return testing parameter settings for the estimator.

        Parameters
        ----------
        parameter_set : str, default="default"
            Name of the set of test parameters to return, for use in tests. If no
            special parameters are defined for a value, will return ``"default"`` set.

        Returns
        -------
        params : dict or list of dict, default = {}
            Parameters to create testing instances of the class
            Each dict are parameters to construct an "interesting" test instance, i.e.,
            ``MyClass(**params)`` or ``MyClass(**params[i])`` creates a valid test
            instance.
            ``create_test_instance`` uses the first (or only) dictionary in ``params``
        """
        return {"threshold": 1}
