import os

from typing import Any

import napari
import numpy.typing as npt
from qtpy.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget

from .base import SingleAxesWidget
from .features import FEATURES_LAYER_TYPES
from .util import Interval

__all__ = ["ScatterBaseWidget", "ScatterWidget", "FeaturesScatterWidget"]


class ScatterBaseWidget(SingleAxesWidget):
    """
    Base class for widgets that scatter two datasets against each other.
    """

    # if the number of points is greater than this value,
    # the scatter is plotted as a 2D histogram
    try:
        _threshold_to_switch_to_histogram = int(
            os.environ.get("MAX_SCATTER_POINTS")
        )
    except:
        _threshold_to_switch_to_histogram = 500
    print(
        f"_threshold_to_switch_to_histogram={_threshold_to_switch_to_histogram}"
    )

    def draw(self) -> None:
        """
        Scatter the currently selected layers.
        """
        if len(self.layers) == 0:
            return
        x, y, x_axis_name, y_axis_name = self._get_data()

        if type(x) is list and type(y) is list:
            for i in range(len(y)):
                self.axes.plot(x[i], y[i], alpha=0.5)
        else:
            if x.size > self._threshold_to_switch_to_histogram:
                self.axes.hist2d(
                    x.ravel(),
                    y.ravel(),
                    bins=100,
                )
            else:
                self.axes.scatter(x, y, alpha=0.5)

        self.axes.set_xlabel(x_axis_name)
        self.axes.set_ylabel(y_axis_name)

    def _get_data(self) -> tuple[npt.NDArray[Any], npt.NDArray[Any], str, str]:
        """
        Get the plot data.

        This must be implemented on the subclass.

        Returns
        -------
        x, y : np.ndarray
            x and y values of plot data.
        x_axis_name, y_axis_name : str
            Label to display on the x/y axis
        """
        raise NotImplementedError


class ScatterWidget(ScatterBaseWidget):
    """
    Scatter data in two similarly shaped layers.

    If there are more than 500 data points, a 2D histogram is displayed instead
    of a scatter plot, to avoid too many scatter points.
    """

    n_layers_input = Interval(2, 2)
    input_layer_types = (napari.layers.Image,)

    def _get_data(self) -> tuple[npt.NDArray[Any], npt.NDArray[Any], str, str]:
        """
        Get the plot data.

        Returns
        -------
        data : List[np.ndarray]
            List contains the in view slice of X and Y axis images.
        x_axis_name : str
            The title to display on the x axis
        y_axis_name: str
            The title to display on the y axis
        """
        x = self.layers[0].data[self.current_z]
        y = self.layers[1].data[self.current_z]
        x_axis_name = self.layers[0].name
        y_axis_name = self.layers[1].name

        return x, y, x_axis_name, y_axis_name


class FeaturesScatterWidget(ScatterBaseWidget):
    """
    Widget to scatter data stored in two layer feature attributes.
    """

    n_layers_input = Interval(1, 1)
    # All layers that have a .features attributes
    input_layer_types = FEATURES_LAYER_TYPES

    def __init__(
        self,
        napari_viewer: napari.viewer.Viewer,
        parent: QWidget | None = None,
    ):
        super().__init__(napari_viewer, parent=parent)

        self.layout().addLayout(QVBoxLayout())

        self._selectors: dict[str, QComboBox] = {}
        for dim in ["x-axis", "y-axis", "Color by"]:
            self._selectors[dim] = QComboBox()
            # Re-draw when combo boxes are updated
            self._selectors[dim].currentTextChanged.connect(self._draw)

            self.layout().addWidget(QLabel(f"{dim}:"))
            self.layout().addWidget(self._selectors[dim])

        self._update_layers(None)

    @property
    def x_axis_key(self) -> str | None:
        """
        Key for the x-axis data.
        """
        if self._selectors["x-axis"].count() == 0:
            return None
        else:
            return self._selectors["x-axis"].currentText()

    @x_axis_key.setter
    def x_axis_key(self, key: str) -> None:
        self._selectors["x-axis"].setCurrentText(key)
        self._draw()

    @property
    def y_axis_key(self) -> str | None:
        """
        Key for the y-axis data.
        """
        if self._selectors["y-axis"].count() == 0:
            return None
        else:
            return self._selectors["y-axis"].currentText()

    @y_axis_key.setter
    def y_axis_key(self, key: str) -> None:
        self._selectors["y-axis"].setCurrentText(key)
        self._draw()

    @property
    def color_by_key(self) -> str | None:
        """
        Key for the color group data.
        """
        if self._selectors["Color by"].count() == 0:
            return None
        else:
            return self._selectors["Color by"].currentText()

    @color_by_key.setter
    def color_by_key(self, key: str) -> None:
        self._selectors["Color by"].setCurrentText(key)
        self._draw()

    def _get_valid_axis_keys(self) -> list[str]:
        """
        Get the valid axis keys from the layer FeatureTable.

        Returns
        -------
        axis_keys : List[str]
            The valid axis keys in the FeatureTable. If the table is empty
            or there isn't a table, returns an empty list.
        """
        if len(self.layers) == 0 or not (hasattr(self.layers[0], "features")):
            return []
        else:
            return self.layers[0].features.keys()

    def _ready_to_scatter(self) -> bool:
        """
        Return True if selected layer has a feature table we can scatter with,
        and the two columns to be scatterd have been selected.
        """
        if not hasattr(self.layers[0], "features"):
            return False

        feature_table = self.layers[0].features
        valid_keys = self._get_valid_axis_keys()
        return (
            feature_table is not None
            and len(feature_table) > 0
            and self.x_axis_key in valid_keys
            and self.y_axis_key in valid_keys
            and self.color_by_key in valid_keys
        )

    def draw(self) -> None:
        """
        Scatter two features from the currently selected layer.
        """
        if self._ready_to_scatter():
            super().draw()

    def _get_data(self) -> tuple[npt.NDArray[Any], npt.NDArray[Any], str, str]:
        """
        Get the plot data from the ``features`` attribute of the first
        selected layer.

        Returns
        -------
        data : List[np.ndarray]
            List contains X and Y columns from the FeatureTable. Returns
            an empty array if nothing to plot.
        x_axis_name : str
            The title to display on the x axis. Returns
            an empty string if nothing to plot.
        y_axis_name: str
            The title to display on the y axis. Returns
            an empty string if nothing to plot.
        """
        feature_table = self.layers[0].features

        if self.color_by_key != "None":
            x = []
            y = []
            labels = []
            for label, group in feature_table.groupby([self.color_by_key]):
                labels.append(label)
                x.append(group[self.x_axis_key])
                y.append(group[self.y_axis_key])
        else:
            x = [feature_table[self.x_axis_key]]
            y = [feature_table[self.y_axis_key]]

        x_axis_name = str(self.x_axis_key)
        y_axis_name = str(self.y_axis_key)

        return x, y, x_axis_name, y_axis_name

    def on_update_layers(self) -> None:
        """
        Called when the layer selection changes by ``self.update_layers()``.
        """
        # Clear combobox
        for dim in ["x-axis", "y-axis", "Color by"]:
            while self._selectors[dim].count() > 0:
                self._selectors[dim].removeItem(0)
            # Add keys for newly selected layer
            if dim in ["Color by"]:
                # "Color by" is an option, so add "None" as first item to disable
                self._selectors[dim].addItems(["None"])
            self._selectors[dim].addItems(self._get_valid_axis_keys())
