import os
import sys
import time
import shutil
import numpy as np
from os.path import basename, split, splitext, realpath, isfile, join
try:
    from odbAccess import (openOdb, isUpgradeRequiredForOdb, upgradeOdb,
           MAX_PRINCIPAL, MID_PRINCIPAL, MIN_PRINCIPAL, PRESS, MISES, SCALAR,
           INTEGRATION_POINT, TRESCA, OdbError, maxEnvelope)
except ImportError:
    raise SystemExit("Script must be run by 'abaqus python'")


class Logger:
    def __init__(self, filename=None):
        self.handlers = [sys.stdout]
        if filename is not None:
            self.handlers.append(open(filename, "w"))
        self.warnings = 0
        self.verbosity = 1
        self.errors = 0

    def flush(self):
        for h in self.handlers:
            h.flush()

    def write(self, string, v=1):
        if v: handlers = self.handlers[:]
        else: handlers = self.handlers[1:]
        for h in handlers:
            h.write(string)

    def progress(self, string, frac):
        frac = abs(frac)
        ifrac = int(frac * 10.)

        bar = "." * min(max(ifrac, 1), 10)
        percent = min(frac, 1.)
        message = "info: {0} [{1:10s}] {2:6.2%}".format(string, bar, percent)

        pre = "" if frac < 1.E-12 else "\r"
        end = "" if frac <= 1. else "\n"
        self.write(pre + message + end, v=self.verbosity)
        self.flush()

    def info(self, message, end="\n"):
        """Log a message to the console handler"""
        message = "info: {0}{1}".format(message, end)
        self.write(message, v=self.verbosity)

    def warn(self, message):
        """Log a warning to the console handler"""
        message = "*** warning: {0}\n".format(message)
        self.write(message, v=1)

    def error(self, message, xit=1):
        message = "*** error: {0}\n".format(message)
        self.errors += 1
        self.write(message, v=1)
        if xit:
            sys.exit(1)

logger = Logger()

class ODBHandler(object):

    def __init__(self, source, destination=None, mode="rw",
                 bak=1, bakd=None, v=1):
        """Copy ODB and open copy"""
        logger.verbosity = v
        source = realpath(source)
        if not isfile(source):
            raise IOError("{0}: no such odb file".format(source))
        source = self.upgrade_if_necessary(source)

        # use first odb as skeleton
        if destination is None:
            odbfile = source
            if bak and "w" in mode:
                filedir, filename = split(source)
                bakd = bakd or filedir
                root, ext = splitext(filename)
                i = 1
                while 1:
                    bak = join(bakd, "{0}.b{1}{2}".format(root, i, ext))
                    if not isfile(bak):
                        break
                    i += 1
                shutil.copyfile(source, bak)
        else:
            shutil.copyfile(source, destination)
            odbfile = destination

        self.filename = odbfile
        if odbfile != source:
            logger.info("Destination: {0}".format(basename(odbfile)))
        logger.info("Opening root file {0}".format(basename(source)))

        # open the root odb
        self.odb = self.open_odb(odbfile, mode=mode)
        self.assy = self.odb.rootAssembly

        # stack is for holding items that are time consuming to retrieve from
        # the output database
        self.stack = {}

        pass

    def field_outputs(self, *args):
        key = tuple([x for x in args])
        try:
            return self.stack[key]
        except KeyError:
            pass

        if len(key) == 2:
            i, j = key
            fo = self.odb.steps.values()[i].frames[j].fieldOutputs
            self.stack[(i, j)] = fo
            return fo

        if len(key) == 3:
            i, j, field = key
            try:
                fo = self.stack[(i, j)]
            except KeyError:
                fo = self.odb.steps.values()[i].frames[j].fieldOutputs
                self.stack[(i, j)] = fo
            if field == "EE" and "EE" not in fo:
                if "LE" in fo:
                    field = "LE"
                else:
                    field = "E"
            fo = fo[field]
            self.stack[(i, j, field)] = fo
            return fo

        i, j, field, position = key
        if (i, j, field) in self.stack:
            fo = self.stack[(i, j, field)]
        elif (i, j) in self.stack:
            fo = self.stack[(i, j)][field]
            self.stack[(i, j, field)] = fo
        fo = fo.getSubset(position=position)
        self.stack[(i, j, field, position)] = fo
        return fo

    def __contains__(self, item):
        """Check if item is in the output database. item is assumed to be a
        field output and we only check if it is in the last frame"""
        i = self.nsteps - 1
        j = self.nframes(-1) - 1
        fo = self.field_outputs(i, j)
        return item in fo.keys()

    @staticmethod
    def upgrade_if_necessary(filename):
        if isUpgradeRequiredForOdb(upgradeRequiredOdbPath=filename):
            oldf = filename
            dirname, basename = split(filename)
            root, ext = splitext(basename)
            basename = root + "_upgraded" + ext
            filename = join(dirname, basename)
            upgradeOdb(existingOdbPath=oldf, upgradedOdbPath=filename)
        return filename

    @property
    def nsteps(self):
        return len(self.odb.steps)

    @property
    def last_step(self):
        return self.odb.steps.values()[-1]

    def open_odb(self, filename, mode="r"):
        filename = self.upgrade_if_necessary(filename)
        odb = openOdb(filename, readOnly="w" not in mode)
        return odb

    def close(self):
        logger.info("Closing {0}".format(basename(self.filename)))
        self.odb.close()

    def nframes(self, step):
        return len(self.odb.steps[step].frames)

    def final_time(self):
        return self.odb.steps[-1].frames[-1].frameValue

    def merge(self, filenames, steps=None, frames=None, inherit=True,
              mode="append", instance=None):
        """Merge filenames with self.

        Parameters
        ----------
        filenames : list of str
            Filenames of odbs to extend to current odb
        steps : list of int, optional, [all]
            If given, use only these steps.  Defaults to all steps.
        inherit : bool, optional, [True]
            Inherit fields from last frame of last step

        """
        assert mode in ("append", "extend")

        # Determine if a single file, or list of files was sent.
        if not isinstance(filenames, (list, tuple)):
            filenames = [filenames]
        for filename in filenames:
            if not isfile(filename):
                raise IOError("No such file or directory: '{0}'".format(filename))
        if mode == "extend":
            for filename in filenames:
                self.genstep_and_merge([filename], steps, frames, inherit, instance)
        else:
            self.genstep_and_merge(filenames, steps, frames, inherit, instance)

    def genstep_and_merge(self, filenames, steps, frames, inherit, instance):
        """Extend the current odb with steps from filename

        Parameters
        ----------
        filenames : list of str
            Filenames of odbs to extend to current odb
        steps : list of int, optional, [all]
            If given, use only these steps.  Defaults to all steps.
        inherit : bool, optional, [True]
            Inherit fields from last frame of last step

        """
        # Open the odb file
        odbs = [self.open_odb(filename, mode="r") for filename in filenames]
        if instance is not None:
            regions = [odb.rootAssembly.instances[instance] for odb in odbs]
        else:
            regions = None

        # make sure all odbs have the same number of steps
        num_steps = len(odbs[0].steps)
        if any([len(odb.steps) != num_steps for odb in odbs]):
            logger.warn("ODBs have unequal number of steps, merging only the last")
            steps = [-1]

        # determine which steps to merge from the new odb
        if steps is None:
            steps = range(num_steps)
        elif steps == "last":
            steps = [-1]
        else:
            # must be a list, make sure we are using 0 indexed arrays
            try:
                steps = [step - 1 for step in steps]
            except TypeError:
                raise ValueError("steps must be a list of steps, or 'all'")
        steps = [step for step in steps]

        # append by combining last step of current odb with
        zero_field = {}
        zero_step = self.last_step
        frame_init_val = zero_step.frames[-1].frameValue
        if inherit:
            fo = zero_step.frames[-1].fieldOutputs
            zero_field = dict([(k, v) for (k, v) in fo.items()])
            if instance is not None:
                region = self.assy.instances[instance]
                for (k, v) in zero_field.items():
                    zero_field[k] = v.getSubset(region=region)

        # determine number of frames to merge (for progress metering)
        ref_odb = odbs[0]
        other_odbs = odbs[1:]

        this_frame = tot_frames = 0
        for step in steps:
            tot_frames += len(ref_odb.steps.values()[step].frames)

        logger.info("Merging steps/frames of {0}".format(
            ", ".join(basename(f) for f in filenames)))
        logger.info("Steps to merge: {0}".format(len(ref_odb.steps)))
        logger.info("Frames to merge: {0}".format(tot_frames))

        N0 = self.nsteps
        jstep = self.nsteps
        for (istep, step) in enumerate(steps):
            step_name = "User Step {0}".format(jstep+istep+1)
            ref_step = ref_odb.steps.values()[step]

            # create a new step for combined results
            new_step = self.odb.Step(
                name=step_name,
                description='User Step {0}'.format(istep+1),
                domain=ref_step.domain,
                procedure=ref_step.procedure,
                timePeriod=ref_step.timePeriod,
                previousStepName=self.last_step.name)

            # determine if we can merge all frames, or just the last
            if frames is None:
                num_ref_frames = len(ref_step.frames)
                num_oth_frames = [len(o.steps.values()[step].frames)
                                  for o in other_odbs]
                if any([num_ref_frames != n for n in num_oth_frames]):
                    # merge only last
                    frames = [-1]
                else:
                    frames = range(num_ref_frames)
            elif frames == "last":
                frames = [-1]

            # combine fields in each step, inheriting state from last step if
            # requested.
            progmsg = "Step {0}: merging frames".format(istep+1)
            logger.progress(progmsg, 0)
            stack = {}
            for iframe in frames:
                ref_frame = ref_step.frames[iframe]
                this_frame += 1
                frac = float(iframe+1) / len(frames)

                # instantiate the new frame
                new_frame = new_step.Frame(
                    incrementNumber=ref_frame.incrementNumber,
                    frameValue=ref_frame.frameValue + frame_init_val,
                    description=ref_frame.description)

                # add field outputs from frames of ref_odb and other odbs
                rfo = ref_frame.fieldOutputs
                for (key, ref_field) in rfo.items():
                    if regions:
                        ref_field = ref_field.getSubset(region=regions[0])
                    if key in zero_field:
                        ref_field += zero_field[key]
                    for (io, other_odb) in enumerate(other_odbs, start=1):
                        other_frame = other_odb.steps.values()[step].frames[iframe]
                        try:
                            ofo = stack[(other_odb.name, step, iframe)]
                        except KeyError:
                            ofo = other_frame.fieldOutputs
                            stack[(other_odb.name, step, iframe)] = fo
                        if key in ofo:
                            val = ofo[key]
                            if regions:
                                val = val.getSubset(region=regions[io])
                            ref_field += val
                    if "SDV" in key.upper() and iframe != 0:
                        # average quantities
                        ref_field = ref_field / 2.
                    desc = ref_field.description
                    try:
                        new_field = new_frame.FieldOutput(name=key,
                                                          field=ref_field,
                                                          description=desc)
                    except OdbError as e:
                        message = ("Unable to create field for {0}.\n"
                                   "Abaqus returned the following error when "
                                   "trying to create a field for {0}:\n"
                                   "'{1}'")
                        logger.error(message.format(key, str(e.args[0])), xit=0)
                        continue

                logger.progress(progmsg, frac)
                continue # frames

            logger.progress(progmsg, 1.2)
            continue # steps

        self.odb.save()

        for odb in odbs:
            odb.close()

        return

    def write_fields(self, *args, **kwargs):
        if not args:
            raise ValueError("no arguments given")

        known_fields = ("DEVI", "MAX-SHEAR")
        for arg in args:
            if arg not in known_fields:
                raise ValueError("{0}: unknown field".format(arg))

        elem_set = kwargs.get("elem_set")
        instance = kwargs.get("instance")
        if instance is None:
            instance = self.odb.rootAssembly.instances.values()[0]
        else:
            try:
                instance = self.odb.rootAssembly.instances[instance]
            except KeyError:
                logger.error("{0}: not an instance".format(instance))

        if elem_set is not None:
            try:
                region = instance.elementSets[elem_set]
            except KeyError:
                elem_sets = ", ".join(instance.elementSets.keys())
                logger.error("'{0}' is not an element set.  "
                             "Choose from {1}".format(elem_set, elem_sets))
        else:
            region = None

        logger.info("Writing the following fields: {0}".format(", ".join(args)))
        for (istep, step) in enumerate(self.odb.steps.values()):
            tstep = time.time()
            logger.info("  Step {0}, len(frames)={1}".format(
                step.name, len(step.frames)))

            for (iframe, frame) in enumerate(step.frames):
                logger.info("    Frame {0}".format(iframe+1))

                field_out = self.field_outputs(step, frame)

                # write new fields
                for arg in args:
                    logger.info("    Field var = {0}".format(arg))

                    if arg in ("DEVI", "MAX-SHEAR"):
                        field = field_out["S"]

                    if region is not None:
                        field = field.getSubset(region=region)

                    # compute field
                    if arg == "DEVI":
                        s1 = field.getScalarField(invariant=MAX_PRINCIPAL)
                        s2 = field.getScalarField(invariant=MID_PRINCIPAL)
                        s3 = field.getScalarField(invariant=MIN_PRINCIPAL)
                        x = s1 - (s1 + s2 + s3) / 3.
                        info = {"name": "DEVI",
                                "description": "Maximum princ deviatoric stress",
                                "type": SCALAR}
                    elif arg == "MAX-SHEAR":
                        info = {"name": "MAX-SHEAR",
                                "description": "Maximum shear stress",
                                "type": SCALAR}
                        x = field.getScalarField(invariant=TRESCA) / 2.

                    fx = frame.FieldOutput(**info)
                    fx.addData(field=x)

            logger.info("  {0}: done ({1:g})".format(step.name, time.time()-tstep))

        self.odb.save()

        return

    def get_max(self, field_names, elem_set=None, steps=None, frames=None,
                position=INTEGRATION_POINT, instance=None, **kwargs):

        if not isinstance(field_names, (list, tuple)):
            field_names = [field_names]

        if steps is None:
            steps = [-1]
        elif not isinstance(steps, (list, tuple)):
            steps = [steps]

        if frames is None:
            frames = [-1]
        elif not isinstance(frames, (list, tuple)):
            frames = [frames]

        logger.info("Getting maximum values for {0}".format(",".join(field_names)))
        tstart = time.time()
        max_fields = dict([(name, -1.E+30) for name in field_names])
        for i in steps:
            for j in frames:
                for name in field_names:
                    mx = fsort(name, elem_set=elem_step, step=i, frame=j,
                               position=position, instance=instance, **kwargs)
                    max_fields[name] = max(mx[-1].data, max_fields[name])

        logger.info("done ({0:g})".format(time.time()-tstart))
        return max_fields

    def fsort(self, field_name, elem_set=None, step=-1, frame=-1,
              position=INTEGRATION_POINT, instance=None, **kwargs):
        """Sort field_name

        Parameters
        ----------
        field_name : str
            A field output name
        elem_set : str
            An element set name.  If not given, find max for all element sets
        step : int [-1]
        frame : int [-1]
        position : enum [INTEGRATION_POINT]
            Should be one of INTEGRATION_POINT, ELEMENT_NODAL, CENTROID
        kwargs : dict
            keyword arguments to be passed to the field's getScalarField method

        Examples
        --------
        Get the maximum principal stress at the element centroid

        >>> p = PostProcessor(filename, instance="PART-1-1")
        >>> mx = p.maximum("THE_SET", "S", position=CENTROID,
                           invariant=MAX_PRINCIPAL)

        Get the maximum value of the 11 component of elastic strain at the
        element nodes

        >>> mx = p.maximum("THE_SET", "EE", position=ELEMENT_NODAL,
                           componentLabel="EE11")

        """
        # get the field, checking first if we have already gotten it - this
        # saves A LOT of time over getting it from the database each time
        fo = self.field_outputs(step, frame, field_name, position)
        if instance is None:
            instance = self.odb.rootAssembly.instances.values()[0]
        else:
            try:
                instance = self.odb.rootAssembly.instances[instance]
            except KeyError:
                logger.error("{0}: not an instance".format(instance))

        # get the subset for this element set
        if elem_set is not None:
            fo = fo.getSubset(region=instance.elementSets[elem_set])
        if kwargs:
            fo = fo.getScalarField(**kwargs)

        # sort the scalar field based on the data attribute
        return sorted([v for v in fo.values], key=lambda x: x.data)

    @property
    def instances(self):
        return self.rootAssembly.instances.keys()

    def gen_elem_set(self, instance, elem_set, elem_labels):
        if instance is None:
            instance = self.assy.instances.keys()[0]
        try:
            instance = self.odb.rootAssembly.instances[instance]
        except KeyError:
            logger.error("{0}: not an instance".format(instance))
        instance.ElementSetFromElementLabels(elem_set, elem_labels)

    def gen_node_set(self, instance, node_set, node_labels):
        if instance is None:
            instance = self.assy.instances.keys()[0]
        try:
            instance = self.odb.rootAssembly.instances[instance]
        except KeyError:
            logger.error("{0}: not an instance".format(instance))
        instance.NodeSetFromNodeLabels(node_set, node_labels)


# Local Variables:
# mode: python
# End:
