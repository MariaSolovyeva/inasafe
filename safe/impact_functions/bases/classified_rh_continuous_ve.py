# coding=utf-8

from safe.common.exceptions import (
    MetadataLayerConstraintError)
from safe.definitions import layer_geometry_raster, \
    layer_mode_classified, layer_geometry_point, layer_geometry_line, \
    layer_geometry_polygon, layer_mode_continuous
from safe.impact_functions.base import ImpactFunction
from safe.impact_functions.bases.layer_types.classified_raster_hazard import \
    ClassifiedRasterHazardMixin
from safe.impact_functions.bases.layer_types.continuous_vector_exposure \
    import ContinuousVectorExposureMixin
from safe.impact_functions.bases.utilities import (
    check_layer_constraint)

__author__ = 'Rizky Maulana Nugraha "lucernae" <lana.pcfre@gmail.com>'
__date__ = '28/05/15'


class ClassifiedRHContinuousVE(
        ImpactFunction,
        ClassifiedRasterHazardMixin,
        ContinuousVectorExposureMixin):
    """Classified Raster Hazard, Continuous Vector Exposure base class.

    """

    def __init__(self):
        """Constructor"""
        super(ClassifiedRHContinuousVE, self).__init__()
        # check constraint
        valid = check_layer_constraint(
            self.metadata(),
            layer_mode_classified,
            [layer_geometry_raster],
            layer_mode_continuous,
            [layer_geometry_point,
             layer_geometry_line,
             layer_geometry_polygon])
        if not valid:
            raise MetadataLayerConstraintError()

    @ImpactFunction.hazard.setter
    # pylint: disable=W0221
    def hazard(self, value):
        ImpactFunction.hazard.fset(self, value)
        self.set_up_hazard_layer(value)

    @ImpactFunction.exposure.setter
    # pylint: disable=W0221
    def exposure(self, value):
        ImpactFunction.exposure.fset(self, value)
        self.set_up_exposure_layer(value)
