# -*- coding: utf-8 -*-

import ROOT
import CombineHarvester.CombineTools.ch as ch

import logging
logger = logging.getLogger(__name__)

import os


class DatacardBuilder(object):
    def __init__(self, input_filename):
        if not os.path.exists(input_filename):
            logger.fatal("File %s does not exist.", input_filename)
            raise Exception
        self._input_filename = input_filename

        self._shapes = self._get_shapes()
        logger.info("Found %d shapes in input file %s.",
                    len(self._shapes), self._input_filename)
        self._cb = ch.CombineHarvester()
        self._shapes_extracted = False

    def make_pairs(self, x):
        return [(i, c) for i, c in enumerate(x)]

    def _convert_to_list(self, x):
        if not isinstance(x, list):
            return [x]
        else:
            return x

    def _get_shapes(self):
        f = ROOT.TFile(self._input_filename)
        shapes = []
        for key in f.GetListOfKeys():
            shape = Shape(key.GetName())
            shapes.append(shape)
        if len(shapes) == 0:
            logger.fatal("No shapes found.")
            raise Exception
        return shapes

    def add_observation(self, mass, analysis, era, channel, category):
        mass = self._convert_to_list(mass)
        analysis = self._convert_to_list(analysis)
        era = self._convert_to_list(era)
        channel = self._convert_to_list(channel)
        category = self._convert_to_list(category)
        logger.info(
            "Add observations with mass %s, analysis %s, era %s, channel %s and category %s.",
            mass, analysis, era, channel, category)
        self.cb.AddObservations(mass, analysis, era, channel, category)

    def add_signals(self, mass, analysis, era, channel, process, category):
        self.add_processes(mass, analysis, era, channel, process, category,
                           True)

    def add_backgrounds(self, mass, analysis, era, channel, process, category):
        self.add_processes(mass, analysis, era, channel, process, category,
                           False)

    def add_processes(self, mass, analysis, era, channel, process, category,
                      flag):
        mass = self._convert_to_list(mass)
        analysis = self._convert_to_list(analysis)
        era = self._convert_to_list(era)
        channel = self._convert_to_list(channel)
        category = self._convert_to_list(category)
        logger.info(
            "Add %s with mass %s, analysis %s, era %s, channel %s, process %s and category %s.",
            "signals" if flag else "backgrounds", mass, analysis, era, channel,
            process, category)
        self.cb.AddProcesses(mass, analysis, era, channel, process, category,
                             flag)

    def add_shape_systematic(self, name, strength, channel, process):
        channel = self._convert_to_list(channel)
        process = self._convert_to_list(process)

        self.cb.cp().channel(channel).process(process).AddSyst(
            self.cb, name, "shape", ch.SystMap()(strength))

    def add_normalization_systematic(self, name, strength, channel, process):
        channel = self._convert_to_list(channel)
        process = self._convert_to_list(process)

        self.cb.cp().channel(channel).process(process).AddSyst(
            self.cb, name, "lnN", ch.SystMap()(strength))

    def extract_shapes(self, channel, analysis, era, variable, bin=None):
        template = self._get_template(channel, analysis, era, variable)
        channel = self._convert_to_list(channel)
        cb_cp = self.cb.cp().channel(channel)

        if bin != None:
            bin = self._convert_to_list(bin)
            cb_cp = cb_cp.bin(bin)

        cb_cp.ExtractShapes(self.input_filename,
                            template.replace("$SYSTEMATIC", ""), template)
        self._shapes_extracted = True

    def _get_template(self, channel, analysis, era, variable):
        # TODO: Find suitable CombineHarvester templates here, e.g., for era or analysis
        return "#{CHANNEL}#$BIN#$PROCESS#{ANALYSIS}#{ERA}#{VARIABLE}#$MASS#$SYSTEMATIC".format(
            CHANNEL=channel, ANALYSIS=analysis, ERA=era, VARIABLE=variable)

    def print_datacard(self):
        self.cb.PrintAll()

    def auto_rebin(self, threshold, mode):
        rebin = ch.AutoRebin()
        rebin.SetBinThreshold(threshold)
        rebin.SetRebinMode(mode)
        rebin.SetPerformRebin(True)
        rebin.SetVerbosity(0)
        if logger.isEnabledFor(logging.DEBUG):
            rebin.SetVerbosity(1)
        rebin.Rebin(self.cb, self.cb)

    def add_bin_by_bin_systematics(self, processes, add_threshold,
                                   merge_threshold, fix_norm):
        if not self._shapes_extracted:
            logger.fatal("Shapes need to be extracted first.")
            raise Exception
        bbb = ch.BinByBinFactory()
        if logger.isEnabledFor(logging.DEBUG):
            bbb.SetVerbosity(1)
        bbb.SetAddThreshold(add_threshold)
        bbb.SetMergeThreshold(merge_threshold)
        bbb.SetFixNorm(fix_norm)
        bbb.MergeBinErrors(self.cb.cp().process(processes))
        bbb.AddBinByBin(self.cb.cp().process(processes), self.cb)
        self.cb.SetGroup("bbb", [".*_bin_\\d+"])
        self.cb.SetGroup("syst_plus_bbb", [".*"])

    def replace_observation_by_asimov_dataset(self, category):
        if not self._shapes_extracted:
            logger.fatal("Shapes need to be extracted first.")
            raise Exception

        def _replace_observation_by_asimov_dataset(observation):
            cb = self.cb.cp().analysis([observation.analysis()]).era([
                observation.era()
            ]).channel([observation.channel()]).bin([observation.bin()])
            background = cb.cp().backgrounds()
            signal = cb.cp().signals()
            observation.set_shape(background.GetShape() + signal.GetShape(),
                                  True)
            observation.set_rate(background.GetRate() + signal.GetRate())

        category = self._convert_to_list(category)
        self.cb.cp().bin(category).ForEachObs(
            _replace_observation_by_asimov_dataset)

    def write(self, output_datacard, output_shapes):
        logger.info("Create datacard files %s and %s.", output_datacard,
                    output_shapes)
        writer = ch.CardWriter(output_datacard, output_shapes)
        if logger.isEnabledFor(logging.DEBUG):
            writer.SetVerbosity(1)
        writer.CreateDirectories(
            False)  # TODO: FIXME: Does not work without this?
        # writer.SetWildcardMasses([]) # TODO: What is this doing?
        writer.WriteCards("", self.cb)

    def summary(self):
        logger.info("Analyses: %s", self.cb.analysis_set())
        logger.info("Eras: %s", self.cb.era_set())
        logger.info("Masses: %s", self.cb.mass_set())
        logger.info("Channels: %s", self.cb.channel_set())
        logger.info("Processes: %s", self.cb.process_set())
        logger.info("Signals: %s", self.cb.cp().signals().process_set())
        logger.info("Backgrounds: %s",
                    self.cb.cp().backgrounds().process_set())
        logger.info("Categories: %s", self.cb.bin_set())

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
        if self._name[-1] == "#":
            self._properties.append("Nominal")

        # TODO: Add validity checks that name is structured as expected

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
