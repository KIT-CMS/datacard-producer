# -*- coding: utf-8 -*-

# NOTE: Do not import any modules from HenryPlotter and move this code in a new module

import ROOT
import CombineHarvester.CombineTools.ch as ch

import logging
logger = logging.getLogger(__name__)

import os


class DatacardBuilder(object):
    def __init__(self, input_filename, **selection):
        if not os.path.exists(input_filename):
            logger.fatal("File %s does not exist.", input_filename)
            raise Exception
        self._input_filename = input_filename

        self._shapes = self._get_shapes(selection)
        logger.info("Found %d shapes in input file %s.",
                    len(self._shapes), self._input_filename)
        self._cb = ch.CombineHarvester()

    def _get_shapes(self, selection):
        f = ROOT.TFile(self._input_filename)
        shapes = []
        for key in f.GetListOfKeys():
            shape = Shape(key.GetName())
            valid = True
            for key, value in selection.iteritems():
                if not isinstance(value, list):
                    value = [value]
                if not shape.get_property(key) in value:
                    valid = False
            if valid:
                logger.debug("Add shape %s.", shape)
                shapes.append(shape)
        if len(shapes) == 0:
            logger.fatal("No shapes found.")
            raise Exception
        return shapes

    def select(self, name, **selection):
        results = []
        for s in self.shapes:
            valid = True
            for key, value in selection.iteritems():
                if not isinstance(value, list):
                    value = [value]
                if not s.get_property(key) in value:
                    valid = False
            if valid:
                results.append(s.get_property(name))
        return list(set(results))

    def add_observation(self):
        pass

    def add_signals(self):
        pass

    def add_backgrounds(self):
        pass

    def add_shape_systematic(self):
        pass

    def add_normalization_systematic(self):
        pass

    def add_bin_by_bin(self):
        pass

    def summary(self):
        pass

    def print_datacard(self):
        self.cb.PrintAll()

    def write(self, output_prefix):
        logger.info("Create datacard files %s.txt and %s.root.", output_prefix,
                    output_prefix)
        writer = ch.CardWriter("{}.txt".format(output_prefix),
                               "{}.root".format(output_prefix))
        if logger.isEnabledFor(logging.DEBUG):
            writer.SetVerbosity(1)
        writer.CreateDirectories(
            False)  # TODO: FIXME: Does not work without this?
        # writer.SetWildcardMasses([]) # TODO: What is this doing?
        writer.WriteCards("", self.cb)

    @property
    def shapes(self):
        return self._shapes

    @property
    def cb(self):
        return self._cb

    @property
    def input_filename(self):
        return self._input_filename


class Shape(object):
    def __init__(self, name):
        self._name = name
        self._legend = {
            c: i
            for i, c in enumerate([
                "channel", "category", "process", "analysis", "era",
                "variable", "mass", "variation"
            ])
        }
        self._properties = [p for p in name.split('#') if p != ""]

    def __str__(self):
        return "Shape(channel={CHANNEL}, category={CATEGORY}, process={PROCESS}, analysis={ANALYSIS}, era={ERA}, variable={VARIABLE}, mass={MASS}, variation={VARIATION})".format(
            CHANNEL=self.channel,
            CATEGORY=self.category,
            PROCESS=self.process,
            ANALYSIS=self.analysis,
            ERA=self.era,
            VARIABLE=self.variable,
            MASS=self.mass,
            VARIATION=self.variation)

    def get_property(self, name):
        return self._properties[self._legend[name]]

    @property
    def name(self):
        return self._name

    @property
    def channel(self):
        return self._properties[self._legend["channel"]]

    @property
    def category(self):
        return self._properties[self._legend["category"]]

    @property
    def process(self):
        return self._properties[self._legend["process"]]

    @property
    def analysis(self):
        return self._properties[self._legend["analysis"]]

    @property
    def era(self):
        return self._properties[self._legend["era"]]

    @property
    def variable(self):
        return self._properties[self._legend["variable"]]

    @property
    def mass(self):
        return self._properties[self._legend["mass"]]

    @property
    def variation(self):
        return self._properties[self._legend["variation"]]
