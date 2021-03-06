# coding=utf-8
"""Flood Evacuation Impact Function."""
__author__ = 'Rizky Maulana Nugraha'

import logging
import numpy

from safe.impact_functions.core import (
    population_rounding_full,
    population_rounding,
    evacuated_population_needs,
    has_no_data)
from safe.impact_functions.impact_function_manager \
    import ImpactFunctionManager
from safe.impact_functions.inundation.flood_raster_population\
    .metadata_definitions import FloodEvacuationRasterHazardMetadata
from safe.impact_functions.bases.continuous_rh_continuous_re import \
    ContinuousRHContinuousRE
from safe.utilities.i18n import tr
from safe.common.tables import Table, TableRow
from safe.common.exceptions import ZeroImpactException
from safe.storage.raster import Raster
from safe.common.utilities import (
    format_int,
    create_classes,
    humanize_class,
    create_label,
    verify,
    get_thousand_separator)
from safe.gui.tools.minimum_needs.needs_profile import add_needs_parameters, \
    get_needs_provenance_value

LOGGER = logging.getLogger('InaSAFE')


class FloodEvacuationRasterHazardFunction(ContinuousRHContinuousRE):
    # noinspection PyUnresolvedReferences
    """Risk plugin for flood population evacuation."""
    _metadata = FloodEvacuationRasterHazardMetadata()

    def __init__(self):
        """Constructor."""
        super(FloodEvacuationRasterHazardFunction, self).__init__()
        self.impact_function_manager = ImpactFunctionManager()

        # AG: Use the proper minimum needs, update the parameters
        self.parameters = add_needs_parameters(self.parameters)

    def _tabulate(
            self,
            counts,
            evacuated,
            minimum_needs,
            question,
            rounding_evacuated,
            thresholds,
            total,
            no_data_warning):
        """Create a tabulated output.
        :param counts: The counts breakdown.
        :param evacuated: The total.
        :param minimum_needs: The minimum needs breakdown.
        :param question: The impact question.
        :param rounding_evacuated: The rounding that was applied.
        :param thresholds: The thresholds that where used.
        :param total: The impact total.
        :param no_data_warning: Flag to warn about nodata in layer data.
        :return:
        """
        table_body = [
            question,
            TableRow([(tr('People in %.1f m of water') % thresholds[-1]),
                      '%s*' % format_int(evacuated)],
                     header=True),
            TableRow(tr('* Number is rounded up to the nearest %s') % (
                rounding_evacuated)),
            TableRow(tr('Map shows the numbers of people needing evacuation')),
            TableRow(tr(
                'Table shows the weekly minimum needs for all evacuated people'
            ))]
        total_needs = evacuated_population_needs(
            evacuated, minimum_needs)
        for frequency, needs in total_needs.items():
            table_body.append(TableRow(
                [
                    tr('Needs should be provided %s' % frequency),
                    tr('Total')
                ],
                header=True))
            for resource in needs:
                table_body.append(TableRow([
                    tr(resource['table name']),
                    format_int(resource['amount'])]))
        table_body.append(TableRow(tr('Action Checklist:'), header=True))
        table_body.append(TableRow(tr('How will warnings be disseminated?')))
        table_body.append(TableRow(tr('How will we reach stranded people?')))
        table_body.append(TableRow(tr('Do we have enough relief items?')))
        table_body.append(TableRow(tr('If yes, where are they located and how '
                                      'will we distribute them?')))
        table_body.append(TableRow(tr(
            'If no, where can we obtain additional relief items from and how '
            'will we transport them to here?')))
        # Extend impact report for on-screen display
        table_body.extend([
            TableRow(tr('Notes'), header=True),
            tr('Total population: %s') % format_int(total),
            tr('People need evacuation if flood levels exceed %(eps).1f m') %
            {'eps': thresholds[-1]},
            tr(get_needs_provenance_value(self.parameters)),
            tr('All values are rounded up to the nearest integer in order to '
               'avoid representing human lives as fractions.'),
            tr('All affected people are assumed to be evacuated.')])
        if no_data_warning:
            table_body.extend([
                tr('The layers contained `no data`. This missing data was '
                   'carried through to the impact layer.'),
                tr('`No data` values in the impact layer were treated as 0 '
                   'when counting the affected or total population.')
            ])
        if len(counts) > 1:
            table_body.append(TableRow(tr('Detailed breakdown'), header=True))

            for i, val in enumerate(counts):
                if i == len(thresholds) - 1:
                    # The last interval
                    s = (tr('People in >= %(lo).1f m of water: %(val)s') % {
                        'lo': thresholds[i],
                        'val': format_int(val)})
                else:
                    # all other classes show lower/upper range
                    s = tr(
                        'People in %(lo).1f m to %(hi).1f m of water: '
                        '%(val)s') % {
                            'lo': thresholds[i],
                            'hi': thresholds[i + 1],
                            'val': format_int(val)}
                table_body.append(TableRow(s))

        return table_body, total_needs

    def _tabulate_zero_impact(self, evacuated, question, table_body,
                              thresholds):
        table_body = [
            question,
            TableRow([(tr('People in %.1f m of water') % thresholds[-1]),
                      '%s' % format_int(evacuated)],
                     header=True)]
        return table_body

    def run(self):
        """Risk plugin for flood population evacuation.

        Counts number of people exposed to flood levels exceeding
        specified threshold.

        :returns: Map of population exposed to flood levels exceeding the
            threshold. Table with number of people evacuated and supplies
            required.
        :rtype: tuple
        """
        self.validate()
        self.prepare()

        # Determine depths above which people are regarded affected [m]
        # Use thresholds from inundation layer if specified
        thresholds = self.parameters['thresholds'].value

        verify(
            isinstance(thresholds, list),
            'Expected thresholds to be a list. Got %s' % str(thresholds))

        # Extract data as numeric arrays
        data = self.hazard.layer.get_data(nan=True)  # Depth
        no_data_warning = False
        if has_no_data(data):
            no_data_warning = True

        # Calculate impact as population exposed to depths > max threshold
        population = self.exposure.layer.get_data(nan=True, scaling=True)
        if has_no_data(population):
            no_data_warning = True

        # Calculate impact to intermediate thresholds
        counts = []
        # merely initialize
        impact = None
        for i, lo in enumerate(thresholds):
            if i == len(thresholds) - 1:
                # The last threshold
                impact = medium = numpy.where(data >= lo, population, 0)
            else:
                # Intermediate thresholds
                hi = thresholds[i + 1]
                medium = numpy.where((data >= lo) * (data < hi), population, 0)

            # Count
            val = int(numpy.nansum(medium))

            counts.append(val)

        # Carry the no data values forward to the impact layer.
        impact = numpy.where(numpy.isnan(population), numpy.nan, impact)
        impact = numpy.where(numpy.isnan(data), numpy.nan, impact)

        # Count totals
        evacuated, rounding_evacuated = population_rounding_full(counts[-1])
        total = int(numpy.nansum(population))
        # Don't show digits less than a 1000
        total = population_rounding(total)

        minimum_needs = [
            parameter.serialize() for parameter in
            self.parameters['minimum needs']
        ]

        # Generate impact report for the pdf map
        # noinspection PyListCreation
        table_body, total_needs = self._tabulate(
            counts,
            evacuated,
            minimum_needs,
            self.question,
            rounding_evacuated,
            thresholds,
            total,
            no_data_warning)

        # Result
        impact_summary = Table(table_body).toNewlineFreeString()
        impact_table = impact_summary

        # check for zero impact
        if numpy.nanmax(impact) == 0 == numpy.nanmin(impact):
            table_body = self._tabulate_zero_impact(
                evacuated, self.question, table_body, thresholds)
            my_message = Table(table_body).toNewlineFreeString()
            raise ZeroImpactException(my_message)

        # Create style
        colours = [
            '#FFFFFF', '#38A800', '#79C900', '#CEED00',
            '#FFCC00', '#FF6600', '#FF0000', '#7A0000']
        classes = create_classes(impact.flat[:], len(colours))
        interval_classes = humanize_class(classes)
        style_classes = []

        for i in xrange(len(colours)):
            style_class = dict()
            if i == 1:
                label = create_label(interval_classes[i], 'Low')
            elif i == 4:
                label = create_label(interval_classes[i], 'Medium')
            elif i == 7:
                label = create_label(interval_classes[i], 'High')
            else:
                label = create_label(interval_classes[i])
            style_class['label'] = label
            style_class['quantity'] = classes[i]
            if i == 0:
                transparency = 100
            else:
                transparency = 0
            style_class['transparency'] = transparency
            style_class['colour'] = colours[i]
            style_classes.append(style_class)

        style_info = dict(
            target_field=None,
            style_classes=style_classes,
            style_type='rasterStyle')

        # For printing map purpose
        map_title = tr('People in need of evacuation')
        legend_notes = tr(
            'Thousand separator is represented by %s' %
            get_thousand_separator())
        legend_units = tr('(people per cell)')
        legend_title = tr('Population Count')

        # Create raster object and return
        raster = Raster(
            impact,
            projection=self.hazard.layer.get_projection(),
            geotransform=self.hazard.layer.get_geotransform(),
            name=tr('Population which %s') % (
                self.impact_function_manager
                .get_function_title(self).lower()),
            keywords={
                'impact_summary': impact_summary,
                'impact_table': impact_table,
                'map_title': map_title,
                'legend_notes': legend_notes,
                'legend_units': legend_units,
                'legend_title': legend_title,
                'evacuated': evacuated,
                'total_needs': total_needs},
            style_info=style_info)
        self._impact = raster
        return raster
