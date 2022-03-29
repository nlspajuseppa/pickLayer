import itertools

import pytest
from qgis.core import (
    QgsGeometry,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsVectorLayerUtils,
)

from pickLayer.core.set_active_layer_tool import SetActiveLayerTool
from pickLayer.qgis_plugin_tools.tools.resources import plugin_test_data_path

ALL_LAYER_TYPES = [
    QgsVectorLayer("Point", "Point", "memory"),
    QgsVectorLayer("LineString", "LineString", "memory"),
    QgsVectorLayer("Polygon", "Polygon", "memory"),
]

LINE_AND_POLYGON_LAYERS = [
    QgsVectorLayer("LineString", "LineString", "memory"),
    QgsVectorLayer("Polygon", "Polygon", "memory"),
]


@pytest.fixture()
def map_tool(qgis_iface):
    return SetActiveLayerTool(qgis_iface.mapCanvas())


@pytest.fixture(scope="session")
def test_layers():
    layers = [
        QgsVectorLayer("PointZ", "point_layer", "memory"),
        QgsVectorLayer("LineStringZ", "line_layer", "memory"),
        QgsVectorLayer("PolygonZ", "polygon_layer", "memory"),
    ]

    wkt_geom_collection = [
        ("PointZ (-1 0 0)", "PointZ (-2 0 0)"),
        ("LineStringZ (1 0 0, 1 5 0)", "LineStringZ (2 0 0, 2 5 0)"),
        (
            "PolygonZ ((1 1 0, 1 2 0, 2 2 0, 2 1 0, 1 1 0))",
            "PolygonZ ((2 0 0, 2 3 0, 3 3 0, 3 0 0, 2 0 0))",
        ),
    ]

    for layer, wkt_geoms in zip(layers, wkt_geom_collection):
        features = [
            QgsVectorLayerUtils.createFeature(layer, QgsGeometry.fromWkt(wkt_geoms[0])),
            QgsVectorLayerUtils.createFeature(layer, QgsGeometry.fromWkt(wkt_geoms[1])),
        ]

        assert all(not feature.geometry().isNull() for feature in features)
        success, _ = layer.dataProvider().addFeatures(features)
        assert success

        QgsProject.instance().addMapLayer(layer)
    return layers


@pytest.mark.parametrize(
    argnames=(
        "mouse_x",
        "mouse_y",
        "search_radius",
        "expected_num_results",
    ),
    argvalues=[
        (0, 0, 0, 0),
        (0, 0, 1, 3),
        (0, 0, 2, 6),
    ],
    ids=[
        "radius-0m-none-found",
        "radius-1m-half-found",
        "radius-2m-all-found",
    ],
)
def test_set_active_layer_using_closest_feature(
    map_tool,
    test_layers,
    mouse_x,
    mouse_y,
    search_radius,
    expected_num_results,
    mocker,
):

    m_choose_layer_from_identify_results = mocker.patch.object(
        map_tool,
        "_choose_layer_from_identify_results",
        return_value=None,
        autospec=True,
    )

    map_tool.set_active_layer_using_closest_feature(mouse_x, mouse_y, search_radius)

    identify_results = m_choose_layer_from_identify_results.call_args.args[0]
    assert len(identify_results) == expected_num_results


def test_set_active_layer_using_closest_feature_sets_returned_layer_active(
    map_tool,
    qgis_iface,
    mocker,
):
    mock_return_layer = QgsVectorLayer("PointZ", "point_layer", "memory")
    m_choose_layer_from_identify_results = mocker.patch.object(
        map_tool,
        "_choose_layer_from_identify_results",
        return_value=mock_return_layer,
        autospec=True,
    )
    m_set_active_layer = mocker.patch.object(
        qgis_iface, "setActiveLayer", return_value=None
    )

    map_tool.set_active_layer_using_closest_feature(0, 0)

    m_choose_layer_from_identify_results.assert_called_once()
    assert m_set_active_layer.call_args.args[0] == mock_return_layer


def test_set_active_layer_using_closest_feature_does_nothing_if_layer_not_found(
    map_tool,
    qgis_iface,
    mocker,
):
    m_choose_layer_from_identify_results = mocker.patch.object(
        map_tool,
        "_choose_layer_from_identify_results",
        return_value=None,
        autospec=True,
    )
    m_set_active_layer = mocker.patch.object(
        qgis_iface, "setActiveLayer", return_value=None
    )

    map_tool.set_active_layer_using_closest_feature(0, 0)

    m_choose_layer_from_identify_results.assert_called_once()
    m_set_active_layer.assert_not_called()


@pytest.mark.parametrize(
    "layers",
    argvalues=itertools.permutations(ALL_LAYER_TYPES, 3),
)
def test_choose_layer_should_choose_point_layer(
    map_tool,
    layers,
):

    resulting_layer = map_tool._choose_layer(layers)

    assert resulting_layer.name() == "Point"


@pytest.mark.parametrize(
    "layers",
    argvalues=itertools.permutations(LINE_AND_POLYGON_LAYERS, 2),
)
def test_choose_layer_should_choose_line_layer(
    map_tool,
    layers,
):

    resulting_layer = map_tool._choose_layer(layers)

    assert resulting_layer.name() == "LineString"


def test_choose_layer_should_return_vector_layer(map_tool):

    raster_file = plugin_test_data_path("raster", "simple_raster_layer.tif")

    raster_layer = QgsRasterLayer(raster_file)

    resulting_layer = map_tool._choose_layer(
        [
            QgsVectorLayer("Point", "Point", "memory"),
            QgsVectorLayer("LineString", "LineString", "memory"),
            QgsVectorLayer("Polygon", "Polygon", "memory"),
            raster_layer,
        ]
    )

    assert resulting_layer.name() == "Point"
