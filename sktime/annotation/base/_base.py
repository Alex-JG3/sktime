#!/usr/bin/env python3 -u
# copyright: sktime developers, BSD-3-Clause License (see LICENSE file)
"""Base class template for annotator base type for time series stream.

    class name: BaseSeriesAnnotator

Scitype defining methods:
    fitting              - fit(self, X, Y=None)
    annotating           - predict(self, X)
    updating (temporal)  - update(self, X, Y=None)
    update&annotate      - update_predict(self, X)

Inspection methods:
    hyper-parameter inspection  - get_params()
    fitted parameter inspection - get_fitted_params()

State:
    fitted model/strategy   - by convention, any attributes ending in "_"
    fitted state flag       - check_is_fitted()
"""

__author__ = ["satya-pattnaik ", "fkiraly"]
__all__ = ["BaseSeriesAnnotator"]

import numpy as np
import pandas as pd

from sktime.base import BaseEstimator
from sktime.utils.validation.series import check_series


class BaseSeriesAnnotator(BaseEstimator):
    """Base series annotator.

    Developers should set the task and learning_type tags in the derived class.

    task : str {"segmentation", "change_point_detection", "anomaly_detection"}
        The main annotation task:
        * If `segmentation`, the annotator divides timeseries into discrete chunks
        based on certain criteria. The same label can be applied at mulitple
        disconnected regions of the timeseries.
        * If `change_point_detection`, the annotator finds points where the statistical
        properties of the timeseries change significantly.
        * If `anomaly_detection`, the annotator finds points that differ significantly
        from the normal statistical properties of the timeseries.

    learning_type : str {"supervised", "unsupervised"}
        Annotation learning type:
        * If `supervised`, the annotator learns from labelled data.
        * If `unsupervised`, the annotator learns from unlabelled data.

    Notes
    -----
    Assumes "predict" data is temporal future of "fit"
    Single time series in both, no meta-data.

    The base series annotator specifies the methods and method
    signatures that all annotators have to implement.

    Specific implementations of these methods is deferred to concrete
    annotators.
    """

    _tags = {
        "object_type": "series-annotator",  # type of object
        "learning_type": "None",  # Tag to determine test in test_all_annotators
        "task": "None",  # Tag to determine test in test_all_annotators
        #
        # todo: distribution_type? we may have to refactor this, seems very soecufuc
        "distribution_type": "None",  # Tag to determine test in test_all_annotators
    }  # for unit test cases

    def __init__(self):
        self.task = self.get_class_tag("task")
        self.learning_type = self.get_class_tag("learning_type")

        self._is_fitted = False

        self._X = None
        self._Y = None

        super().__init__()

    def fit(self, X, Y=None):
        """Fit to training data.

        Parameters
        ----------
        X : pd.DataFrame
            Training data to fit model to (time series).
        Y : pd.Series, optional
            Ground truth annotations for training if annotator is supervised.

        Returns
        -------
        self :
            Reference to self.

        Notes
        -----
        Creates fitted model that updates attributes ending in "_". Sets
        _is_fitted flag to True.
        """
        X = check_series(X)

        if Y is not None:
            Y = check_series(Y)

        self._X = X
        self._Y = Y

        # fkiraly: insert checks/conversions here, after PR #1012 I suggest

        self._fit(X=X, Y=Y)

        # this should happen last
        self._is_fitted = True

        return self

    def predict(self, X):
        """Create annotations on test/deployment data.

        Parameters
        ----------
        X : pd.DataFrame
            Data to annotate (time series).

        Returns
        -------
        Y : pd.Series
            Annotations for sequence X exact format depends on annotation type.
        """
        self.check_is_fitted()

        X = check_series(X)

        # fkiraly: insert checks/conversions here, after PR #1012 I suggest

        Y = self._predict(X=X)

        return Y

    def transform(self, X):
        """Create annotations on test/deployment data.

        Parameters
        ----------
        X : pd.DataFrame
            Data to annotate (time series).

        Returns
        -------
        Y : pd.Series
            Annotations for sequence X. The returned annotations will be in the dense
            format.
        """
        if self.task == "anomaly_detection" or self.task == "change_point_detection":
            Y = self.predict_points(X)
        elif self.task == "segmentation":
            Y = self.predict_segments(X)

        return self.sparse_to_dense(Y, len(X))

    def predict_scores(self, X):
        """Return scores for predicted annotations on test/deployment data.

        Parameters
        ----------
        X : pd.DataFrame
            Data to annotate (time series).

        Returns
        -------
        Y : pd.Series
            Scores for sequence X exact format depends on annotation type.
        """
        self.check_is_fitted()
        X = check_series(X)
        return self._predict_scores(X)

    def update(self, X, Y=None):
        """Update model with new data and optional ground truth annotations.

        Parameters
        ----------
        X : pd.DataFrame
            Training data to update model with (time series).
        Y : pd.Series, optional
            Ground truth annotations for training if annotator is supervised.

        Returns
        -------
        self :
            Reference to self.

        Notes
        -----
        Updates fitted model that updates attributes ending in "_".
        """
        self.check_is_fitted()

        X = check_series(X)

        if Y is not None:
            Y = check_series(Y)

        self._X = X.combine_first(self._X)

        if Y is not None:
            self._Y = Y.combine_first(self._Y)

        self._update(X=X, Y=Y)

        return self

    def update_predict(self, X):
        """Update model with new data and create annotations for it.

        Parameters
        ----------
        X : pd.DataFrame
            Training data to update model with, time series.

        Returns
        -------
        Y : pd.Series
            Annotations for sequence X exact format depends on annotation type.

        Notes
        -----
        Updates fitted model that updates attributes ending in "_".
        """
        X = check_series(X)

        self.update(X=X)
        Y = self.predict(X=X)

        return Y

    def fit_predict(self, X, Y=None):
        """Fit to data, then predict it.

        Fits model to X and Y with given annotation parameters
        and returns the annotations made by the model.

        Parameters
        ----------
        X : pd.DataFrame, pd.Series or np.ndarray
            Data to be transformed
        Y : pd.Series or np.ndarray, optional (default=None)
            Target values of data to be predicted.

        Returns
        -------
        self : pd.Series
            Annotations for sequence X exact format depends on annotation type.
        """
        # Non-optimized default implementation; override when a better
        # method is possible for a given algorithm.
        return self.fit(X, Y).predict(X)

    def _fit(self, X, Y=None):
        """Fit to training data.

        core logic

        Parameters
        ----------
        X : pd.DataFrame
            Training data to fit model to time series.
        Y : pd.Series, optional
            Ground truth annotations for training if annotator is supervised.

        Returns
        -------
        self :
            Reference to self.

        Notes
        -----
        Updates fitted model that updates attributes ending in "_".
        """
        raise NotImplementedError("abstract method")

    def _predict(self, X):
        """Create annotations on test/deployment data.

        core logic

        Parameters
        ----------
        X : pd.DataFrame
            Data to annotate, time series.

        Returns
        -------
        Y : pd.Series
            Annotations for sequence X exact format depends on annotation type.
        """
        raise NotImplementedError("abstract method")

    def _predict_scores(self, X):
        """Return scores for predicted annotations on test/deployment data.

        core logic

        Parameters
        ----------
        X : pd.DataFrame
            Data to annotate, time series.

        Returns
        -------
        Y : pd.Series
            Annotations for sequence X exact format depends on annotation type.
        """
        raise NotImplementedError("abstract method")

    def _update(self, X, Y=None):
        """Update model with new data and optional ground truth annotations.

        core logic

        Parameters
        ----------
        X : pd.DataFrame
            Training data to update model with time series
        Y : pd.Series, optional
            Ground truth annotations for training if annotator is supervised.

        Returns
        -------
        self :
            Reference to self.

        Notes
        -----
        Updates fitted model that updates attributes ending in "_".
        """
        # default/fallback: re-fit to all data
        self._fit(self._X, self._Y)

        return self

    def predict_segments(self, X):
        """Predict segments on test/deployment data.

        Parameters
        ----------
        X : pd.DataFrame
            Data to annotate, time series.

        Returns
        -------
        Y : pd.DataFrame
            Dataframe with two columns: seg_label, and seg_end. seg_label contains the
            labels of the segments, and seg_start contains the starting indexes of the
            segments.
        """
        if self.task == "anomaly_detection":
            raise RuntimeError(
                "Anomaly detection annotators should not be used for segmentation."
            )
        self.check_is_fitted()
        X = check_series(X)

        if self.task == "change_point_detection":
            return self.segments_to_change_points(self.predict_points(X))
        elif self.task == "segmentation":
            return self._predict_segments(X)

    def predict_points(self, X):
        """Predict changepoints/anomalies on test/deployment data.

        Parameters
        ----------
        X : pd.DataFrame
            Data to annotate, time series.

        Returns
        -------
        Y : pd.Series
            A series containing the indexes of the changepoints/anomalies in X.
        """
        self.check_is_fitted()
        X = check_series(X)

        if self.task == "anomaly_detection" or self.task == "change_point_detection":
            return self._predict_points(X)
        elif self.task == "segmentation":
            return self.segments_to_change_points(self.predict_segments(X))

    def _predict_segments(self, X):
        """Predict segments on test/deployment data.

        Parameters
        ----------
        X : pd.DataFrame
            Data to annotate, time series.

        Returns
        -------
        Y : pd.DataFrame
            Dataframe with two columns: seg_label, and seg_end. seg_label contains the
            labels of the segments, and seg_start contains the starting indexes of the
            segments.
        """
        raise NotImplementedError("abstract method")

    def _predict_points(self, X):
        """Predict changepoints/anomalies on test/deployment data.

        Parameters
        ----------
        X : pd.DataFrame
            Data to annotate, time series.

        Returns
        -------
        Y : np.ndarray
            1D array containing the indexes of the changepoints/anomalies in X.
        """
        raise NotImplementedError("abstract method")

    @staticmethod
    def sparse_to_dense(y_sparse, length=None):
        """Convert the sparse output from an annotator to a dense format.

        Parameters
        ----------
        y_sparse : {pd.DataFrame, pd.Series}
            * If `y_sparse` is a series, it should contain the integer index locations
              of anomalies/changepoints.
            * If `y_sparse` is a dataframe it should contain the following columns:
              `seg_label`, `seg_start`, and `seg_end`. `seg_label` contains the integer
              label of the segment, `seg_start` contains the integer start points of
              each segment, and `seg_end` contains the integer end points of each
              segment.
        length : {int, None}, optional
            Right pad the retured dense array so it has `length` elements. If `y_sparse`
            is dataframe of segments, pad the series with 0's. If the `y_sparse` is a
            series of changepoints/anomalies, pad the series with -1's.

        Returns
        -------
        pd.Series
            * If `y_sparse` is a series of changepoint/anomaly indices then a series of
              0's and 1's is returned. 1's represent anomalies/changepoints.
            * If `y_sparse` is a dataframe with columns: `seg_label`, `seg_start`, and
              `seg_end`, then a series of segments will be returned. The segments are
              labelled according to the seg_labels column. Areas which do not fall into
              a segment are given the -1 label.

        Examples
        --------
        >>> import pandas as pd
        >>> from sktime.annotation.base._base import BaseSeriesAnnotator
        >>> y_sparse = pd.Series([2, 5, 7])  # Indices of changepoints/anomalies
        >>> BaseSeriesAnnotator.sparse_to_dense(y_sparse, 10)
        0    0
        1    0
        2    1
        3    0
        4    0
        5    1
        6    0
        7    1
        8    0
        9    0
        dtype: int32
        >>> y_sparse = pd.DataFrame({
        ...     "seg_label": [1, 2, 1],
        ...     "seg_start": [0, 4, 6],
        ...     "seg_end": [3, 5, 9],
        ... })
        >>> BaseSeriesAnnotator.sparse_to_dense(y_sparse)
        0    1
        1    1
        2    1
        3    1
        4    2
        5    2
        6    1
        7    1
        8    1
        9    1
        dtype: int32
        """
        # The changepoint/anomly case
        if y_sparse.ndim == 1:
            final_index = y_sparse.iloc[-1]
            if length is None:
                length = y_sparse.iloc[-1] + 1

            if length <= final_index:
                raise RuntimeError(
                    "The length must be greater than the index of the final point."
                )

            y_dense = pd.Series(np.zeros(length, dtype="int32"))
            y_dense.iloc[y_sparse] = 1
            return y_dense

        # The segmentation case
        elif y_sparse.ndim == 2:
            final_index = y_sparse["seg_end"].iloc[-1]
            if length is None:
                length = y_sparse["seg_end"].iat[-1] + 1

            if length <= final_index:
                raise RuntimeError(
                    "The length must be greater than the index of the end point of the"
                    "final segment."
                )

            y_dense = pd.Series(np.full(length, np.nan))
            y_dense.iloc[y_sparse["seg_start"]] = y_sparse["seg_label"].astype("int32")
            y_dense.iloc[y_sparse["seg_end"]] = -y_sparse["seg_label"].astype("int32")

            if np.isnan(y_dense.iat[0]):
                y_dense.iat[0] = -1  # -1 represent unlabelled sections

            # The end points of the segments, and unclassified areas will have negative
            # labels
            y_dense = y_dense.ffill().astype("int32")

            # Replace the end points of the segments with correct label
            y_dense.iloc[y_sparse["seg_end"]] = y_sparse["seg_label"].astype("int32")

            # Areas with negative labels are unclassified so replace them with -1
            y_dense[y_dense < 0] = -1
            return y_dense.astype("int32")
        else:
            raise TypeError(
                "The input, y_sparse, must be a 1D pandas series or 2D dataframe."
            )

    @staticmethod
    def _sparse_points_to_dense(y_sparse, index):
        """Label the points in index as 1 or 0 depending on if they are in index.

        Parameters
        ----------
        y_sparse: pd.Series
            The values of the series must be the indexes of the change points.
        index: array-like
            Array of indexes which are to be labelled as

        Returns
        -------
        pd.Series
            A series with an index of `index`. Its value is 1 if the index is in
            y_sparse and 0 otherwise.
        """
        y_dense = pd.Series(np.zeros(len(index)), index=index, dtype="int64")
        y_dense[y_sparse.values] = 1
        return y_dense

    @staticmethod
    def _sparse_segments_to_dense(y_sparse, index):
        """Find the label for each index in `index` from sparse segments.

        Parameters
        ----------
        y_sparse : pd.Series
            A sparse representation of segments. The index must be the pandas interval
            datatype and the values must be the integer labels of the segments.
        index : array-like
            List of indexes that are to be labelled according to `y_sparse`.

        Returns
        -------
        pd.Series
            A series with the same index as `index` where each index is labelled
            according to `y_sparse`. Indexes that do not fall within any index are
            labelled -1.
        """
        if y_sparse.index.is_overlapping:
            raise NotImplementedError(
                "Cannot convert overlapping segments to a dense formet yet."
            )

        interval_indexes = y_sparse.index.get_indexer(index)

        # Negative indexes do not fall within any interval so they are ignored
        interval_labels = y_sparse.iloc[
            interval_indexes[interval_indexes >= 0]
        ].to_numpy()

        # -1 is used to represent points do not fall within a segment
        labels_dense = interval_indexes.copy()
        labels_dense[labels_dense >= 0] = interval_labels

        y_dense = pd.Series(labels_dense, index=index)
        return y_dense

    @staticmethod
    def dense_to_sparse(y_dense):
        """Convert the dense output from an annotator to a dense format.

        Parameters
        ----------
        y_dense : pd.Series
            * If `y_sparse` contains only 1's and 0's the 1's represent change points
              or anomalies.
            * If `y_sparse` contains only contains integers greater than 0, it is an
              an array of segments.

        Returns
        -------
        pd.DataFrame, pd.Series
            * If `y_sparse` is a series of changepoints/anomalies, a pandas series
              will be returned containing the indexes of the changepoints/anomalies
            * If `y_sparse` is a series of segments, a pandas dataframe will be
              returned with two columns: seg_label, and seg_start. The seg_label column
              contains the labels of each segment, and the seg_start column contains
              the indexes of the start of each segment.

        Examples
        --------
        >>> import pandas as pd
        >>> from sktime.annotation.base._base import BaseSeriesAnnotator
        >>> change_points = pd.Series([1, 0, 0, 1, 1, 0, 1])
        >>> BaseSeriesAnnotator.dense_to_sparse(change_points)
        0    0
        1    3
        2    4
        3    6
        dtype: int64
        >>> segments = pd.Series([1, 2, 2, 3, 3, 2])
        >>> BaseSeriesAnnotator.dense_to_sparse(segments)
           seg_label  seg_start  seg_end
        0          1          0        0
        1          2          1        2
        2          3          3        4
        3          2          5        5
        """
        if (y_dense == 0).any():
            # y_dense is a series of changepoints/anomalies
            return pd.Series(np.where(y_dense == 1)[0])
        else:
            segment_start_indexes = np.where(y_dense.diff() != 0)[0]
            segment_end_indexes = np.where(y_dense.diff(-1) != 0)[0]
            segment_labels = y_dense.iloc[segment_start_indexes].to_numpy()
            y_sparse = pd.DataFrame(
                {
                    "seg_label": segment_labels,
                    "seg_start": segment_start_indexes,
                    "seg_end": segment_end_indexes,
                }
            )

            # -1 represents unclassified regions so we remove them
            y_sparse = y_sparse.loc[y_sparse["seg_label"] != -1].reset_index(drop=True)
            return y_sparse

    @staticmethod
    def change_points_to_segments(y_sparse, start=None, end=None):
        """Convert an series of change point indexes to segments.

        Parameters
        ----------
        y_sparse : pd.Series
            A series containing the indexes of change points.
        start : optional
            Starting point of the first segment.
        end : optional
            Ending point of the last segment

        Returns
        -------
        pd.Series
            A series with an interval interval index indicating the start and end points
            of the segments. The values of the series are the labels of the segments.

        Examples
        --------
        >>> import pandas as pd
        >>> from sktime.annotation.base._base import BaseSeriesAnnotator
        >>> change_points = pd.Series([1, 2, 5])
        >>> BaseSeriesAnnotator.change_points_to_segments(change_points, 0, 7)
        [0, 1)   -1
        [1, 2)    1
        [2, 5)    2
        [5, 7)    3
        dtype: int64
        """
        breaks = y_sparse.values

        if start > breaks.min():
            raise ValueError(
                "The starting index must be before the first change point."
            )
        first_change_point = breaks.min()

        if start is not None:
            breaks = np.insert(breaks, 0, start)
        if end is not None:
            breaks = np.append(breaks, end)

        index = pd.IntervalIndex.from_breaks(breaks, copy=True, closed="left")
        segments = pd.Series(0, index=index)

        in_range = index.left >= first_change_point

        number_of_segments = in_range.sum()
        segments.loc[in_range] = range(1, number_of_segments + 1)
        segments.loc[~in_range] = -1

        return segments

    @staticmethod
    def segments_to_change_points(y_sparse):
        """Convert 2D array of segments to a 1D array of change points.

        Parameters
        ----------
        y_sparse : pd.DataFrame
            Dataframe with two columns: seg_label, and seg_end. seg_label contains the
            labels of the segments, and seg_start contains the starting indexes of the
            segments.

        Returns
        -------
        pd.Series
            A series containing the indexes of the start of each segment.

        Examples
        --------
        >>> import pandas as pd
        >>> from sktime.annotation.base._base import BaseSeriesAnnotator
        >>> change_points = pd.DataFrame({
        ...     "seg_label": [1, 2, 1],
        ...     "seg_start": [2, 5, 7],
        ...     "seg_end": [4, 6, 8],
        ... })
        >>> BaseSeriesAnnotator.segments_to_change_points(change_points)
        0    2
        1    5
        2    7
        dtype: int64
        """
        y_dense = BaseSeriesAnnotator.sparse_to_dense(y_sparse)
        diff = y_dense.diff()
        diff.iat[0] = 0  # The first point is never a change point
        change_points = np.where(diff != 0)[0]
        return pd.Series(change_points)
