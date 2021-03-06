# Author: Arnaud Joly, Joel Nothman, Hamzeh Alsalhi
#
# License: BSD 3 clause
"""
Multi-class / multi-label utility function
==========================================

"""
from collections import Sequence
from itertools import chain
import warnings

from scipy.sparse import issparse
from scipy.sparse.base import spmatrix
from scipy.sparse import dok_matrix
from scipy.sparse import lil_matrix

import numpy as np

from ..externals.six import string_types

from .validation import check_array


def _unique_multiclass(y):
    if hasattr(y, '__array__'):
        return np.unique(np.asarray(y))
    else:
        return set(y)


def _unique_sequence_of_sequence(y):
    if hasattr(y, '__array__'):
        y = np.asarray(y)
    return set(chain.from_iterable(y))


def _unique_indicator(y):
    return np.arange(check_array(y, ['csr', 'csc', 'coo']).shape[1])


_FN_UNIQUE_LABELS = {
    'binary': _unique_multiclass,
    'multiclass': _unique_multiclass,
    'multilabel-sequences': _unique_sequence_of_sequence,
    'multilabel-indicator': _unique_indicator,
}


def unique_labels(*ys):
    """Extract an ordered array of unique labels

    We don't allow:
        - mix of multilabel and multiclass (single label) targets
        - mix of label indicator matrix and anything else,
          because there are no explicit labels)
        - mix of label indicator matrices of different sizes
        - mix of string and integer labels

    At the moment, we also don't allow "multiclass-multioutput" input type.

    Parameters
    ----------
    ys : array-likes,

    Returns
    -------
    out : numpy array of shape [n_unique_labels]
        An ordered array of unique labels.

    Examples
    --------
    >>> from sklearn.utils.multiclass import unique_labels
    >>> unique_labels([3, 5, 5, 5, 7, 7])
    array([3, 5, 7])
    >>> unique_labels([1, 2, 3, 4], [2, 2, 3, 4])
    array([1, 2, 3, 4])
    >>> unique_labels([1, 2, 10], [5, 11])
    array([ 1,  2,  5, 10, 11])
    """
    if not ys:
        raise ValueError('No argument has been passed.')
    # Check that we don't mix label format

    ys_types = set(type_of_target(x) for x in ys)
    if ys_types == set(["binary", "multiclass"]):
        ys_types = set(["multiclass"])

    if len(ys_types) > 1:
        raise ValueError("Mix type of y not allowed, got types %s" % ys_types)

    label_type = ys_types.pop()

    # Check consistency for the indicator format
    if (label_type == "multilabel-indicator" and
            len(set(check_array(y, ['csr', 'csc', 'coo']).shape[1] for y in ys)) > 1):
        raise ValueError("Multi-label binary indicator input with "
                         "different numbers of labels")

    # Get the unique set of labels
    _unique_labels = _FN_UNIQUE_LABELS.get(label_type, None)
    if not _unique_labels:
        raise ValueError("Unknown label type: %r" % ys)

    ys_labels = set(chain.from_iterable(_unique_labels(y) for y in ys))

    # Check that we don't mix string type with number type
    if (len(set(isinstance(label, string_types) for label in ys_labels)) > 1):
        raise ValueError("Mix of label input types (string and number)")

    return np.array(sorted(ys_labels))


def _is_integral_float(y):
    return y.dtype.kind == 'f' and np.all(y.astype(int) == y)


def is_label_indicator_matrix(y):
    """ Check if ``y`` is in the label indicator matrix format (multilabel).

    Parameters
    ----------
    y : numpy array of shape [n_samples] or sequence of sequences
        Target values. In the multilabel case the nested sequences can
        have variable lengths.

    Returns
    -------
    out : bool,
        Return ``True``, if ``y`` is in a label indicator matrix format,
        else ``False``.

    Examples
    --------
    >>> import numpy as np
    >>> from sklearn.utils.multiclass import is_label_indicator_matrix
    >>> is_label_indicator_matrix([0, 1, 0, 1])
    False
    >>> is_label_indicator_matrix([[1], [0, 2], []])
    False
    >>> is_label_indicator_matrix(np.array([[1, 0], [0, 0]]))
    True
    >>> is_label_indicator_matrix(np.array([[1], [0], [0]]))
    False
    >>> is_label_indicator_matrix(np.array([[1, 0, 0]]))
    True

    """
    if hasattr(y, '__array__'):
        y = np.asarray(y)
    if not (hasattr(y, "shape") and y.ndim == 2 and y.shape[1] > 1):
        return False

    if issparse(y):
        if isinstance(y, (dok_matrix, lil_matrix)):
            y = y.tocsr()
        return (len(y.data) == 0 or np.ptp(y.data) == 0 and
                (y.dtype.kind in 'biu' or  # bool, int, uint
                 _is_integral_float(np.unique(y.data))))
    else:
        labels = np.unique(y)

        return len(labels) < 3 and (y.dtype.kind in 'biu' or  # bool, int, uint
                                    _is_integral_float(labels))


def is_sequence_of_sequences(y):
    """ Check if ``y`` is in the sequence of sequences format (multilabel).

    This format is DEPRECATED.

    Parameters
    ----------
    y : sequence or array.

    Returns
    -------
    out : bool,
        Return ``True``, if ``y`` is a sequence of sequences else ``False``.
    """
    # the explicit check for ndarray is for forward compatibility; future
    # versions of Numpy might want to register ndarray as a Sequence
    try:
        if hasattr(y, '__array__'):
            y = np.asarray(y)
        out = (not hasattr(y[0], '__array__') and isinstance(y[0], Sequence)
               and not isinstance(y[0], string_types))
    except (IndexError, TypeError):
        return False
    if out:
        warnings.warn('Direct support for sequence of sequences multilabel '
                      'representation will be unavailable from version 0.17. '
                      'Use sklearn.preprocessing.MultiLabelBinarizer to '
                      'convert to a label indicator representation.',
                      DeprecationWarning)
    return out


def is_multilabel(y):
    """ Check if ``y`` is in a multilabel format.

    Parameters
    ----------
    y : numpy array of shape [n_samples] or sequence of sequences
        Target values. In the multilabel case the nested sequences can
        have variable lengths.

    Returns
    -------
    out : bool,
        Return ``True``, if ``y`` is in a multilabel format, else ```False``.

    Examples
    --------
    >>> import numpy as np
    >>> from sklearn.utils.multiclass import is_multilabel
    >>> is_multilabel([0, 1, 0, 1])
    False
    >>> is_multilabel(np.array([[1, 0], [0, 0]]))
    True
    >>> is_multilabel(np.array([[1], [0], [0]]))
    False
    >>> is_multilabel(np.array([[1, 0, 0]]))
    True

    """
    return is_label_indicator_matrix(y) or is_sequence_of_sequences(y)


def type_of_target(y):
    """Determine the type of data indicated by target `y`

    Parameters
    ----------
    y : array-like

    Returns
    -------
    target_type : string
        One of:
        * 'continuous': `y` is an array-like of floats that are not all
          integers, and is 1d or a column vector.
        * 'continuous-multioutput': `y` is a 2d array of floats that are
          not all integers, and both dimensions are of size > 1.
        * 'binary': `y` contains <= 2 discrete values and is 1d or a column
          vector.
        * 'multiclass': `y` contains more than two discrete values, is not a
          sequence of sequences, and is 1d or a column vector.
        * 'multiclass-multioutput': `y` is a 2d array that contains more
          than two discrete values, is not a sequence of sequences, and both
          dimensions are of size > 1.
        * 'multilabel-sequences': `y` is a sequence of sequences, a 1d
          array-like of objects that are sequences of labels.
        * 'multilabel-indicator': `y` is a label indicator matrix, an array
          of two dimensions with at least two columns, and at most 2 unique
          values.
        * 'unknown': `y` is array-like but none of the above, such as a 3d
          array, or an array of non-sequence objects.

    Examples
    --------
    >>> import numpy as np
    >>> type_of_target([0.1, 0.6])
    'continuous'
    >>> type_of_target([1, -1, -1, 1])
    'binary'
    >>> type_of_target(['a', 'b', 'a'])
    'binary'
    >>> type_of_target([1, 0, 2])
    'multiclass'
    >>> type_of_target(['a', 'b', 'c'])
    'multiclass'
    >>> type_of_target(np.array([[1, 2], [3, 1]]))
    'multiclass-multioutput'
    >>> type_of_target(np.array([[1.5, 2.0], [3.0, 1.6]]))
    'continuous-multioutput'
    >>> type_of_target(np.array([[0, 1], [1, 1]]))
    'multilabel-indicator'
    """
    valid = ((isinstance(y, (Sequence, spmatrix)) or hasattr(y, '__array__'))
             and not isinstance(y, string_types))
    if not valid:
        raise ValueError('Expected array-like (array or non-string sequence), '
                         'got %r' % y)

    if is_sequence_of_sequences(y):
        return 'multilabel-sequences'
    elif is_label_indicator_matrix(y):
        return 'multilabel-indicator'

    try:
        y = np.asarray(y)
    except ValueError:
        # known to fail in numpy 1.3 for array of arrays
        return 'unknown'
    if y.ndim > 2 or (y.dtype == object and len(y) and
                      not isinstance(y.flat[0], string_types)):
        return 'unknown'
    if y.ndim == 2 and y.shape[1] == 0:
        return 'unknown'
    elif y.ndim == 2 and y.shape[1] > 1:
        suffix = '-multioutput'
    else:
        # column vector or 1d
        suffix = ''

    # check float and contains non-integer float values:
    if y.dtype.kind == 'f' and np.any(y != y.astype(int)):
        return 'continuous' + suffix
    if len(np.unique(y)) <= 2:
        assert not suffix, "2d binary array-like should be multilabel"
        return 'binary'
    else:
        return 'multiclass' + suffix


def _check_partial_fit_first_call(clf, classes=None):
    """Private helper function for factorizing common classes param logic

    Estimators that implement the ``partial_fit`` API need to be provided with
    the list of possible classes at the first call to partial_fit.

    Subsequent calls to partial_fit should check that ``classes`` is still
    consistent with a previous value of ``clf.classes_`` when provided.

    This function returns True if it detects that this was the first call to
    ``partial_fit`` on ``clf``. In that case the ``classes_`` attribute is also
    set on ``clf``.

    """
    if getattr(clf, 'classes_', None) is None and classes is None:
        raise ValueError("classes must be passed on the first call "
                         "to partial_fit.")

    elif classes is not None:
        if getattr(clf, 'classes_', None) is not None:
            if not np.all(clf.classes_ == unique_labels(classes)):
                raise ValueError(
                    "`classes=%r` is not the same as on last call "
                    "to partial_fit, was: %r" % (classes, clf.classes_))

        else:
            # This is the first call to partial_fit
            clf.classes_ = unique_labels(classes)
            return True

    # classes is None and clf.classes_ has already previously been set:
    # nothing to do
    return False
